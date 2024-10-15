from django.db import connection, transaction

from .utils import dictfetchall


def clean_invoices_and_subscriptions():
    with transaction.atomic():
        # deleting subscriptions where invoice is unpaid past the due time
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE api_subscription AS s
                SET deleted_at = EXTRACT(EPOCH FROM NOW())
                FROM api_invoice i
                WHERE s.invoice_id = i.id
                AND i.deleted_at IS NOT NULL OR (EXTRACT(EPOCH FROM NOW()) > i.due_date AND i.status = 'DRAFT')
            """)

        # deleting invoice where invoice is unpaid past the due time
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE api_invoice i
                SET deleted_at = EXTRACT(EPOCH FROM NOW())
                WHERE (i.deleted_at IS NOT NULL OR (EXTRACT(EPOCH FROM NOW()) > i.due_date AND i.status = 'DRAFT'))
            """)
