import random

from django.utils import timezone

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .. import models
from .. import serializers
from ..utils import generate_refresh_token



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

        if not phone:
            return Response({'error': 'phone number missing'}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
        

class OTPValidation(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        input_otp = request.data.get('otp')

        if not phone:
            return Response({'error': 'phone number missing'}, status=status.HTTP_400_BAD_REQUEST)
        if not input_otp:
            return Response({'error': 'OTP missing'}, status=status.HTTP_400_BAD_REQUEST)

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
                    return Response({"error": "invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

            except models.OTP.DoesNotExist:
                return Response({"error": "OTP not found for the customer"}, status=status.HTTP_404_NOT_FOUND)

        except models.Customer.DoesNotExist:
            return Response({"error": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
