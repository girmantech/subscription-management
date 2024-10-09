from django.db import connection

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .. import models
from ..utils import dictfetchall


class InvoiceList(APIView):
    def get(self, request):
        try:
            customer = models.Customer.objects.get(id=request.customer_id)

            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM api_invoice
                    WHERE customer_id = %s;
                """, [customer.id])
                
                result = dictfetchall(cursor)

            return Response(result, status=status.HTTP_200_OK)
        
        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
