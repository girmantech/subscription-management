from django.contrib import admin
from .models import Currency, Customer, Product, ProductPricing

# Register your models here.
admin.site.register(Currency)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(ProductPricing)
