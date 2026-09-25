from functools import cached_property

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class DegreeLevel(models.TextChoices):
    UNDERGRADUATE = "undergraduate", "Undergraduate"
    MASTERS = "masters", "Master's"
    PHD = "phd", "PhD"
    POSTDOC = "postdoctoral", "Postdoctoral"
    OTHER = "other", "Other"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Admin/staff accounts only. The public website has no member accounts.
    (Some fields are kept from the earlier version so no existing data is dropped.)
    """

    username = None
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=120)
    handle = models.SlugField(max_length=60, unique=True, help_text="Public profile URL name.")
    email_verified = models.BooleanField(default=False)

    # Moderation
    warning_count = models.PositiveSmallIntegerField(default=0)
    suspended_until = models.DateTimeField(null=True, blank=True)
    suspension_reason = models.CharField(max_length=255, blank=True)

    # Marks accounts created by `load_demo_data` so they can be removed easily.
    is_demo = models.BooleanField(default=False, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if not self.handle:
            base = slugify(self.full_name or self.email.split("@")[0])[:50] or "member"
            handle, n = base, 2
            while User.objects.filter(handle=handle).exclude(pk=self.pk).exists():
                handle, n = f"{base}-{n}", n + 1
            self.handle = handle
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.full_name or "Member"

    @property
    def initials(self):
        parts = [p for p in self.display_name.split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "M"

    @property
    def is_suspended(self):
        return bool(self.suspended_until and self.suspended_until > timezone.now())

    @cached_property
    def is_moderator(self):
        return self.is_superuser or self.groups.filter(name="Moderator").exists()


def profile_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"profile_photos/{instance.user_id}.{ext}"


class Profile(models.Model):
    """
    LEGACY (earlier version with member accounts). Not used by the website any
    more; kept only so the existing database table is not dropped without your say-so.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    photo = models.ImageField(
        upload_to=profile_photo_path,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    bio = models.TextField(max_length=500, blank=True)
    country = models.CharField(max_length=80, blank=True)
    institution = models.CharField("current university / institution", max_length=150, blank=True)
    field_of_study = models.CharField(max_length=120, blank=True)
    degree_level = models.CharField(max_length=20, choices=DegreeLevel.choices, blank=True)
    interests = models.CharField("academic / research interests", max_length=255, blank=True)

    show_country = models.BooleanField("show my country publicly", default=True)
    show_institution = models.BooleanField("show my institution publicly", default=False)
    show_academic_details = models.BooleanField(
        "show my field, degree level and interests publicly", default=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.display_name}"
