"""Authentication decorators for role-based authorization."""

from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def role_required(*roles):
    """Decorator ensuring current user has one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if current_user.role not in roles:
                flash("You do not have permission to access this resource.", "danger")
                if current_user.role == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif current_user.role == "faculty":
                    return redirect(url_for("faculty.dashboard"))
                elif current_user.role == "student":
                    return redirect(url_for("student.dashboard"))
                return redirect(url_for("main.index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return role_required("admin")(f)


def faculty_required(f):
    return role_required("faculty")(f)


def student_required(f):
    return role_required("student")(f)
