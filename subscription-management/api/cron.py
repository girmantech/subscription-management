from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import Customer
from .utils import (
    dictfetchone, dictfetchall, currency_unit_mapping
)

import os
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

def clean_invoices_and_subscriptions():
    with transaction.atomic():
        # deleting subscriptions where invoice is unpaid past the due time
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE api_subscription AS s
                SET deleted_at = EXTRACT(EPOCH FROM NOW())
                FROM api_invoice i
                WHERE s.invoice_id = i.id
                AND (i.deleted_at IS NOT NULL OR (EXTRACT(EPOCH FROM NOW()) > i.due_at AND i.status <> 'PAID'))
            """)

        # deleting invoice where invoice is unpaid past the due time
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE api_invoice i
                SET deleted_at = EXTRACT(EPOCH FROM NOW())
                WHERE (i.deleted_at IS NOT NULL OR (EXTRACT(EPOCH FROM NOW()) > i.due_at AND i.status <> 'PAID'))
            """)


# log file for storing renewal reminder details
log_file = os.path.join(settings.BASE_DIR, 'logs', 'renewal_reminder_log.txt')

log_dir = os.path.dirname(log_file)
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

def send_renewal_reminders():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""
            WITH latest_reminders AS (
                SELECT DISTINCT ON (r.customer_id) r.customer_id, r.created_at
                FROM api_subscriptionrenewalreminder r
                ORDER BY r.customer_id, r.created_at DESC
            )
            SELECT s.customer_id
            FROM api_subscription s
            LEFT JOIN latest_reminders lr ON lr.customer_id = s.customer_id
            WHERE
                s.ends_at - EXTRACT(EPOCH FROM NOW()) <= EXTRACT(EPOCH FROM INTERVAL '7 days') AND
                s.deleted_at IS NULL AND
                s.status = 'ACTIVE' AND
                s.renewed_at IS NULL AND
                s.cancelled_at IS NULL AND
                (lr.created_at IS NULL OR EXTRACT(EPOCH FROM NOW()) - lr.created_at >= EXTRACT(EPOCH FROM INTERVAL '48 hours'))
            ORDER BY s.customer_id, s.ends_at;
            """)
            results = dictfetchall(cursor)

        for result in results:
            try:
                customer_id = result['customer_id']
                customer = Customer.objects.get(id=customer_id)
                
                # getting next plan id (either downgraded plan or same as current plan)
                with connection.cursor() as cursor:
                    cursor.execute("""
                    WITH current_subscription AS (
                        SELECT s.downgraded_to_plan_id, s.downgraded_at, s.starts_at, s.ends_at, i.plan_id
                        FROM api_subscription s
                        JOIN api_invoice i ON s.invoice_id = i.id
                        WHERE s.customer_id = %s
                        AND EXTRACT(EPOCH FROM NOW()) BETWEEN s.starts_at AND s.ends_at
                        AND s.deleted_at IS NULL
                        AND s.status = 'ACTIVE'
                    )
                    SELECT CASE
                        WHEN downgraded_to_plan_id IS NOT NULL THEN downgraded_to_plan_id
                        ELSE plan_id
                    END AS next_plan_id
                    FROM current_subscription;
                    """, [customer_id])

                    next_plan_id = dictfetchone(cursor)['next_plan_id']

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
                    """, [next_plan_id, customer.currency.code])
                    
                    result = dictfetchone(cursor)

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
                                'description': f'Plan {next_plan_id} for {billing_interval} month(s)',
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
                        """, [customer.id, next_plan_id, tax_amount, total_amount, session.id])

                        result = dictfetchone(cursor)
                        invoice_id = result['id']

                    # creating subscription (inactive)
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO api_subscription (status, invoice_id, customer_id, starts_at, ends_at, created_at)
                            VALUES ('INACTIVE', %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()))
                        """, [invoice_id, customer.id, start_timestamp, end_timestamp])

                    session_url = session.url
                    print(f"Stripe session created for customer {customer_id}: {session_url}")

                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO api_subscriptionrenewalreminder (customer_id, created_at)
                                VALUES (%s, EXTRACT(EPOCH FROM NOW()));
                        """, [customer_id])

                    with open(log_file, "a") as log:
                        log.write(f"customer {customer_id} - session URL: {session_url}\n")

            except Exception as e:
                with open(log_file, "a") as log:
                    log.write(f"error sending renewal reminder for customer {customer_id}: {str(e)}\n")
