from io import BytesIO

from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from core.forms import HoneypotMixin, StyledFormMixin

from .models import Profile, User

MAX_PHOTO_BYTES = 2 * 1024 * 1024


class SignupForm(HoneypotMixin, StyledFormMixin, forms.ModelForm):
    """Deliberately short: name, email, password. Everything else is optional later."""

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters. Avoid common passwords.",
    )
    agree = forms.BooleanField(
        label="I agree to the Terms of Use and Community Guidelines",
        required=True,
    )

    class Meta:
        model = User
        fields = ["full_name", "email"]
        labels = {"full_name": "Full name", "email": "Email address"}
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try logging in.")
        return email

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        if len(name) < 2:
            raise forms.ValidationError("Please enter your name.")
        return name

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class EmailLoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label="Email address", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"})
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class StyledPasswordResetForm(StyledFormMixin, PasswordResetForm):
    pass


class StyledSetPasswordForm(StyledFormMixin, SetPasswordForm):
    pass


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class AccountSettingsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name"]
        labels = {"full_name": "Display name"}


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "photo",
            "bio",
            "country",
            "institution",
            "field_of_study",
            "degree_level",
            "interests",
            "show_country",
            "show_institution",
            "show_academic_details",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "maxlength": 500}),
            "country": forms.TextInput(attrs={"list": "country-list", "autocomplete": "country-name"}),
        }
        help_texts = {
            "bio": "A few sentences about you (optional, max 500 characters).",
            "photo": "JPG, PNG or WEBP, up to 2 MB. It will be resized to a small square-friendly image.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.PROFILE_PHOTO_UPLOADS_ENABLED:
            del self.fields["photo"]

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        self._processed_photo = None
        if photo and getattr(photo, "content_type", None):  # a new upload
            if photo.size > MAX_PHOTO_BYTES:
                raise forms.ValidationError("Please upload an image smaller than 2 MB.")
            try:
                photo.seek(0)
                image = Image.open(photo)
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((400, 400))
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=85)
            except (UnidentifiedImageError, OSError):
                raise forms.ValidationError("That file could not be read as an image.")
            self._processed_photo = buffer.getvalue()
        return photo

    def save(self, commit=True):
        old_name = Profile.objects.filter(pk=self.instance.pk).values_list("photo", flat=True).first()
        photo = self.cleaned_data.get("photo") if "photo" in self.fields else None
        profile = super().save(commit=False)
        storage = profile.photo.storage

        processed = getattr(self, "_processed_photo", None)
        if photo is False and old_name:  # "clear" was ticked
            storage.delete(old_name)
            profile.photo = ""
        elif processed:
            if old_name:
                storage.delete(old_name)
            profile.photo.save(f"{profile.user_id}.jpg", ContentFile(processed), save=False)

        if commit:
            profile.save()
        return profile
