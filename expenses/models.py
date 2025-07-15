from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

User = get_user_model()

class Currency(models.TextChoices):
    USD = 'USD', 'US Dollar'
    LBP = 'LBP', 'Lebanese Lira'
    SAR = 'SAR', 'Saudi Riyal'

class Consumption(models.Model):
    TYPE_CHOICES = [
        ('market', 'Market'),
        ('food', 'Food'),
        ('other', 'Other'),
    ]

    date = models.DateField(
        default=timezone.now,
        editable=True,
        help_text="Date of the expense"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original amount entered in the selected currency"
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        help_text="Currency of the entered amount"
    )
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
        default=Decimal('0.00'),
        help_text="Amount converted to USD for dashboards and totals"
    )
    consumption_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='market'
    )
    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_consumptions'
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_consumptions'
    )
    record_status = models.CharField(max_length=10, default='active')

    class Meta:
        ordering = ['-date']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'

    def save(self, *args, **kwargs):
        rates = getattr(settings, 'EXCHANGE_RATES', {}) or {}
        try:
            rate = Decimal(str(rates.get(self.currency, 1)))
        except Exception:
            rate = Decimal('1')
        amt = self.amount if isinstance(self.amount, Decimal) else Decimal(self.amount or 0)
        self.amount_usd = (amt * rate).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date}: {self.amount} {self.currency} - {self.get_consumption_type_display()}"
