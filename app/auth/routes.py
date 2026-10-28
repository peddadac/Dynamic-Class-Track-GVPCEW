"""Authentication routes for login, logout, and password management."""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.audit import AuditLog
from app.auth.forms import LoginForm, ChangePasswordForm
from app.auth.rate_limiter import check_rate_limit, record_failed_attempt, clear_failed_attempts

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "faculty":
            return redirect(url_for("faculty.dashboard"))
        elif current_user.role == "student":
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("main.index"))

    # Check for role in query string to preselect the portal
    role_param = request.args.get("role", "admin").lower()
    if role_param not in ["admin", "faculty", "student"]:
        role_param = "admin"

    form = LoginForm()
    if request.method == "GET":
        form.role.data = role_param

    if form.validate_on_submit():
        ip = request.remote_addr or "unknown"
        identifier = form.username_or_email.data.strip()
        rate_key = f"{ip}:{identifier}"

        # Rate limit check
        is_allowed, remaining_sec = check_rate_limit(
            rate_key,
            max_attempts=current_app.config.get("LOGIN_RATE_LIMIT_ATTEMPTS", 5),
            window_seconds=current_app.config.get("LOGIN_RATE_LIMIT_WINDOW", 300),
        )
        if not is_allowed:
            flash(
                f"Too many failed login attempts. Please wait {remaining_sec} seconds before trying again.",
                "danger",
            )
            return render_template("auth/login.html", form=form, active_role=form.role.data)

        # Lookup user by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user or not user.check_password(form.password.data):
            record_failed_attempt(rate_key)
            AuditLog.log(
                user_id=user.id if user else None,
                action="failed_login",
                entity_type="User",
                details=f"Failed login attempt for {identifier} on {form.role.data} portal",
                ip_address=ip,
            )
            flash("Invalid credentials. Please verify your username/email and password.", "danger")
            return render_template("auth/login.html", form=form, active_role=form.role.data)

        if not user.is_active:
            flash("Your account has been deactivated. Please contact your college administrator.", "danger")
            return render_template("auth/login.html", form=form, active_role=form.role.data)

        # Check role match
        selected_role = form.role.data
        if user.role != selected_role:
            flash(
                f"Your account is registered as '{user.role.title()}'. Please use the {user.role.title()} Portal to sign in.",
                "warning",
            )
            return render_template("auth/login.html", form=form, active_role=selected_role)

        # Successful login
        clear_failed_attempts(rate_key)
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        login_user(user, remember=form.remember_me.data)
        AuditLog.log(
            user_id=user.id,
            action="login",
            entity_type="User",
            details=f"User {user.username} logged into {user.role} portal",
            ip_address=ip,
        )

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        if user.role == "admin":
            flash(f"Welcome back, Administrator {user.full_name}!", "success")
            return redirect(url_for("admin.dashboard"))
        elif user.role == "faculty":
            flash(f"Welcome, Professor {user.full_name}!", "success")
            return redirect(url_for("faculty.dashboard"))
        elif user.role == "student":
            flash(f"Welcome, {user.full_name}!", "success")
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("main.index"))

    return render_template("auth/login.html", form=form, active_role=form.role.data or role_param)


@auth_bp.route("/login/<role>")
def portal_login(role):
    """Direct route for portal-specific login shortcuts."""
    if role not in ["admin", "faculty", "student"]:
        role = "admin"
    return redirect(url_for("auth.login", role=role))


@auth_bp.route("/logout")
@login_required
def logout():
    role = current_user.role
    name = current_user.full_name
    AuditLog.log(
        user_id=current_user.id,
        action="logout",
        entity_type="User",
        details=f"User {name} logged out",
        ip_address=request.remote_addr,
    )
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login", role=role))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash("Current password entered is incorrect.", "danger")
            return render_template("auth/change_password.html", form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        AuditLog.log(
            user_id=current_user.id,
            action="change_password",
            entity_type="User",
            details="User changed password",
            ip_address=request.remote_addr,
        )
        flash("Your password has been updated successfully.", "success")
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "faculty":
            return redirect(url_for("faculty.dashboard"))
        else:
            return redirect(url_for("student.dashboard"))

    return render_template("auth/change_password.html", form=form)
