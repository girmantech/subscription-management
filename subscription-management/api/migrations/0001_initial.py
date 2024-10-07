# Generated by Django 5.1.1 on 2024-10-07 23:45

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('code', models.CharField(max_length=3, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=320)),
                ('created_at', models.BigIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=11, unique=True, validators=[django.core.validators.RegexValidator(message='Phone number must be 10-digit long.', regex='^\\d{10}$')])),
                ('email', models.EmailField(max_length=255, unique=True)),
                ('address1', models.CharField(max_length=255)),
                ('address2', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(max_length=255)),
                ('postal_code', models.CharField(max_length=12)),
                ('created_at', models.BigIntegerField()),
                ('deleted_at', models.BigIntegerField(blank=True, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='api.currency')),
            ],
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('billing_interval', models.IntegerField(default=1)),
                ('created_at', models.BigIntegerField()),
                ('deleted_at', models.BigIntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(blank=True, max_length=1000, null=True)),
                ('created_at', models.BigIntegerField()),
                ('deleted_at', models.BigIntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OTP',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='api.customer')),
                ('otp', models.CharField(max_length=6)),
                ('expires_at', models.BigIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tax_amount', models.IntegerField()),
                ('total_amount', models.IntegerField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PAID', 'Paid'), ('UNPAID', 'Unpaid')], default='UNPAID', max_length=7)),
                ('due_date', models.BigIntegerField()),
                ('paid_at', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.BigIntegerField()),
                ('deleted_at', models.BigIntegerField(blank=True, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='api.customer')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='api.plan')),
            ],
        ),
        migrations.AddField(
            model_name='plan',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='api.product'),
        ),
        migrations.CreateModel(
            name='ProductPricing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.BigIntegerField()),
                ('to_date', models.BigIntegerField()),
                ('price', models.IntegerField()),
                ('tax_percentage', models.FloatField()),
                ('created_at', models.BigIntegerField()),
                ('deleted_at', models.BigIntegerField(blank=True, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='api.currency')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.product')),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('UPGRADED', 'Upgraded')], default='INACTIVE', max_length=9)),
                ('starts_at', models.BigIntegerField()),
                ('ends_at', models.BigIntegerField()),
                ('renewed_at', models.BigIntegerField(blank=True, null=True)),
                ('downgraded_at', models.BigIntegerField(blank=True, null=True)),
                ('upgraded_at', models.BigIntegerField(blank=True, null=True)),
                ('cancelled_at', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.BigIntegerField(blank=True, null=True)),
                ('deleted_at', models.BigIntegerField(blank=True, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='subscriptions', to='api.customer')),
                ('downgraded_to_plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='downgraded_subscriptions', to='api.plan')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='subscriptions', to='api.invoice')),
                ('renewed_subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='renewed_from', to='api.subscription')),
                ('upgraded_to_plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='upgraded_subscriptions', to='api.plan')),
            ],
        ),
    ]
