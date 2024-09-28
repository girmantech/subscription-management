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



