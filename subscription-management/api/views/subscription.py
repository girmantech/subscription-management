from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

import razorpay
import stripe

from .. import models
from ..utils import (
    dictfetchone, dictfetchall, currency_unit_mapping
)

# Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Stripe client
stripe.api_key = settings.STRIPE_SECRET_KEY


class Subscription(APIView):
    def post(self, request):
        plan_id = request.data.get('plan_id')

        if not plan_id:
            return Response({"error": "plan id missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            customer = models.Customer.objects.get(id=request.customer_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
            
            with connection.cursor() as cursor:
                # fetching product price, tax percentage and billing interval
                cursor.execute("""
                    SELECT
                        pricing.price,
                        pricing.tax_percentage,
                        plan.billing_interval
                    FROM api_productpricing pricing
                    JOIN api_plan plan on pricing.product_id = plan.product_id
                    WHERE plan.id = %s and pricing.currency_id = %s;
                """, [plan_id, currency])

                try:
                    result = dictfetchone(cursor)
                except:
                    return Response({'error': "selected plan is not associated with customer's curreny"}, status=status.HTTP_404_NOT_FOUND)
                
                # tax and total amount calculation
                billing_interval = result['billing_interval']
                price = float(result['price'])
                tax_percentage = result['tax_percentage']

                tax_amount = (tax_percentage / 100) * (price * billing_interval)
                total_amount = (price * billing_interval) + tax_amount
                
                current_timestamp = timezone.now()
                start_timestamp = int(current_timestamp.timestamp())
                end_timestamp = int((current_timestamp + timezone.timedelta(days=30 * billing_interval)).timestamp())

            total_amount = int(total_amount * currency_unit_mapping[customer.currency.code])
            tax_amount = int(tax_amount * currency_unit_mapping[customer.currency.code])

            # generate session-id using Stripe session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': customer.currency.code.lower(),
                        'product_data': {
                            'name': 'Subscription Plan',
                            'description': f'Plan {plan_id} for {billing_interval} month(s)',
                        },
                        'unit_amount': total_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{settings.FRONTEND_URL}/success',
                cancel_url=f'{settings.FRONTEND_URL}/cancel',
            )
            
            with transaction.atomic():
                # creating invoice (draft)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_invoice (status, customer_id, plan_id, tax_amount, total_amount, created_at, due_at, provider_session_or_order_id)
                        VALUES ('DRAFT', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW() + INTERVAL '2 hours'), %s)
                        RETURNING id;
                    """, [customer.id, plan_id, tax_amount, total_amount, session.id])

                    result = dictfetchone(cursor)
                    invoice_id = result['id']

                # creating subscription (inactive)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_subscription (status, invoice_id, customer_id, starts_at, ends_at, created_at)
                        VALUES ('INACTIVE', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()))
                    """, [invoice_id, customer.id, start_timestamp, end_timestamp])

            return Response({
                'checkout_url': session.url,
                'message': 'invoice and subscription created successfully'
            }, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    

    def get(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)

            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM api_subscription
                    WHERE customer_id = %s
                    AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                    AND status = 'ACTIVE' AND deleted_at IS NULL;
                """, [customer.id])
                
                
                result = dictfetchall(cursor)

            return Response(result, status=status.HTTP_200_OK)
        
        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)


class UpgradeSubscription(APIView):
    def post(self, request):
        plan_id = request.data.get('plan_id')

        if not plan_id:
            return Response({"error": "invalid plan id"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            customer = models.Customer.objects.get(id=request.customer_id)
            plan = models.Plan.objects.get(id=plan_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)    
            
            # getting unused percentage from the current plan
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        invoice.total_amount, invoice.tax_amount, subscription.starts_at, subscription.ends_at
                    FROM api_subscription subscription
                    JOIN api_invoice invoice ON invoice.id = subscription.invoice_id
                    WHERE invoice.customer_id = %s
                        AND EXTRACT(EPOCH FROM NOW()) BETWEEN subscription.starts_at AND subscription.ends_at
                        AND subscription.deleted_at IS NULL AND subscription.status = 'ACTIVE';
                """, [customer.id])

                try:
                    result = dictfetchone(cursor)
                except:
                    return Response({'error': 'no active subscription found'}, status=status.HTTP_404_NOT_FOUND)
                
                current_subscription_starts_at = result['starts_at']
                current_subscription_ends_at = result['ends_at']
                current_subscription_total_amount = result['total_amount']
                current_subscription_tax_amount = result['tax_amount']

                # calculating unused percentage
                current_timestamp = int(timezone.now().timestamp())
                unused_percentage = 1 - (current_timestamp - current_subscription_starts_at) / \
                    (current_subscription_ends_at - current_subscription_starts_at)
                
            # calculating unused amount
            unused_amount = int((current_subscription_total_amount - current_subscription_tax_amount) * unused_percentage)
            
            # fetching product price, tax percentage and billing interval for the next_plan
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        pricing.price,
                        pricing.tax_percentage,
                        plan.billing_interval
                    FROM api_productpricing pricing
                    JOIN api_plan plan ON pricing.product_id = plan.product_id
                    WHERE plan.id = %s AND pricing.currency_id = %s;
                """, [plan_id, currency])

                try:
                    result = dictfetchone(cursor)
                except:
                    return Response({'error': "selected plan not associated with customer's curreny"}, status=status.HTTP_400_BAD_REQUEST)
                
                # tax and total amount calculation
                billing_interval = result['billing_interval']
                price = float(result['price'])
                tax_percentage = result['tax_percentage']

                tax_amount = (tax_percentage / 100) * (price * billing_interval)

                total_amount = (price * billing_interval) + tax_amount
                
                current_timestamp = timezone.now()
                start_timestamp = int(current_timestamp.timestamp())
                end_timestamp = int((current_timestamp + timezone.timedelta(days=30 * billing_interval)).timestamp())

            # removing unused amount from the total amount for the next plan
            total_amount = int(total_amount * currency_unit_mapping[customer.currency.code]) - unused_amount
            tax_amount = int(tax_amount * currency_unit_mapping[customer.currency.code])

            # generate session-id using Stripe session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': customer.currency.code.lower(),
                        'product_data': {
                            'name': 'Subscription Plan Upgrade',
                            'description': f'Plan {plan_id} for {billing_interval} month(s)',
                        },
                        'unit_amount': total_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{settings.FRONTEND_URL}/success',
                cancel_url=f'{settings.FRONTEND_URL}/cancel',
            )

            # creating new invoice and subscriptions
            with transaction.atomic():
                # creating invoice (draft)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_invoice (status, customer_id, plan_id, tax_amount, total_amount, created_at, due_at, provider_session_or_order_id)
                        VALUES ('DRAFT', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW() + INTERVAL '2 hours'), %s)
                        RETURNING id;
                    """, [customer.id, plan_id, tax_amount, total_amount, session.id])

                    result = dictfetchone(cursor)
                    invoice_id = result['id']

                # creating subscription (inactive)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_subscription (status, invoice_id, customer_id, starts_at, ends_at, created_at)
                        VALUES ('INACTIVE', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()))
                    """, [invoice_id, customer.id, start_timestamp, end_timestamp])

                # updating upgrade information in the current subscription
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE api_subscription SET
                            upgraded_to_plan_id = %s
                        WHERE customer_id = %s
                            AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                            AND deleted_at IS NULL AND status = 'ACTIVE';
                    """, [plan_id, customer.id])

            return Response({
                'checkout_url': session.url,
                'message': 'invoice and subscription created successfully'
            }, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Plan.DoesNotExist:
            return Response({"error": "plan not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class DowngradeSubscription(APIView):
    def post(self, request):
        plan_id = request.data.get('plan_id')

        if not plan_id:
            return Response({"error": "missing plan id"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            customer = models.Customer.objects.get(id=request.customer_id)
            plan = models.Plan.objects.get(id=plan_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                product = plan.product
                pricing = models.ProductPricing.objects.get(product=product)
                assert pricing.currency.code == currency
            except:
                return Response({'error': "selected plan not associated with customer's curreny"}, status=status.HTTP_400_BAD_REQUEST)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE api_subscription SET
                        downgraded_at = EXTRACT(EPOCH FROM NOW()),
                        downgraded_to_plan_id = %s
                    WHERE customer_id = %s
                        AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                        AND deleted_at IS NULL AND status = 'ACTIVE';
                """, [plan_id, customer.id])

            return Response({'message': 'subscription downgraded successfully'}, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Plan.DoesNotExist:
            return Response({"error": "plan not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class CancelSubscription(APIView):
    def post(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE api_subscription SET
                        cancelled_at = EXTRACT(EPOCH FROM NOW())
                    WHERE customer_id = %s
                        AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                        AND deleted_at IS NULL AND status = 'active';
                """, [customer.id])

            return Response({'message': 'subscription cancelled successfully'}, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Plan.DoesNotExist:
            return Response({"error": "plan not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response({'error': 'invalid payload or signature'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event['type']
        session = event['data']['object']

        if event_type == 'checkout.session.completed':
            return self.handle_payment_success(session)

        else:
            return self.handle_payment_failure(session)

    def handle_payment_success(self, session):
        try:
            # checking if invoice and subscription associated with stripe session exist
            invoice = models.Invoice.objects.get(provider_session_or_order_id=session.id)
            subscription = models.Subscription.objects.get(invoice=invoice)

            invoice_id = invoice.id

            with transaction.atomic():
                # updating invoice status to 'PAID'
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE api_invoice SET
                            status = 'PAID',
                            paid_at = EXTRACT(EPOCH FROM NOW())
                        WHERE id = %s;
                    """, [invoice_id])

                # getting start timestamp of the corresponding subscription
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT starts_at FROM api_subscription
                        WHERE invoice_id = %s;
                    """, [invoice_id])

                    result = dictfetchone(cursor)
                    starts_at = result['starts_at']

                ### first time activation case ###
                if starts_at <= int(timezone.now().timestamp()):
                    # fetching billing interval
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT plan.billing_interval
                            FROM api_invoice invoice
                            JOIN api_plan plan
                            ON invoice.plan_id = plan.id WHERE invoice.id = %s;
                        """, [invoice_id])

                        result = dictfetchone(cursor)
                        billing_interval = result['billing_interval']

                    # checking if there is a currently active subscription
                    # which is supposed to be upgraded to the invoice plan id
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT id FROM api_subscription
                                WHERE customer_id = %s
                                AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                                AND deleted_at IS NULL AND status = 'ACTIVE'
                                AND upgraded_to_plan_id = %s;
                        """, [subscription.customer.id, invoice.plan_id])

                        try:
                            result = dictfetchone(cursor)
                        except:
                            result = None
                    
                    # updating upgrade information in the current subscription
                    if result:
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                UPDATE api_subscription SET
                                    upgraded_at = EXTRACT(EPOCH FROM NOW()),
                                    status = 'UPGRADED'
                                WHERE id = %s;
                                """, [result['id']])
                    
                    current_timestamp = timezone.now()
                    start_timestamp = int(current_timestamp.timestamp())
                    end_timestamp = int((current_timestamp + timezone.timedelta(days=30 * billing_interval)).timestamp())

                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE api_subscription
                            SET status='ACTIVE', starts_at = %s, ends_at = %s
                            WHERE invoice_id = %s;
                        """, [start_timestamp, end_timestamp, invoice_id])

                    return Response({'message': 'subscription activated'}, status=status.HTTP_201_CREATED)

                ### renewal case ###
                else:
                    # updating next subscription status to active
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE api_subscription
                            SET status = 'ACTIVE'
                            WHERE invoice_id = %s
                            RETURNING id;
                        """, [invoice_id])

                        result = dictfetchone(cursor)
                        next_subscription_id = result['id']

                    # update renewal information in the current subscription plan
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE api_subscription SET
                            renewed_at = EXTRACT(EPOCH FROM NOW()),
                            renewed_subscription_id = %s
                            WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                            AND deleted_at IS NULL AND status = 'ACTIVE';
                        """, [next_subscription_id])

                return Response({'message': 'payment successful, invoice and subscription updated'}, status=status.HTTP_200_OK)

        except models.Invoice.DoesNotExist:
            return Response({'error': 'invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Subscription.DoesNotExist:
            return Response({'error': 'subscription not found'}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def handle_payment_failure(self, session):
        try:
            invoice = models.Invoice.objects.get(stripe_session_id=session.id)
            invoice.status = models.Invoice.InvoiceStatus.UNPAID
            invoice.save()

            subscription = models.Subscription.objects.get(invoice=invoice)

            return Response({'message': 'payment expired or failed, invoice and subscription canceled'}, status=status.HTTP_200_OK)

        except models.Invoice.DoesNotExist:
            return Response({'error': 'invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Subscription.DoesNotExist:
            return Response({'error': 'subscription not found'}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)
