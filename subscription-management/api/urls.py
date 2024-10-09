from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('signup', views.Signup.as_view(), name='signup'),
    path('signin', views.Signin.as_view(), name='signin'),
    path('validate-otp', views.OTPValidation.as_view(), name='otp_validation'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('me', views.Me.as_view(), name='me'),
    path('currencies', views.CurrencyList.as_view(), name='currency_list'),
    path('products', views.ProductList.as_view(), name='product_list'),
    path('plans', views.PlanList.as_view(), name='plan_list'),
    path('plans/<int:product_id>', views.PlanListForProduct.as_view(), name='plan_list_for_product'),
    path('subscriptions', views.Subscription.as_view(), name='subscription'),
    path('subscriptions/activate', views.ActivateSubscription.as_view(), name='activate_subscription'),
    path('subscriptions/upgrade', views.UpgradeSubscription.as_view(), name='upgrade_subscription'),
    path('subscriptions/downgrade', views.DowngradeSubscription.as_view(), name='downgrade_subscription'),
    path('subscriptions/cancel', views.CancelSubscription.as_view(), name='cancel_subscription'),
]