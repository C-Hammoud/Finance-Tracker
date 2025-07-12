from django import forms
from .models import Consumption

class ConsumptionForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ['amount', 'consumption_type', 'note']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount',
                'step': '1',        # only allow whole numbers
                'min': '1',         # optional: disallow negatives
                'inputmode': 'numeric',  # better mobile support
            }),
            'consumption_type': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'class': 'form-control'}),
        }
        
class ConsumptionEditForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ['amount','note']   # drop consumption_type entirely
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount',
                'step': '1',        # only allow whole numbers
                'min': '1',         # optional: disallow negatives
                'inputmode': 'numeric',  # better mobile support
            }),
            'note': forms.Textarea(attrs={'class': 'form-control'}),
        }        
