from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("join/", views.signup, name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password/reset/sent/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password/reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password/reset/complete/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("verify/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("settings/", views.account_settings, name="settings"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("my-posts/", views.my_posts, name="my_posts"),
    path("saved/", views.saved_items, name="saved"),
    path("members/<slug:handle>/", views.profile, name="profile"),
]
