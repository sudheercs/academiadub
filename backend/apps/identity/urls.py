from django.urls import path

from .views import (CookieTokenRefreshView, CsrfTokenView, CurrentUserView,
                    CustomTokenObtainPairView, LogoutView,
                    UserRegistrationView)

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf-token"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
]
