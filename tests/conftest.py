"""Pytest fixtures for testing Dynamic Class Track with in-memory database."""

import pytest
import os
import shutil
from datetime import datetime, date, time
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.academic import (
    Branch,
    AcademicYear,
    Semester,
    Section,
    Subject,
    FacultyProfile,
    StudentProfile,
)
from app.models.classroom import Classroom
from app.models.timetable import TimetableVersion, TimetableEntry, RoomChangeHistory
from app.models.notification import Notification


@pytest.fixture(scope="session")
def app():
    """Create Flask test application configured for testing."""
    os.environ["FLASK_ENV"] = "testing"
    test_app = create_app("testing")

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()

    # Clean up test uploads directory if created
    test_uploads = test_app.config.get("UPLOAD_FOLDER")
    if test_uploads and os.path.exists(test_uploads):
        shutil.rmtree(test_uploads, ignore_errors=True)


@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures database tables are clean and reseeded for each test function."""
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed standard academic entities
        b_cse = Branch(code="CSE", name="Computer Science and Engineering", is_active=True)
        b_ece = Branch(code="ECE", name="Electronics and Communication Engineering", is_active=True)
        db.session.add_all([b_cse, b_ece])
        db.session.flush()

        ay = AcademicYear(year_label="2025-2026", is_current=True)
        db.session.add(ay)
        db.session.flush()

        s5 = Semester(number=5, name="Semester 5", is_active=True)
        db.session.add(s5)
        db.session.flush()

        sec_csea = Section(name="A", branch_id=b_cse.id, academic_year_id=ay.id, semester_id=s5.id, is_active=True)
        sec_cseb = Section(name="B", branch_id=b_cse.id, academic_year_id=ay.id, semester_id=s5.id, is_active=True)
        sec_ecea = Section(name="A", branch_id=b_ece.id, academic_year_id=ay.id, semester_id=s5.id, is_active=True)
        db.session.add_all([sec_csea, sec_cseb, sec_ecea])
        db.session.flush()

        # Classrooms
        r204 = Classroom(room_number="C-204", building_block="CSE Block", capacity=70, is_active=True)
        r305 = Classroom(room_number="C-305", building_block="R&D Block", capacity=65, is_active=True)
        db.session.add_all([r204, r305])
        db.session.flush()

        # Subjects
        sub_ds = Subject(code="CS501", name="Data Structures", branch_id=b_cse.id, semester_id=s5.id)
        sub_dsp = Subject(code="EC501", name="Digital Signal Processing", branch_id=b_ece.id, semester_id=s5.id)
        db.session.add_all([sub_ds, sub_dsp])
        db.session.flush()

        # Admin user
        admin = User(username="admin_test", email="admin@test.com", role="admin", full_name="Admin Test", is_active=True)
        admin.set_password("Admin@123")
        db.session.add(admin)

        # Faculty user
        fac_user = User(username="fac_sharma", email="sharma@test.com", role="faculty", full_name="Dr. Ananya Sharma", is_active=True)
        fac_user.set_password("Faculty@123")
        db.session.add(fac_user)
        db.session.flush()

        fac_profile = FacultyProfile(
            user_id=fac_user.id,
            faculty_id="GVP-FAC-01",
            department_branch_id=b_cse.id,
            designation="Associate Professor",
            is_active=True,
        )
        db.session.add(fac_profile)

        # Student 1 in CSE-A
        st1_user = User(username="student_sneha", email="sneha@test.com", role="student", full_name="Sneha Reddy", is_active=True)
        st1_user.set_password("Student@123")
        db.session.add(st1_user)
        db.session.flush()

        st1_profile = StudentProfile(
            user_id=st1_user.id,
            roll_number="22L31A0501",
            branch_id=b_cse.id,
            academic_year_id=ay.id,
            semester_id=s5.id,
            section_id=sec_csea.id,
            is_active=True,
        )
        db.session.add(st1_profile)

        # Student 2 in CSE-B (different section)
        st2_user = User(username="student_b", email="student_b@test.com", role="student", full_name="Student B", is_active=True)
        st2_user.set_password("Student@123")
        db.session.add(st2_user)
        db.session.flush()

        st2_profile = StudentProfile(
            user_id=st2_user.id,
            roll_number="22L31A0580",
            branch_id=b_cse.id,
            academic_year_id=ay.id,
            semester_id=s5.id,
            section_id=sec_cseb.id,
            is_active=True,
        )
        db.session.add(st2_profile)

        db.session.commit()
        yield
