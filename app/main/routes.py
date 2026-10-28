"""Main public blueprint with landing page and portal gateways."""

from flask import Blueprint, render_template, current_app
from app.models.academic import Branch, Section, Subject
from app.models.classroom import Classroom
from app.models.timetable import TimetableVersion

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Professional landing page showcasing the three portals: Admin, Faculty, Student."""
    stats = {
        "branches_count": Branch.query.filter_by(is_active=True).count(),
        "sections_count": Section.query.filter_by(is_active=True).count(),
        "classrooms_count": Classroom.query.filter_by(is_active=True).count(),
        "timetables_count": TimetableVersion.query.filter_by(status="published").count(),
    }
    return render_template(
        "index.html",
        stats=stats,
        college_name=current_app.config.get("COLLEGE_NAME"),
        college_short_name=current_app.config.get("COLLEGE_SHORT_NAME"),
    )
