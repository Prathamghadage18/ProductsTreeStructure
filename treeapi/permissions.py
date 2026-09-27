"""
Custom permissions and decorators for RBAC implementation.
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import AllowedUser


def allowed_user_required(view_func):
    """
    Decorator that ensures only allowed users (predefined normal users + superusers) can access.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Superusers always allowed
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user is in allowed users list
        if AllowedUser.objects.filter(user=request.user).exists():
            return view_func(request, *args, **kwargs)
        
        return HttpResponseForbidden("You are not authorized to access this page.")
    return wrapper
