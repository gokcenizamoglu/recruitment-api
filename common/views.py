from django.db import connection
from django.db.utils import OperationalError
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Application and database healthy"),
            503: OpenApiResponse(description="Database unavailable"),
        }
    )
    def get(self, request):
        try:
            connection.ensure_connection()
        except OperationalError:
            return Response(
                {"status": "unhealthy", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "healthy", "database": "reachable"})
