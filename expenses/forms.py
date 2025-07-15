# expenses/forms.py

from django import forms
from .models import Consumption, Currency

class ConsumptionCreateForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = [
            'date',
            'consumption_type',
            'amount',
            'currency',
            'note',
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'consumption_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'inputmode': 'decimal',
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional note…',
            }),
        }


class ConsumptionEditForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = [
            'amount',
            'currency',
            'note',
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'inputmode': 'decimal',
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional note…',
            }),
        }
