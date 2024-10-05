from django.db import models

# Create your models here.
class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=320)
    created_at = models.BigIntegerField()

    def __str__(self):
        return self.code


class Customer(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=320)
    phone = models.CharField(max_length=32)
    email = models.CharField(max_length=320)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=12)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


class ProductPricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_date = models.BigIntegerField()
    to_date = models.BigIntegerField()
    price = models.IntegerField()
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT)
    tax_percentage = models.FloatField()
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.currency.code} ({self.from_date} to {self.to_date})"


class Plan(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    billing_interval = models.IntegerField(default=1)
    created_at = models.BigIntegerField()
    deleted_at = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.billing_interval} Month(s)"


class Invoice(models.Model):
    id = models.BigAutoField(primary_key=True)
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

    def __str__(self):
        return f"Invoice {self.id} - {self.customer.name} - {self.plan.product.name} - {self.plan.billing_interval} Month(s) - Total: {self.total_amount}"
    

class Subscription(models.Model):
    id = models.BigAutoField(primary_key=True)

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"
        UPGRADED = "UPGRADED"
    
    status = models.CharField(max_length=9, choices=SubscriptionStatus.choices, default=SubscriptionStatus.INACTIVE)

    invoice = models.ForeignKey(Invoice, on_delete=models.DO_NOTHING, related_name="subscriptions")
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