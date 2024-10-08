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
            except Exception as e:
                return Response({'error': 'Currency is not defined for the customer.'}, status=status.HTTP_404_NOT_FOUND)
            
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
            except Exception as e:
                return Response({'error': 'Currency is not defined for the customer.'}, status=status.HTTP_404_NOT_FOUND)
            
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
            except Exception as e:
                return Response({'error': 'Currency is not defined for the customer.'}, status=status.HTTP_404_NOT_FOUND)
            
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
                """, [product_id, currency])

                results = dictfetchall(cursor)
            
            return Response(results)

        except models.Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class Subscription(APIView):
    def post(self, request):
        plan_id = request.data.get('plan_id')

        if not plan_id:
            return Response({"error": "Invalid plan id"}, status=status.HTTP_400_BAD_REQUEST)
