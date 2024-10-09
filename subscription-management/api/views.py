import random

from django.db import connection, transaction
from django.utils import timezone
from django.forms.models import model_to_dict

from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from . import models
from . import serializers
from .utils import dictfetchone, dictfetchall, generate_refresh_token


class CurrencyList(generics.ListAPIView):
    queryset = models.Currency.objects.all()
    serializer_class = serializers.CurrencySerializer


class Signup(APIView):
    def post(self, request):
        request.data['created_at'] = int(timezone.now().timestamp())
        serializer = serializers.CustomerSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Signin(APIView):
    def post(self, request):
        phone = request.data.get('phone')

        try:
            customer = models.Customer.objects.get(phone=phone)

            # otp generation and setting expiry-time-stamp
            otp_code = '{:06d}'.format(random.randint(0, 999999))
            expires_at = int((timezone.now() + timezone.timedelta(minutes=10)).timestamp())

            otp, _ = models.OTP.objects.update_or_create(
                phone=phone,
                defaults={
                    'otp': otp_code,
                    'expires_at': expires_at
                }
            )

            # return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
            return Response({"id": otp.id, "otp": otp.otp}, status=status.HTTP_200_OK)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        

class OTPValidation(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        input_otp = request.data.get('otp')

        try:
            customer = models.Customer.objects.get(phone=phone)

            try:
                otp_record = models.OTP.objects.get(phone=phone)

                if otp_record.is_expired():
                    return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

                if str(otp_record.otp) == str(input_otp):
                    otp_record.delete()

                    tokens = generate_refresh_token(customer)
                    return Response(tokens, status=status.HTTP_200_OK)
                
                else:
                    return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

            except models.OTP.DoesNotExist:
                return Response({"error": "OTP not found for this customer"}, status=status.HTTP_404_NOT_FOUND)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)


class Me(APIView):
    def get(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)
            return Response(model_to_dict(customer), status=status.HTTP_200_OK)
        
        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)
            serializer = serializers.CustomerSerializer(customer, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)


class CustomerList(generics.ListCreateAPIView):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerSerializer


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerSerializer


class ProductList(APIView):
    def get(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)
            
            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'Currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        product.id as product_id,
                        product.name,
                        product.description,
                        pricing.price,
                        pricing.currency_id
                    FROM api_product product
                    LEFT JOIN api_productpricing pricing ON product.id = pricing.product_id
                    WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN pricing.from_date AND pricing.to_date
                    AND product.deleted_at IS NULL AND pricing.deleted_at IS NULL AND pricing.currency_id = %s;
                """, [currency])

                results = dictfetchall(cursor)
            
            return Response(results)
    
        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class PlanList(APIView):
    def get(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'Currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        plan.id as plan_id,
                        product.id as product_id,
                        product.name,
                        product.description,
                        pricing.price,
                        pricing.currency_id,
                        plan.billing_interval
                    FROM api_plan plan
                    LEFT JOIN api_product product ON plan.product_id = product.id
                    LEFT JOIN api_productpricing pricing ON product.id = pricing.product_id
                    WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN pricing.from_date AND pricing.to_date
                    AND plan.deleted_at IS NULL AND product.deleted_at IS NULL
                    AND product.deleted_at IS NULL AND pricing.deleted_at IS NULL
                    AND pricing.currency_id = %s;
                """, [currency])

                results = dictfetchall(cursor)
            
            return Response(results)
        
        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class PlanListForProduct(APIView):
    def get(self, request, product_id):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'Currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        plan.id as plan_id,
                        product.id as product_id,
                        product.name,
                        product.description,
                        pricing.price,
                        pricing.currency_id,
                        plan.billing_interval
                    FROM api_plan plan
                    LEFT JOIN api_product product ON plan.product_id = product.id
                    LEFT JOIN api_productpricing pricing ON product.id = pricing.product_id
                    WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN pricing.from_date AND pricing.to_date
                    AND product.id = %s
                    AND plan.deleted_at IS NULL AND product.deleted_at IS NULL
                    AND product.deleted_at IS NULL AND pricing.deleted_at IS NULL
                    AND pricing.currency_id = %s;
                """, [product_id, currency])

                results = dictfetchall(cursor)
            
            return Response(results)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class Subscription(APIView):
    def post(self, request):
        try:
            plan_id = request.data.get('plan_id')

            if not plan_id:
                return Response({"error": "Invalid plan id"}, status=status.HTTP_400_BAD_REQUEST)
            
            customer = models.Customer.objects.get(id=request.customer_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'Currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
                
            
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
                    return Response({'error': "Selected plan not associated with customer's curreny"}, status=status.HTTP_404_NOT_FOUND)
                
                # tax and total amount calculation
                billing_interval = result['billing_interval']
                price = float(result['price'])
                tax_percentage = result['tax_percentage']

                tax_amount = (tax_percentage / 100) * (price * billing_interval)
                total_amount = (price * billing_interval) + tax_amount
                
                current_timestamp = timezone.now()
                start_timestamp = int(current_timestamp.timestamp())
                end_timestamp = int((current_timestamp + timezone.timedelta(days=30 * billing_interval)).timestamp())

            # TODO: handle smallest currency for amounts
            
            with transaction.atomic():
                # creating invoice (draft)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_invoice (status, customer_id, plan_id, tax_amount, total_amount, created_at, due_date)
                        VALUES ('DRAFT', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW() + INTERVAL '24 hours'))
                        RETURNING id;
                    """, [customer.id, plan_id, tax_amount, total_amount])

                    result = dictfetchone(cursor)
                    invoice_id = result['id']

                # creating subscription (inactive)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_subscription (status, invoice_id, customer_id, starts_at, ends_at)
                        VALUES ('INACTIVE', %s, %s, %s, %s)
                    """, [invoice_id, customer.id, start_timestamp, end_timestamp])

            # TODO: Write a CRON-JOB to clean up the subscription and invoices table if the payment in not made within 2 hours 

            return Response({'message': 'Invoice and subscription created successfully'}, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ActivateSubscription(APIView):
    def post(self, request):
        try:
            invoice_id = request.data.get('invoice_id')
            payment_status = request.data.get('payment_status')

            if not invoice_id:
                return Response({"error": "Invalid plan id"}, status=status.HTTP_400_BAD_REQUEST)
            if not payment_status:
                return Response({"error": "Invalid payment status"}, status=status.HTTP_400_BAD_REQUEST)
            
            if payment_status == 'DUE':
                return Response({"error": "Payment is pending"}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # ?? Check if invoice already paid
            
            if payment_status == 'SUCCESS':
                # check if invoice id associated with any subscription
                check_subscription = models.Subscription.objects.get(invoice_id=invoice_id)

                with transaction.atomic():
                    # updating invoice status to 'PAID'
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE api_invoice SET status = 'PAID'
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
                        
                        current_timestamp = timezone.now()
                        start_timestamp = int(current_timestamp.timestamp())
                        end_timestamp = int((current_timestamp + timezone.timedelta(days=30 * billing_interval)).timestamp())

                        with connection.cursor() as cursor:
                            cursor.execute("""
                                UPDATE api_subscription
                                SET status='ACTIVE', starts_at = %s, ends_at = %s
                                WHERE invoice_id = %s;
                            """, [start_timestamp, end_timestamp, invoice_id])

                        return Response({'message': 'Subscription activated'}, status=status.HTTP_201_CREATED)

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

                    return Response({'message': 'Subscription renewed'}, status=status.HTTP_201_CREATED)
            
            else:
                return Response({"error": "Invalid payment status"}, status=status.HTTP_400_BAD_REQUEST)
            
        except models.Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class UpgradeSubscription(APIView):
    def post(self, request):
        try:
            plan_id = request.data.get('plan_id')

            if not plan_id:
                return Response({"error": "Invalid plan id"}, status=status.HTTP_400_BAD_REQUEST)
            
            customer = models.Customer.objects.get(id=request.customer_id)
            plan = models.Plan.objects.get(id=plan_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'Currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)    
            
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
                    return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)
                
                current_subscription_starts_at = result['starts_at']
                current_subscription_ends_at = result['ends_at']
                current_subscription_total_amount = result['total_amount']
                current_subscription_tax_amount = result['tax_amount']

                # calculating unused percentage
                current_timestamp = int(timezone.now().timestamp())
                unused_percentage = 1 - (current_timestamp - current_subscription_starts_at) / \
                    (current_subscription_ends_at - current_subscription_starts_at)
                
            # calculating unused amount
            unused_amount = (current_subscription_total_amount - current_subscription_tax_amount) * unused_percentage
            
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
                    return Response({'error': "Selected plan not associated with customer's curreny"}, status=status.HTTP_400_BAD_REQUEST)
                
                # tax and total amount calculation
                billing_interval = result['billing_interval']
                price = float(result['price'])
                tax_percentage = result['tax_percentage']

                tax_amount = (tax_percentage / 100) * (price * billing_interval)

                # removing unused amount from the total amount for the next plan
                total_amount = (price * billing_interval) + tax_amount - unused_amount
                
                current_timestamp = timezone.now()
                start_timestamp = int(current_timestamp.timestamp())
                end_timestamp = int((current_timestamp + timezone.timedelta(days=30 * billing_interval)).timestamp())

            # TODO: handle smallest currency for amounts

            # creating new invoice and subscriptions
            with transaction.atomic():
                # creating invoice (draft)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_invoice (status, customer_id, plan_id, tax_amount, total_amount, created_at, due_date)
                        VALUES ('DRAFT', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW()))
                        RETURNING id;
                    """, [customer.id, plan_id, tax_amount, total_amount])

                    result = dictfetchone(cursor)
                    invoice_id = result['id']

                # creating subscription (inactive)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_subscription (status, invoice_id, customer_id, starts_at, ends_at)
                        VALUES ('INACTIVE', %s, %s, %s, %s)
                    """, [invoice_id, customer.id, start_timestamp, end_timestamp])

                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE api_subscription SET
                            upgraded_at = EXTRACT(EPOCH FROM NOW()),
                            upgraded_to_plan_id = %s,
                            status = 'UPGRADED'
                        WHERE customer_id = %s
                            AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                            AND deleted_at IS NULL AND status = 'ACTIVE';
                    """, [plan_id, customer.id])

            return Response({'message': 'Subscription upgraded successfully'}, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class DowngradeSubscription(APIView):
    def post(self, request):
        try:
            plan_id = request.data.get('plan_id')

            if not plan_id:
                return Response({"error": "Invalid plan id"}, status=status.HTTP_400_BAD_REQUEST)
            
            customer = models.Customer.objects.get(id=request.customer_id)
            plan = models.Plan.objects.get(id=plan_id)

            try:
                currency = customer.currency.code
            except:
                return Response({'error': 'Currency is not defined for the customer'}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                product = plan.product
                pricing = models.ProductPricing.objects.get(product=product)
                assert pricing.currency.code == currency
            except:
                return Response({'error': "Selected plan not associated with customer's curreny"}, status=status.HTTP_400_BAD_REQUEST)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE api_subscription SET
                        downgraded_at = EXTRACT(EPOCH FROM NOW()),
                        downgraded_to_plan_id = %s
                    WHERE customer_id = %s
                        AND EXTRACT(EPOCH FROM NOW()) BETWEEN starts_at AND ends_at
                        AND deleted_at IS NULL AND status = 'ACTIVE';
                """, [plan_id, customer.id])

            return Response({'message': 'Subscription downgraded successfully'}, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        
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

            return Response({'message': 'Subscription cancelled successfully'}, status=status.HTTP_201_CREATED)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except models.Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'error': str(e)}, status=500)
