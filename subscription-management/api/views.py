from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from .models import Currency
from .serializers import CurrencySerializer


class CurrencyList(ListAPIView):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
