from django import forms


class HoneypotMixin:
    """
    Adds an invisible 'website' field. Humans never see it; simple bots fill
    every field. Any value in it rejects the submission.
    """

    honeypot_field = "website"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.honeypot_field] = forms.CharField(
            required=False,
            label="Leave this field empty",
            widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
        )

    def clean_website(self):
        value = self.cleaned_data.get(self.honeypot_field)
        if value:
            raise forms.ValidationError("Submission rejected.")
        return value


class StyledFormMixin:
    """Applies the site's Tailwind input classes to every widget."""

    input_class = "form-input"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "form-checkbox")
            elif isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                continue
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "form-file")
            else:
                widget.attrs.setdefault("class", self.input_class)
