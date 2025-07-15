# expenses/forms.py

from django import forms
from .models import Consumption, Currency
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


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




User = get_user_model()

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Password',
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirm password',
            }),
        }
