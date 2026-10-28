"""Tests for Admin Management operations: Branches, Sections, Classrooms, Subjects, and CSV Import."""

import io
from app.extensions import db
from app.models.academic import Branch, Section, Subject, StudentProfile, FacultyProfile
from app.models.classroom import Classroom
from app.models.user import User


def test_admin_branch_and_section_management(client):
    """Verify admin can create branches and sections."""
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    # Create new branch
    res_b = client.post(
        "/admin/branches",
        data={"code": "MECH", "name": "Mechanical Engineering", "is_active": "on"},
        follow_redirects=True,
    )
    assert res_b.status_code == 200
    assert Branch.query.filter_by(code="MECH").first() is not None

    # Create new section
    b_mech = Branch.query.filter_by(code="MECH").first()
    sec_a = Section.query.first()
    res_sec = client.post(
        "/admin/sections",
        data={
            "name": "A",
            "branch_id": b_mech.id,
            "academic_year_id": sec_a.academic_year_id,
            "semester_id": sec_a.semester_id,
        },
        follow_redirects=True,
    )
    assert res_sec.status_code == 200
    assert Section.query.filter_by(branch_id=b_mech.id, name="A").first() is not None


def test_admin_classroom_and_subject_management(client):
    """Verify admin can add classrooms and subjects."""
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    # Add classroom
    res_rm = client.post(
        "/admin/classrooms",
        data={"room_number": "C-401", "building_block": "R&D Block", "capacity": 80, "is_active": "on"},
        follow_redirects=True,
    )
    assert res_rm.status_code == 200
    assert Classroom.query.filter_by(room_number="C-401").first() is not None

    # Add subject
    b_cse = Branch.query.filter_by(code="CSE").first()
    sec = Section.query.first()
    res_sub = client.post(
        "/admin/subjects",
        data={"code": "CS505", "name": "Software Engineering", "branch_id": b_cse.id, "semester_id": sec.semester_id},
        follow_redirects=True,
    )
    assert res_sub.status_code == 200
    assert Subject.query.filter_by(code="CS505").first() is not None


def test_admin_student_csv_bulk_import(client):
    """Verify CSV import creates students with validation and handles errors."""
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    csv_content = (
        "roll_number,full_name,email,username,password,branch_code,section_name\n"
        "22L31A0515,Harika Varma,harika@test.com,student_harika,Student@123,CSE,A\n"
        "22L31A0516,Geetha Rao,geetha@test.com,student_geetha,Student@123,CSE,A\n"
    )
    csv_file = (io.BytesIO(csv_content.encode("utf-8")), "students.csv")

    res = client.post("/admin/students/import-csv", data={"csv_file": csv_file}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Successfully imported 2 students" in res.data

    # Verify student exists in database
    st = StudentProfile.query.filter_by(roll_number="22L31A0515").first()
    assert st is not None
    assert st.user.username == "student_harika"
