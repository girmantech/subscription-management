from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('validate-otp/', views.OTPValidationView.as_view(), name='otp_validation'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('me/', views.MeView.as_view(), name='me'),
    path('currencies/', views.CurrencyList.as_view(), name='currency_list'),
    path('products/', views.ProductList.as_view(), name='product_list'),
    path('plans/', views.PlanList.as_view(), name='plan_list'),
    path('plans/<int:product_id>', views.PlanListForProduct.as_view(), name='plan_list_for_product'),
]