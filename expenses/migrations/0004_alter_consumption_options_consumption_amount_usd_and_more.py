# Generated by Django 5.2.4 on 2025-07-15 17:47

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_alter_consumption_amount'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='consumption',
            options={'ordering': ['-date'], 'verbose_name': 'Expense', 'verbose_name_plural': 'Expenses'},
        ),
        migrations.AddField(
            model_name='consumption',
            name='amount_usd',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), editable=False, help_text='Amount converted to USD for dashboards and totals', max_digits=12),
        ),
        migrations.AddField(
            model_name='consumption',
            name='currency',
            field=models.CharField(choices=[('USD', 'US Dollar'), ('LBP', 'Lebanese Lira'), ('SAR', 'Saudi Riyal')], default='USD', help_text='Currency of the entered amount', max_length=3),
        ),
        migrations.AlterField(
            model_name='consumption',
            name='amount',
            field=models.DecimalField(decimal_places=2, help_text='Original amount entered in the selected currency', max_digits=10),
        ),
    ]
