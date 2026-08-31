from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.serializers import RegistrationSerializer, UserSerializer
from accounts.throttles import LoginThrottle, RegistrationThrottle


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RegistrationThrottle]


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    @extend_schema(responses=UserSerializer)
    def get_object(self):
        return self.request.user
