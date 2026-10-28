"""Application entry point for Dynamic Class Track."""

import os
from app import create_app
from app.extensions import socketio, db
from cli import init_db_command, create_admin_command, seed_data_command

env_name = os.environ.get("FLASK_ENV", "development")
app = create_app(env_name)

# Register CLI commands with the Flask app
app.cli.add_command(init_db_command)
app.cli.add_command(create_admin_command)
app.cli.add_command(seed_data_command)


@app.shell_context_processor
def make_shell_context():
    from app.models import (
        User,
        Branch,
        AcademicYear,
        Semester,
        Section,
        Subject,
        FacultyProfile,
        StudentProfile,
        Classroom,
        TimetableVersion,
        TimetableEntry,
        UploadedTimetableImage,
        RoomChangeHistory,
        Notification,
        AuditLog,
    )
    return {
        "db": db,
        "User": User,
        "Branch": Branch,
        "AcademicYear": AcademicYear,
        "Semester": Semester,
        "Section": Section,
        "Subject": Subject,
        "FacultyProfile": FacultyProfile,
        "StudentProfile": StudentProfile,
        "Classroom": Classroom,
        "TimetableVersion": TimetableVersion,
        "TimetableEntry": TimetableEntry,
        "UploadedTimetableImage": UploadedTimetableImage,
        "RoomChangeHistory": RoomChangeHistory,
        "Notification": Notification,
        "AuditLog": AuditLog,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Pass CLI commands like init-db, seed-data, create-admin to Flask CLI
        app.cli()
    else:
        from app.services.reminder_service import init_scheduler
        init_scheduler(app)
        port = int(os.environ.get("PORT", 5000))
        # SocketIO provides real-time websockets with seamless polling fallback
        socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
