"""
Forms for Crowdfund application
"""

from django import forms

from decimal import Decimal
from datetime import date, timedelta

from muckrock.crowdfund.models import Crowdfund, CrowdfundPayment


class NumberInput(forms.TextInput):
    """Patches a NumberInput widget on top of the TextInput widget"""
    input_type = 'number'


class CrowdfundForm(forms.ModelForm):
    """Form to confirm enable crowdfunding"""

    fee_rate = Decimal(0.15)

    class Meta:
        model = Crowdfund
        fields = [
            'name',
            'description',
            'payment_required',
            'payment_capped',
            'date_due',
        ]

    payment_required = forms.DecimalField(
        label='Amount',
        help_text='We will add 15% to this amount, which goes towards our operating costs.',
        widget=NumberInput()
    )

    payment_capped = forms.BooleanField(
        label='Limit Amount',
        required=False,
        help_text='If checked, this prevents you from collecting more than your stated amount.',
        widget=forms.CheckboxInput()
    )

    date_due = forms.DateField(
        label='Deadline',
        help_text='Crowdfunding campaigns are limited to a maximum duration of 30 days',
        widget=forms.DateInput()
    )

    def clean_payment_required(self):
        """Add fee to the total crowdfund amount, make sure it isn't zero"""
        amount = self.cleaned_data['payment_required']
        valid_amount = amount > 0
        if not valid_amount:
            raise forms.ValidationError('Amount to crowdfund must be greater than zero.')
        amount += amount * self.fee_rate
        return amount

    def clean_date_due(self):
        """Ensure date is not in the past"""
        deadline = self.cleaned_data['date_due']
        today = date.today()
        after_today = deadline > today
        if not after_today:
            raise forms.ValidationError('Crowdfund deadline must be after today.')
        lte_30_days = deadline - today <= timedelta(30)
        if not lte_30_days:
            raise forms.ValidationError('Crowdfund duration cannot exceed 30 days.')
        return deadline


class CrowdfundPaymentForm(forms.ModelForm):
    """Form to create a payment to a crowdfund"""
    class Meta:
        model = CrowdfundPayment
        fields = ['amount', 'show', 'crowdfund']
        widgets = {
            'amount': NumberInput(),
            'show': forms.CheckboxInput(),
            'crowdfund': forms.HiddenInput()
        }

    def clean_amount(self):
        """Ensure the amount of the payment is greater than zero"""
        amount = self.cleaned_data['amount']
        if not amount > 0:
            raise forms.ValidationError('Cannot contribute zero dollars')
        amount = Decimal(amount)/100
        return amount
