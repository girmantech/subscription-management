from django.contrib import admin
from .models import Currency, Customer, Product, ProductPricing, Plan, Invoice, Subscription

# Register your models here.
admin.site.register(Currency)
admin.site.register(Customer)
admin.site.register(Invoice)
admin.site.register(Plan)
admin.site.register(Product)
admin.site.register(ProductPricing)
admin.site.register(Subscription)
