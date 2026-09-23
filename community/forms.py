from django import forms

from core.forms import HoneypotMixin, StyledFormMixin

from .models import SUCCESS_STORIES_SLUG, Comment, Post, PostCategory


class PostForm(HoneypotMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Post
        fields = ["category", "title", "body", "external_link", "achievement_type"]
        labels = {
            "body": "Details",
            "achievement_type": "What did you achieve? (success stories only)",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Which US universities waive the PhD application fee?"}),
            "body": forms.Textarea(
                attrs={
                    "rows": 8,
                    "placeholder": "Share details, context or your question. Please don't post personal documents or contact details.",
                }
            ),
            "external_link": forms.URLInput(attrs={"placeholder": "https://official-website.edu/..."}),
        }
        help_texts = {
            "external_link": "Sharing an opportunity? Link to the official source.",
            "achievement_type": "You don't need to reveal universities, amounts or personal details.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = PostCategory.objects.filter(is_active=True)
        self.fields["category"].empty_label = "Choose a category"

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        if len(title) < 8:
            raise forms.ValidationError("Please write a slightly longer, descriptive title.")
        return title

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category and category.slug != SUCCESS_STORIES_SLUG:
            cleaned["achievement_type"] = ""
        return cleaned


class CommentForm(HoneypotMixin, StyledFormMixin, forms.ModelForm):
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Comment
        fields = ["body"]
        labels = {"body": "Your comment"}
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Add a helpful comment…"})}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError("Comment is too short.")
        return body


class CommentEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        labels = {"body": "Edit your comment"}
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}
