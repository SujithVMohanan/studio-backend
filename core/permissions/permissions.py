from rest_framework.permissions import BasePermission

from apps.users.models import User


class _RolePermission(BasePermission):
    role: str

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.is_superuser or user.role == self.role


class IsStaffRole(_RolePermission):
    role = User.Role.STAFF
    message = "Staff access required."


class IsMemberRole(_RolePermission):
    role = User.Role.MEMBER
    message = "Member access required."
