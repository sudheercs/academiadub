from django.conf import settings
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from academiadub.throttles import LoginRateThrottle

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


def set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        "access_token",
        access_token,
        max_age=15 * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(
        "access_token",
        path="/",
        samesite="Lax",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        samesite="Lax",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    return response


class CsrfTokenView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        response = Response({"csrfToken": get_token(request._request)})
        response.set_cookie(
            "csrftoken",
            get_token(request._request),
            secure=not settings.DEBUG,
            httponly=False,
            samesite="Lax",
            path="/",
        )
        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        SessionAuthentication().enforce_csrf(request)
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")
            if access_token and refresh_token:
                set_auth_cookies(response, access_token, refresh_token)
                response.data = {"detail": "Logged in successfully."}
        return response


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        headers = self.get_success_headers(serializer.data)
        response_data = {
            "message": "User registered successfully",
            "email": user.email,
            "status": user.status,
        }
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class LogoutView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        SessionAuthentication().enforce_csrf(request)
        response = Response(
            {"detail": "Logged out successfully."}, status=status.HTTP_200_OK
        )
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        return clear_auth_cookies(response)


class CookieTokenRefreshView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            raise InvalidToken("Refresh token cookie is missing.")

        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["access"]
        refresh_token = serializer.validated_data.get("refresh", raw_refresh)
        response = Response({"detail": "Token refreshed."}, status=status.HTTP_200_OK)
        return set_auth_cookies(response, access_token, refresh_token)


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
