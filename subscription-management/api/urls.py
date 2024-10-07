from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('currencies/', views.CurrencyList.as_view(), name='currency-list'),
    path('products/', views.ProductList.as_view(), name='product-list'),
]