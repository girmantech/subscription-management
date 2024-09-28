from django.contrib import admin
from .models import Currency, Customer, Product

# Register your models here.
admin.site.register(Currency)
admin.site.register(Customer)
admin.site.register(Product)
