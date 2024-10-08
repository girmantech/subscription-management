from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='customer-list'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('validate-otp/', views.OTPValidationView.as_view(), name='otp-validation'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('currencies/', views.CurrencyList.as_view(), name='currency-list'),
    path('products/', views.ProductList.as_view(), name='product-list'),
]