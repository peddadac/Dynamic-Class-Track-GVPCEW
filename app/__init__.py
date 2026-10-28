"""Flask application factory for Dynamic Class Track."""

import os
from flask import Flask, render_template
from config import config_by_name
from app.extensions import db, login_manager, csrf, socketio
from app.services.reminder_service import init_scheduler


def create_app(config_name=None):
    """Factory function creating and configuring the Flask application instance."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Ensure required directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["TIMETABLE_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CSV_UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    # Exempt JSON API routes from CSRF for fetch POST requests if desired,
    # or keep CSRF token support in JS
    csrf.exempt("app.api.routes.push_subscribe")
    csrf.exempt("app.api.routes.mark_read")

    # Register blueprints
    from app.main import main_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.faculty import faculty_bp
    from app.student import student_bp
    from app.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    # Global template context processor
    @app.context_processor
    def inject_global_template_vars():
        from flask_login import current_user
        from app.models.notification import Notification

        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

        return {
            "COLLEGE_NAME": app.config.get("COLLEGE_NAME", "Gayatri Vidya Parishad College of Engineering for Women"),
            "COLLEGE_SHORT_NAME": app.config.get("COLLEGE_SHORT_NAME", "GVPCEW"),
            "unread_notifications_count": unread_count,
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template("errors/413.html"), 413

    # Start background scheduler if enabled and not running tests or CLI commands
    if app.config.get("ENABLE_SCHEDULER") and not app.config.get("TESTING"):
        init_scheduler(app)

    return app
