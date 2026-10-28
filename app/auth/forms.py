"""Authentication forms with WTForms and CSRF validation."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    username_or_email = StringField(
        "Username or Email",
        validators=[DataRequired(message="Username or email is required."), Length(min=3, max=120)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
    )
    role = SelectField(
        "Login Portal",
        choices=[("admin", "Admin Portal"), ("faculty", "Faculty Portal"), ("student", "Student Portal")],
        validators=[DataRequired()],
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField(
        "Current Password",
        validators=[DataRequired()],
    )
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=6, message="Password must be at least 6 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Update Password")
