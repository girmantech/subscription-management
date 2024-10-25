from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import auth, currency, invoice, me, plan, product, subscription

urlpatterns = [
    path('signup', auth.Signup.as_view(), name='signup'),
    path('signin', auth.Signin.as_view(), name='signin'),
    path('validate-otp', auth.OTPValidation.as_view(), name='otp_validation'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('me', me.Me.as_view(), name='me'),
    path('currencies', currency.CurrencyList.as_view(), name='currency_list'),
    path('products', product.ProductList.as_view(), name='product_list'),
    path('plans', plan.PlanList.as_view(), name='plan_list'),
    path('plans/<int:product_id>', plan.PlanListForProduct.as_view(), name='plan_list_for_product'),
    path('subscriptions', subscription.Subscription.as_view(), name='subscription'),
    path('subscriptions/upgrade', subscription.UpgradeSubscription.as_view(), name='upgrade_subscription'),
    path('subscriptions/downgrade', subscription.DowngradeSubscription.as_view(), name='downgrade_subscription'),
    path('subscriptions/cancel', subscription.CancelSubscription.as_view(), name='cancel_subscription'),
    path('invoices', invoice.InvoiceList.as_view(), name='invoice_list'),
    path('stripe-webhook', subscription.StripeWebhookView.as_view(), name='stripe_webhook'),
]