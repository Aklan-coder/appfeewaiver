from django import forms

from core.forms import StyledFormMixin

from .models import Report


class ReportForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details"]
        labels = {"reason": "Why are you reporting this?", "details": "Anything else moderators should know? (optional)"}
        widgets = {
            "reason": forms.RadioSelect,
            "details": forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        }


class ResolveReportForm(forms.Form):
    ACTIONS = [
        ("dismiss", "Dismiss report (no action needed)"),
        ("remove", "Remove the content"),
        ("remove_warn", "Remove the content and warn the author"),
        ("remove_suspend", "Remove the content and suspend the author for 7 days"),
    ]
    action = forms.ChoiceField(choices=ACTIONS, widget=forms.RadioSelect)
    note = forms.CharField(
        required=False,
        max_length=255,
        label="Note (sent to the author with a warning/suspension)",
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
