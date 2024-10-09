from django.db import connection

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .. import models
from ..utils import dictfetchall


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
