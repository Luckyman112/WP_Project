from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Anyone may read; only the author may change or delete a tasting."""

    message = "Only the author can modify this tasting."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return str(obj.author_id) == str(request.user.pk)
