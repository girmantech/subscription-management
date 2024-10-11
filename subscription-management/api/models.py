from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=320)
    created_at = models.BigIntegerField()

    def __str__(self):
        return self.code


class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^\d{10}$', message="Phone number must be 10-digit long.")],
        unique=True
    )
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT, null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=12, null=True, blank=True)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class OTP(models.Model):
    phone = phone = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^\d{10}$', message="Phone number must be 10-digit long.")],
        unique=True
    )
    otp = models.CharField(max_length=6)
    expires_at = models.BigIntegerField()

    def is_expired(self):
        current_time = int(timezone.now().timestamp())
        return current_time > self.expires_at

    def __str__(self):
        return f"OTP {self.otp} for {self.customer.phone}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


class ProductPricing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_date = models.BigIntegerField()
    to_date = models.BigIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=3)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT)
    tax_percentage = models.FloatField()
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.currency.code} ({self.from_date} to {self.to_date})"


class Plan(models.Model):
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    billing_interval = models.IntegerField(default=1)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.billing_interval} Month(s)"


class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.RESTRICT)
    plan = models.ForeignKey(Plan, on_delete=models.RESTRICT)
    tax_amount = models.IntegerField()
    total_amount = models.IntegerField()
    
    class InvoiceStatus(models.TextChoices):
        DRAFT = "DRAFT"
        PAID = "PAID"
        UNPAID = "UNPAID"
    
    status = models.CharField(max_length=7, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)

    due_date = models.BigIntegerField()
    paid_at = models.BigIntegerField(blank=True, null=True)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(blank=True, null=True)
    # order_id = models.CharField(max_length=255)

    def __str__(self):
        return f"Invoice {self.id} - {self.customer.name} - {self.plan.product.name} - {self.plan.billing_interval} Month(s) - Total: {self.total_amount}"
    

class Subscription(models.Model):
    class SubscriptionStatus(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"
        UPGRADED = "UPGRADED"
    
    status = models.CharField(max_length=9, choices=SubscriptionStatus.choices, default=SubscriptionStatus.INACTIVE)

    invoice = models.OneToOneField(Invoice, on_delete=models.DO_NOTHING, related_name="subscription")
    customer = models.ForeignKey(Customer, on_delete=models.DO_NOTHING, related_name="subscriptions")
    starts_at = models.BigIntegerField()
    ends_at = models.BigIntegerField()
    renewed_at = models.BigIntegerField(blank=True, null=True)
    renewed_subscription = models.ForeignKey(
        'self', on_delete=models.SET_NULL, blank=True, null=True, related_name="renewed_from"
    )
    downgraded_at = models.BigIntegerField(blank=True, null=True)
    downgraded_to_plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, blank=True, null=True, related_name="downgraded_subscriptions"
    )
    upgraded_at = models.BigIntegerField(blank=True, null=True)
    upgraded_to_plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, blank=True, null=True, related_name="upgraded_subscriptions"
    )

    cancelled_at = models.BigIntegerField(blank=True, null=True)
    created_at = models.BigIntegerField(blank=True, null=True)
    deleted_at = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Subscription {self.id} for Invoice {self.invoice.id} - Status: {self.status}"
