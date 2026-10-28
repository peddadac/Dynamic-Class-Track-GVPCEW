"""Tests for Timetable Image Upload, OCR Extraction, Inline Correction, and Publishing."""

import io
from datetime import time
from PIL import Image, ImageDraw
from app.extensions import db
from app.models.academic import Branch, Section, Subject, FacultyProfile
from app.models.classroom import Classroom
from app.models.timetable import TimetableVersion, TimetableEntry, UploadedTimetableImage


def create_sample_timetable_image():
    """Generates an in-memory sample timetable image."""
    img = Image.new("RGB", (800, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "GVPCEW TIMETABLE CSE-A", fill=(0, 0, 0))
    draw.text((20, 60), "Monday | CS501 / GVP-FAC-01 / C-204", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_7_and_22_file_upload_validation_and_security(client):
    """Req 7 & 22: Reject unsupported file extensions (e.g. .exe, .sh) and execute security sanitization."""
    # Log in as admin
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()

    # Attempt to upload malicious/unsupported script
    bad_file = (io.BytesIO(b"malicious payload"), "exploit.exe")
    res = client.post(
        "/admin/timetables/upload",
        data={
            "branch_id": b_cse.id,
            "academic_year_id": sec_a.academic_year_id,
            "semester_id": sec_a.semester_id,
            "section_id": sec_a.id,
            "timetable_file": bad_file,
        },
        follow_redirects=True,
    )
    assert b"Unsupported file format" in res.data or b"danger" in res.data


def test_8_ocr_extraction_produces_reviewable_draft(client):
    """Req 8: Image upload triggers OCR and creates a reviewable draft version."""
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()

    img_buf = create_sample_timetable_image()
    valid_file = (img_buf, "test_timetable.png")

    res = client.post(
        "/admin/timetables/upload",
        data={
            "branch_id": b_cse.id,
            "academic_year_id": sec_a.academic_year_id,
            "semester_id": sec_a.semester_id,
            "section_id": sec_a.id,
            "timetable_type": "regular",
            "timetable_file": valid_file,
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Review & Correct Extracted Timetable" in res.data

    # Verify draft version created in database
    draft = TimetableVersion.query.filter_by(section_id=sec_a.id, status="draft").first()
    assert draft is not None
    assert len(draft.entries) > 0


def test_9_and_11_extracted_data_corrected_and_published_updates_dashboards(client):
    """Req 9 & 11: Admin can update extracted cell values, save draft, and publish."""
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sub_ds = Subject.query.filter_by(code="CS501").first()
    fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
    r204 = Classroom.query.filter_by(room_number="C-204").first()
    r305 = Classroom.query.filter_by(room_number="C-305").first()

    # Create draft version
    version = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_a.academic_year_id, semester_id=sec_a.semester_id, section_id=sec_a.id, version_number=1, status="draft")
    db.session.add(version)
    db.session.flush()

    entry = TimetableEntry(timetable_version_id=version.id, day_of_week="Monday", period_number=1, start_time=time(9, 0), end_time=time(9, 50), subject_id=sub_ds.id, faculty_id=fac.id, classroom_id=r204.id, is_uncertain=True)
    db.session.add(entry)
    db.session.commit()

    # Admin corrects classroom to C-305 and publishes
    post_data = {
        "action": "publish",
        "entry_id[]": [str(entry.id)],
        f"subject_{entry.id}": sub_ds.id,
        f"faculty_{entry.id}": fac.id,
        f"classroom_{entry.id}": r305.id,
        f"start_time_{entry.id}": "09:00",
        f"end_time_{entry.id}": "09:50",
    }
    res = client.post(f"/admin/timetables/{version.id}/review", data=post_data, follow_redirects=True)
    assert res.status_code == 200

    # Verify status changed to published
    updated_v = TimetableVersion.query.get(version.id)
    assert updated_v.status == "published"
    updated_e = TimetableEntry.query.get(entry.id)
    assert updated_e.classroom_id == r305.id
    assert updated_e.is_uncertain is False

    # Verify Student Sneha in Section A now sees this published class in C-305
    client.get("/logout")
    client.post("/login", data={"username_or_email": "student_sneha", "password": "Student@123", "role": "student"})
    res_st = client.get("/student/schedule")
    assert b"C-305" in res_st.data
    assert b"CS501" in res_st.data
