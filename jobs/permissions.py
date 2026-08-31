from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User


class IsEmployer(BasePermission):
    message = "Only employers may perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.EMPLOYER


class IsCandidate(BasePermission):
    message = "Only candidates may perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.CANDIDATE


class IsEmployerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == User.Role.EMPLOYER


class IsJobOwnerOrReadOnly(BasePermission):
    message = "You may only modify your own jobs."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.employer_id == request.user.id
