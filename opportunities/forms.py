from django import forms
from django.utils import timezone

from core.forms import HoneypotMixin, StyledFormMixin

from .models import Opportunity


class OpportunitySubmitForm(HoneypotMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = [
            "title",
            "organization",
            "country",
            "opportunity_type",
            "degree_level",
            "field_of_study",
            "funding_type",
            "deadline",
            "deadline_note",
            "description",
            "eligibility",
            "official_source_url",
            "application_url",
            "additional_info",
        ]
        labels = {
            "title": "Opportunity title",
            "opportunity_type": "Type",
            "field_of_study": "Field",
            "funding_type": "Funding",
            "description": "Short description",
            "deadline_note": "Deadline note (if there is no fixed date)",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. PhD Application Fee Waiver for International Students"}),
            "organization": forms.TextInput(attrs={"placeholder": "e.g. University of Example"}),
            "country": forms.TextInput(attrs={"list": "country-list", "placeholder": "e.g. Germany"}),
            "field_of_study": forms.TextInput(attrs={"placeholder": "e.g. Computer Science, or Any field"}),
            "deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "deadline_note": forms.TextInput(attrs={"placeholder": "e.g. Rolling, or Varies by program"}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "eligibility": forms.Textarea(attrs={"rows": 3}),
            "additional_info": forms.Textarea(attrs={"rows": 3}),
            "official_source_url": forms.URLInput(attrs={"placeholder": "https://..."}),
            "application_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }
        help_texts = {
            "official_source_url": "Required. The official university or scholarship page where this information is published.",
            "application_url": "Optional. Direct link to the application portal.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["opportunity_type"].empty_label = "Choose a type"

    def clean_deadline(self):
        deadline = self.cleaned_data.get("deadline")
        if deadline and deadline < timezone.localdate():
            raise forms.ValidationError("This deadline has already passed.")
        return deadline

    def clean_country(self):
        return " ".join((self.cleaned_data.get("country") or "").split())
