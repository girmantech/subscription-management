import random

from django.db import connection, transaction
from django.utils import timezone

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


class RegisterView(APIView):
    def post(self, request):
        serializer = serializers.CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        phone = request.data.get('phone')

        try:
            customer = models.Customer.objects.get(phone=phone)

            # otp generation and setting expiry-time-stamp
            otp_code = '{:06d}'.format(random.randint(0, 999999))
            expires_at = int((timezone.now() + timezone.timedelta(minutes=10)).timestamp())

            models.OTP.objects.update_or_create(
                customer=customer,
                defaults={
                    'otp': otp_code,
                    'expires_at': expires_at
                }
            )

            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        

class OTPValidationView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        input_otp = request.data.get('otp')

        try:
            customer = models.Customer.objects.get(phone=phone)

            try:
                otp_record = models.OTP.objects.get(customer=customer)

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


class MeView(APIView):
    def get(self, request):
        return Response(request.customer, status=status.HTTP_200_OK)


class CustomerList(generics.ListCreateAPIView):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerSerializer


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerSerializer


class ProductList(APIView):
    def get(self, request):
        try:
            currency_id = request.customer['currency']
            
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


class PlanList(APIView):
    def get(self, request):
        try:
            currency_id = request.customer['currency']
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        plan.id as plan_id,
                        product.id as product_id,
                        product.name,
                        product.description,
                        price.price,
                        price.currency_id,
                        plan.billing_interval
                    FROM api_plan AS plan
                    LEFT JOIN api_product AS product ON plan.product_id = product.id
                    LEFT JOIN api_productpricing AS price ON product.id = price.product_id
                    WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN price.from_date AND price.to_date
                    AND plan.deleted_at IS NULL AND product.deleted_at IS NULL
                    AND product.deleted_at IS NULL AND price.deleted_at IS NULL
                    AND price.currency_id = %s;
                """, [currency_id])

                results = dictfetchall(cursor)
            
            return Response(results)
    
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class PlanListForProduct(APIView):
    def get(self, request, product_id):
        try:
            currency_id = request.customer['currency']
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        plan.id as plan_id,
                        product.id as product_id,
                        product.name,
                        product.description,
                        price.price,
                        price.currency_id,
                        plan.billing_interval
                    FROM api_plan AS plan
                    LEFT JOIN api_product AS product ON plan.product_id = product.id
                    LEFT JOIN api_productpricing AS price ON product.id = price.product_id
                    WHERE EXTRACT(EPOCH FROM NOW()) BETWEEN price.from_date AND price.to_date
                    AND product.id = %s
                    AND plan.deleted_at IS NULL AND product.deleted_at IS NULL
                    AND product.deleted_at IS NULL AND price.deleted_at IS NULL
                    AND price.currency_id = %s;
                """, [product_id, currency_id])

                results = dictfetchall(cursor)
            
            return Response(results)
    
        except Exception as e:
            return Response({'error': str(e)}, status=500)
