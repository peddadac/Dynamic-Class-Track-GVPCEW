"""Tests for Timetable Section Isolation, Cross-Branch Faculty Scheduling, and Versioning."""

from datetime import datetime, date, time
from app.extensions import db
from app.models.academic import Branch, Section, Subject, FacultyProfile
from app.models.classroom import Classroom
from app.models.timetable import TimetableVersion, TimetableEntry


def test_5_students_cannot_view_another_sections_timetable(client):
    """Req 5: Students must only view timetable of their assigned branch/section."""
    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sec_b = Section.query.filter_by(name="B", branch_id=b_cse.id).first()
    sub_ds = Subject.query.filter_by(code="CS501").first()
    fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
    room = Classroom.query.filter_by(room_number="C-204").first()

    # Create published timetable for Section A
    v_a = TimetableVersion(
        branch_id=b_cse.id,
        academic_year_id=sec_a.academic_year_id,
        semester_id=sec_a.semester_id,
        section_id=sec_a.id,
        version_number=1,
        status="published",
    )
    db.session.add(v_a)
    db.session.flush()

    e_a = TimetableEntry(
        timetable_version_id=v_a.id,
        day_of_week="Monday",
        period_number=1,
        start_time=time(9, 0),
        end_time=time(9, 50),
        subject_id=sub_ds.id,
        faculty_id=fac.id,
        classroom_id=room.id,
        notes="Section A Exclusive Class",
    )
    db.session.add(e_a)
    db.session.commit()

    # Log in as Student B (enrolled in Section B, NOT Section A)
    client.post(
        "/login",
        data={"username_or_email": "student_b", "password": "Student@123", "role": "student"},
    )
    res = client.get("/student/dashboard")
    assert res.status_code == 200
    # Student B should NOT see Section A's class
    assert b"Section A Exclusive Class" not in res.data


def test_6_faculty_see_their_own_classes_across_multiple_branches(client):
    """Req 6: Faculty teaching classes in CSE and ECE see all classes in chronological order."""
    b_cse = Branch.query.filter_by(code="CSE").first()
    b_ece = Branch.query.filter_by(code="ECE").first()
    sec_csea = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sec_ecea = Section.query.filter_by(name="A", branch_id=b_ece.id).first()
    sub_cse = Subject.query.filter_by(code="CS501").first()
    sub_ece = Subject.query.filter_by(code="EC501").first()
    fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
    r204 = Classroom.query.filter_by(room_number="C-204").first()
    r305 = Classroom.query.filter_by(room_number="C-305").first()

    # Published version in CSE
    v_cse = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_csea.academic_year_id, semester_id=sec_csea.semester_id, section_id=sec_csea.id, status="published")
    db.session.add(v_cse)
    db.session.flush()

    e_cse = TimetableEntry(timetable_version_id=v_cse.id, day_of_week="Monday", period_number=1, start_time=time(9, 0), end_time=time(9, 50), subject_id=sub_cse.id, faculty_id=fac.id, classroom_id=r204.id)
    db.session.add(e_cse)

    # Published version in ECE (different branch)
    v_ece = TimetableVersion(branch_id=b_ece.id, academic_year_id=sec_ecea.academic_year_id, semester_id=sec_ecea.semester_id, section_id=sec_ecea.id, status="published")
    db.session.add(v_ece)
    db.session.flush()

    e_ece = TimetableEntry(timetable_version_id=v_ece.id, day_of_week="Monday", period_number=2, start_time=time(9, 50), end_time=time(10, 40), subject_id=sub_ece.id, faculty_id=fac.id, classroom_id=r305.id)
    db.session.add(e_ece)
    db.session.commit()

    # Log in as faculty Dr. Sharma
    client.post("/login", data={"username_or_email": "fac_sharma", "password": "Faculty@123", "role": "faculty"})
    res = client.get("/faculty/schedule")
    assert res.status_code == 200
    # Both CSE and ECE classes must appear on the faculty member's schedule
    assert b"CS501" in res.data
    assert b"EC501" in res.data
    assert b"CSE" in res.data
    assert b"ECE" in res.data


def test_10_unapproved_timetables_remain_hidden_from_users(client):
    """Req 10: Timetable in draft status must never be visible to students or faculty."""
    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sub_ds = Subject.query.filter_by(code="CS501").first()
    fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
    room = Classroom.query.filter_by(room_number="C-204").first()

    # Draft version (unapproved)
    v_draft = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_a.academic_year_id, semester_id=sec_a.semester_id, section_id=sec_a.id, version_number=2, status="draft")
    db.session.add(v_draft)
    db.session.flush()

    e_draft = TimetableEntry(timetable_version_id=v_draft.id, day_of_week="Monday", period_number=3, start_time=time(10, 50), end_time=time(11, 40), subject_id=sub_ds.id, faculty_id=fac.id, classroom_id=room.id, notes="Secret Unapproved Draft Subject")
    db.session.add(e_draft)
    db.session.commit()

    # Student check
    client.post("/login", data={"username_or_email": "student_sneha", "password": "Student@123", "role": "student"})
    res_st = client.get("/student/schedule")
    assert b"Secret Unapproved Draft Subject" not in res_st.data

    # Faculty check
    client.get("/logout")
    client.post("/login", data={"username_or_email": "fac_sharma", "password": "Faculty@123", "role": "faculty"})
    res_fac = client.get("/faculty/schedule")
    assert b"Secret Unapproved Draft Subject" not in res_fac.data


def test_21_new_timetable_versions_do_not_damage_unrelated_sections(client):
    """Req 21: Creating/publishing a new version for Section A does not touch Section B or other terms."""
    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sec_b = Section.query.filter_by(name="B", branch_id=b_cse.id).first()
    sub_ds = Subject.query.filter_by(code="CS501").first()

    # Section B established timetable
    v_b = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_b.academic_year_id, semester_id=sec_b.semester_id, section_id=sec_b.id, version_number=1, status="published")
    db.session.add(v_b)
    db.session.commit()

    # Publish new version for Section A
    v_a = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_a.academic_year_id, semester_id=sec_a.semester_id, section_id=sec_a.id, version_number=1, status="published")
    db.session.add(v_a)
    db.session.commit()

    # Section B must remain published with status unchanged
    sec_b_version = TimetableVersion.query.filter_by(section_id=sec_b.id).first()
    assert sec_b_version.status == "published"
    assert sec_b_version.id == v_b.id
