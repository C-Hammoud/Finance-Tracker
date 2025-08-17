from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, date
import uuid
from .firestore_models import ConsumptionFS as Consumption
from django.conf import settings

CURRENCY_CHOICES = [
    ("USD", "US Dollar"),
    ("LBP", "Lebanese Lira"),
    ("SAR", "Saudi Riyal"),
]

TYPE_CHOICES = [
    ("market", "Market"),
    ("transport", "Transport"),
    ("food", "Food"),
    ("other", "Other"),
]

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

class ConsumptionCreateForm(forms.Form):
    date = forms.DateField(required=True, initial=date.today, widget=forms.DateInput(attrs={"type": "date"}))
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial="USD")
    consumption_type = forms.ChoiceField(choices=TYPE_CHOICES, initial="market")
    note = forms.CharField(widget=forms.Textarea, required=False)

    def save(self, created_by=None):
        data = self.cleaned_data
        c = Consumption(
            pk=str(uuid.uuid4()),
            date=data["date"],
            amount=Decimal(str(data["amount"])),
            currency=data["currency"],
            consumption_type=data["consumption_type"],
            note=data.get("note", ""),
            created_by=str(created_by.id) if created_by else None,
            created_at=datetime.utcnow(),
            modified_by=None,
            modified_at=None,
            record_status="active"
        )
        c.save()  # Triggers compute_amount_usd and saves to Firestore
        return c

class ConsumptionEditForm(forms.Form):
    date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date"}))
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES)
    consumption_type = forms.ChoiceField(choices=TYPE_CHOICES)
    note = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance:
            self.initial = {
                "date": instance.date,
                "amount": instance.amount,
                "currency": instance.currency,
                "consumption_type": instance.consumption_type,
                "note": instance.note,
            }

    def save(self, modified_by=None):
        data = self.cleaned_data
        inst = self.instance
        inst.date = data["date"]
        inst.amount = Decimal(str(data["amount"]))
        inst.currency = data["currency"]
        inst.consumption_type = data["consumption_type"]
        inst.note = data.get("note", "")
        inst.modified_by = str(modified_by.id) if modified_by else None
        inst.modified_at = datetime.utcnow()
        inst.save()  # Triggers compute_amount_usd and saves to Firestore
        return inst