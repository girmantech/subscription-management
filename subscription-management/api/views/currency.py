from rest_framework import generics

from .. import models
from .. import serializers


class CurrencyList(generics.ListAPIView):
    queryset = models.Currency.objects.all()
    serializer_class = serializers.CurrencySerializer
