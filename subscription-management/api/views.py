from django.db import connection, transaction
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .models import Currency
from .serializers import CurrencySerializer
from .utils import dictfetchone, dictfetchall


class CurrencyList(ListAPIView):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class ProductList(APIView):
    def get(self, request):
        try:
            # random value for testing (to be obtained later using bearer access token)
            customer_id = 1
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT currency_id
                    FROM api_customer
                    WHERE id = %s;
                """, [customer_id])

                currency_id = dictfetchone(cursor)['currency_id']
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        product.id as product_id,
                        product.name,
                        product.description,
                        price.price,
                        price.currency_id
                    FROM api_product AS product
                    LEFT JOIN api_productpricing AS price ON product.id = price.product_id
                    WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN price.from_date AND price.to_date
                    AND product.deleted_at IS NULL AND price.deleted_at IS NULL AND price.currency_id = %s;
                """, [currency_id])

                results = dictfetchall(cursor)
            
            return Response(results)
    
        except Exception as e:
            return Response({'error': str(e)}, status=500)
