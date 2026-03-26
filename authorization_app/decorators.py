from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .permissions import (
    has_right,
    has_student_rights,
    has_teacher_rights,
    has_researcher_rights,
    has_admin_rights,
    has_teacher_or_admin_rights,
    has_teacher_or_student_rights
)


def rights_required(test_func):
    def decorator(view_func):
        @login_required(login_url="/auth/login/")
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not test_func(request.user):
                raise PermissionDenied("У вас нет прав для доступа к этой странице.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def roles_required(*allowed_roles):
    def decorator(view_func):
        @login_required(login_url="/auth/login/")
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not has_right(request.user, *allowed_roles):
                raise PermissionDenied("У вас нет прав для доступа к этой странице.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def student_required(view_func):
    return rights_required(has_student_rights)(view_func)


def teacher_required(view_func):
    return rights_required(has_teacher_rights)(view_func)


def researcher_required(view_func):
    return rights_required(has_researcher_rights)(view_func)


def admin_required(view_func):
    return rights_required(has_admin_rights)(view_func)

def teacher_ur_student_required(view_func):
    return rights_required(has_teacher_or_student_rights)(view_func)

def teacher_or_admin_required(view_func):
    return rights_required(has_teacher_or_admin_rights)(view_func)

