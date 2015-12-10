# encoding: utf-8
from django.forms import ModelForm, Form, ImageField, DecimalField, CharField, FileInput

from . import models

class NewCoffeeDrinkerForm(ModelForm):
    class Meta:
        model = models.CoffeeDrinker
        exclude = ("active", "deposit", "prefill", "note")

class CoffeeDrinkerForm(ModelForm):
    class Meta:
        model = models.CoffeeDrinker
        exclude = ("deposit",)

class ManualSheetUpload(Form):
    sheet = ImageField(label="Sheet", help_text="Upload single sheets as JPG/PNG", widget=FileInput(attrs={ "accept": "image/*", "capture": "camera" }))

class DepositForm(Form):
    amount = DecimalField(label="Amount", help_text="How much to deposit?")
    description = CharField(label="Description", help_text="Details to include in the transaction list", required=False)

class BankAccountingEntryForm(ModelForm):
    class Meta:
        model = models.BankAccountingEntry
        exclude = ("coffee_drinker",)
        widgets = {
            "attachment": FileInput(attrs={ "accept": "image/*", "capture": "camera" }),
        }
