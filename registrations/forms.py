from django import forms

from .countries import COUNTRIES
from .models import CommunityRegistration, CurrentLevel

COUNTRY_CHOICES = [("", "Select your country")] + [(c, c) for c in COUNTRIES] + [("Other", "Other")]
LEVEL_CHOICES = [("", "Select your level")] + list(CurrentLevel.choices)


class RegistrationForm(forms.ModelForm):
    country = forms.ChoiceField(choices=COUNTRY_CHOICES)
    current_level = forms.ChoiceField(choices=LEVEL_CHOICES, label="Current Level")
    # Honeypot: hidden from people, filled in by simple bots.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}))

    class Meta:
        model = CommunityRegistration
        fields = ["full_name", "email", "country", "current_level", "field_of_study"]
        labels = {"full_name": "Full Name", "email": "Email Address", "field_of_study": "Field of Study"}
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Enter your full name", "autocomplete": "name"}),
            "email": forms.EmailInput(
                attrs={"placeholder": "Enter your email address", "autocomplete": "email", "inputmode": "email"}
            ),
            "field_of_study": forms.TextInput(attrs={"placeholder": "e.g. Computer Science"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("full_name", "email", "country", "current_level"):
            self.fields[name].required = True

    def validate_unique(self):
        """Duplicate emails are handled in the view (the link is re-sent instead of showing an error)."""

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_field_of_study(self):
        return " ".join((self.cleaned_data.get("field_of_study") or "").split())

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Submission rejected.")
        return ""
