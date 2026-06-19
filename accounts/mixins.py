from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class GroupRequiredMixin(LoginRequiredMixin):
    """Restrict a class-based view to users in any of the specified groups.

    Set group_required to a string or list of group names on the subclass.
    Unauthenticated users are redirected to LOGIN_URL; wrong-group users get 403.
    """
    group_required = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        groups = self.group_required
        if isinstance(groups, str):
            groups = [groups]
        if not request.user.groups.filter(name__in=groups).exists():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
