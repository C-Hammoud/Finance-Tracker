from django.db import models
from django.contrib.auth.models import User

class Consumption(models.Model):
    TYPE_CHOICES = [
        ('market', 'Market'),
        ('food', 'Food'),
        ('other', 'Other'),
    ]

    amount = models.IntegerField()
    consumption_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='market')
    note = models.TextField(blank=True, null=True)
    date = models.DateField(auto_now_add=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_consumptions')
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='modified_consumptions')
    record_status = models.CharField(max_length=10, default='active')
