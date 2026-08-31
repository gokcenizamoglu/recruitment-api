from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "role", "first_name", "last_name", "date_joined")
        read_only_fields = fields


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("id", "email", "password", "role", "first_name", "last_name")
        read_only_fields = ("id",)

    def validate_email(self, value):
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def to_representation(self, instance):
        return UserSerializer(instance).data
