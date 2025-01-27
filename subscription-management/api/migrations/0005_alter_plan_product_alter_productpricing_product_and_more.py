# Generated by Django 5.1.1 on 2024-10-16 15:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_remove_currency_created_at_remove_upgrade_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='plans', to='api.product'),
        ),
        migrations.AlterField(
            model_name='productpricing',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_pricings', to='api.product'),
        ),
        migrations.CreateModel(
            name='SubscriptionRenewalReminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.BigIntegerField()),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='subscription_renewal_reminders', to='api.customer')),
            ],
        ),
    ]
