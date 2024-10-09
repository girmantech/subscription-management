from django.forms.models import model_to_dict

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .. import models
from .. import serializers


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
