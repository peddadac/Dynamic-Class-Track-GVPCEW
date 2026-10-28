"""Admin portal routes for comprehensive management of college academic entities and timetables."""

import os
import csv
import io
from datetime import datetime, date, time
from werkzeug.utils import secure_filename
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user
from app.extensions import db
from app.auth.decorators import admin_required
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
from app.models.timetable import (
    TimetableVersion,
    TimetableEntry,
    UploadedTimetableImage,
    RoomChangeHistory,
)
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.services.ocr_service import OCRService
from app.services.timetable_parser import TimetableParser, DEFAULT_PERIOD_SLOTS, DAYS_OF_WEEK
from app.services.timetable_validation import TimetableConflictValidator
from app.services.notification_service import NotificationService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
@admin_required
def require_admin():
    """Ensure all admin routes are strictly restricted to authenticated administrators."""
    pass


# =========================================================================
# DASHBOARD
# =========================================================================
@admin_bp.route("/dashboard")
def dashboard():
    today_name = datetime.utcnow().strftime("%A")
    stats = {
        "total_branches": Branch.query.count(),
        "total_sections": Section.query.count(),
        "total_faculty": FacultyProfile.query.count(),
        "total_students": StudentProfile.query.count(),
        "total_classrooms": Classroom.query.count(),
        "published_timetables": TimetableVersion.query.filter_by(status="published").count(),
        "pending_drafts": TimetableVersion.query.filter_by(status="draft").count(),
        "today_classes": TimetableEntry.query.join(TimetableVersion)
        .filter(TimetableVersion.status == "published", TimetableEntry.day_of_week == today_name)
        .count(),
    }

    recent_uploads = UploadedTimetableImage.query.order_by(UploadedTimetableImage.uploaded_at.desc()).limit(5).all()
    recent_changes = RoomChangeHistory.query.order_by(RoomChangeHistory.change_timestamp.desc()).limit(6).all()
    recent_audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_uploads=recent_uploads,
        recent_changes=recent_changes,
        recent_audits=recent_audits,
    )


# =========================================================================
# BRANCH MANAGEMENT
# =========================================================================
@admin_bp.route("/branches", methods=["GET", "POST"])
def branches():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        is_active = bool(request.form.get("is_active"))

        if not code or not name:
            flash("Branch code and branch name are required.", "danger")
        elif Branch.query.filter_by(code=code).first():
            flash(f"Branch with code '{code}' already exists.", "danger")
        else:
            branch = Branch(code=code, name=name, is_active=is_active)
            db.session.add(branch)
            db.session.commit()
            AuditLog.log(current_user.id, "create_branch", "Branch", branch.id, f"Created branch {code} - {name}")
            flash(f"Branch '{code}' created successfully.", "success")
        return redirect(url_for("admin.branches"))

    all_branches = Branch.query.order_by(Branch.code).all()
    return render_template("admin/branches.html", branches=all_branches)


@admin_bp.route("/branches/<int:branch_id>/edit", methods=["POST"])
def edit_branch(branch_id):
    branch = Branch.query.get_or_404(branch_id)
    name = request.form.get("name", "").strip()
    is_active = bool(request.form.get("is_active"))
    if name:
        branch.name = name
        branch.is_active = is_active
        db.session.commit()
        AuditLog.log(current_user.id, "edit_branch", "Branch", branch.id, f"Updated branch {branch.code}")
        flash(f"Branch '{branch.code}' updated successfully.", "success")
    return redirect(url_for("admin.branches"))


# =========================================================================
# ACADEMIC YEARS & SEMESTERS
# =========================================================================
@admin_bp.route("/academic-terms", methods=["GET", "POST"])
def academic_terms():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_year":
            year_label = request.form.get("year_label", "").strip()
            is_current = bool(request.form.get("is_current"))
            if year_label:
                if is_current:
                    AcademicYear.query.update({AcademicYear.is_current: False})
                ay = AcademicYear(year_label=year_label, is_current=is_current)
                db.session.add(ay)
                db.session.commit()
                flash(f"Academic Year '{year_label}' created.", "success")
        elif action == "set_current_year":
            ay_id = request.form.get("year_id")
            AcademicYear.query.update({AcademicYear.is_current: False})
            target = AcademicYear.query.get(ay_id)
            if target:
                target.is_current = True
                db.session.commit()
                flash(f"Active Academic Year set to '{target.year_label}'.", "success")
        return redirect(url_for("admin.academic_terms"))

    years = AcademicYear.query.order_by(AcademicYear.year_label.desc()).all()
    semesters = Semester.query.order_by(Semester.number).all()
    return render_template("admin/academic_terms.html", years=years, semesters=semesters)


# =========================================================================
# SECTION MANAGEMENT
# =========================================================================
@admin_bp.route("/sections", methods=["GET", "POST"])
def sections():
    if request.method == "POST":
        name = request.form.get("name", "").strip().upper()
        branch_id = request.form.get("branch_id", type=int)
        academic_year_id = request.form.get("academic_year_id", type=int)
        semester_id = request.form.get("semester_id", type=int)

        if not (name and branch_id and academic_year_id and semester_id):
            flash("All section fields are required.", "danger")
        else:
            existing = Section.query.filter_by(
                name=name, branch_id=branch_id, academic_year_id=academic_year_id, semester_id=semester_id
            ).first()
            if existing:
                flash(f"Section '{name}' already exists for this branch and term.", "warning")
            else:
                sec = Section(name=name, branch_id=branch_id, academic_year_id=academic_year_id, semester_id=semester_id)
                db.session.add(sec)
                db.session.commit()
                AuditLog.log(current_user.id, "create_section", "Section", sec.id, f"Created section {sec.display_name}")
                flash(f"Section '{sec.display_name}' created successfully.", "success")
        return redirect(url_for("admin.sections"))

    all_sections = Section.query.join(Branch).order_by(Branch.code, Section.name).all()
    branches_list = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    years_list = AcademicYear.query.order_by(AcademicYear.year_label.desc()).all()
    semesters_list = Semester.query.order_by(Semester.number).all()

    return render_template(
        "admin/sections.html",
        sections=all_sections,
        branches=branches_list,
        years=years_list,
        semesters=semesters_list,
    )


# =========================================================================
# CLASSROOM MANAGEMENT
# =========================================================================
@admin_bp.route("/classrooms", methods=["GET", "POST"])
def classrooms():
    if request.method == "POST":
        room_number = request.form.get("room_number", "").strip().upper()
        building_block = request.form.get("building_block", "").strip()
        capacity = request.form.get("capacity", 60, type=int)
        is_active = bool(request.form.get("is_active", True))

        if not room_number:
            flash("Room number is required.", "danger")
        elif Classroom.query.filter_by(room_number=room_number).first():
            flash(f"Classroom '{room_number}' already exists.", "warning")
        else:
            room = Classroom(
                room_number=room_number,
                building_block=building_block or "Main Block",
                capacity=capacity,
                is_active=is_active,
            )
            db.session.add(room)
            db.session.commit()
            AuditLog.log(current_user.id, "create_classroom", "Classroom", room.id, f"Created classroom {room_number}")
            flash(f"Classroom '{room_number}' created successfully.", "success")
        return redirect(url_for("admin.classrooms"))

    all_rooms = Classroom.query.order_by(Classroom.room_number).all()
    return render_template("admin/classrooms.html", classrooms=all_rooms)


@admin_bp.route("/classrooms/<int:room_id>/toggle", methods=["POST"])
def toggle_classroom(room_id):
    room = Classroom.query.get_or_404(room_id)
    room.is_active = not room.is_active
    db.session.commit()
    status_str = "activated" if room.is_active else "deactivated"
    AuditLog.log(current_user.id, "toggle_classroom", "Classroom", room.id, f"Classroom {room.room_number} {status_str}")
    flash(f"Classroom '{room.room_number}' {status_str}.", "info")
    return redirect(url_for("admin.classrooms"))


# =========================================================================
# SUBJECT MANAGEMENT
# =========================================================================
@admin_bp.route("/subjects", methods=["GET", "POST"])
def subjects():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        branch_id = request.form.get("branch_id", type=int)
        semester_id = request.form.get("semester_id", type=int)

        if not (code and name and branch_id and semester_id):
            flash("All subject fields are required.", "danger")
        else:
            existing = Subject.query.filter_by(code=code, branch_id=branch_id, semester_id=semester_id).first()
            if existing:
                flash(f"Subject '{code}' already exists for this branch and semester.", "warning")
            else:
                subj = Subject(code=code, name=name, branch_id=branch_id, semester_id=semester_id)
                db.session.add(subj)
                db.session.commit()
                AuditLog.log(current_user.id, "create_subject", "Subject", subj.id, f"Created subject {code} - {name}")
                flash(f"Subject '{code} - {name}' created.", "success")
        return redirect(url_for("admin.subjects"))

    all_subjects = Subject.query.join(Branch).order_by(Branch.code, Subject.code).all()
    branches_list = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    semesters_list = Semester.query.order_by(Semester.number).all()
    return render_template(
        "admin/subjects.html",
        subjects=all_subjects,
        branches=branches_list,
        semesters=semesters_list,
    )


# =========================================================================
# FACULTY MANAGEMENT
# =========================================================================
@admin_bp.route("/faculty", methods=["GET", "POST"])
def faculty():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        faculty_id = request.form.get("faculty_id", "").strip().upper()
        branch_id = request.form.get("branch_id", type=int)
        phone = request.form.get("phone", "").strip()
        designation = request.form.get("designation", "Assistant Professor").strip()

        if not (full_name and email and username and password and faculty_id and branch_id):
            flash("All required faculty fields must be filled.", "danger")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("A user with this username or email already exists.", "warning")
        elif FacultyProfile.query.filter_by(faculty_id=faculty_id).first():
            flash(f"Faculty ID '{faculty_id}' is already registered.", "warning")
        else:
            user = User(
                username=username,
                email=email,
                role="faculty",
                full_name=full_name,
                is_active=True,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            profile = FacultyProfile(
                user_id=user.id,
                faculty_id=faculty_id,
                department_branch_id=branch_id,
                phone=phone,
                designation=designation,
                is_active=True,
            )
            db.session.add(profile)
            db.session.commit()
            AuditLog.log(current_user.id, "create_faculty", "FacultyProfile", profile.id, f"Added faculty {faculty_id} ({full_name})")
            flash(f"Faculty member '{full_name}' ({faculty_id}) registered successfully.", "success")
        return redirect(url_for("admin.faculty"))

    all_faculty = FacultyProfile.query.join(User).order_by(FacultyProfile.faculty_id).all()
    branches_list = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    return render_template("admin/faculty.html", faculty_list=all_faculty, branches=branches_list)


# =========================================================================
# STUDENT MANAGEMENT & CSV IMPORT
# =========================================================================
@admin_bp.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        roll_number = request.form.get("roll_number", "").strip().upper()
        branch_id = request.form.get("branch_id", type=int)
        academic_year_id = request.form.get("academic_year_id", type=int)
        semester_id = request.form.get("semester_id", type=int)
        section_id = request.form.get("section_id", type=int)

        if not (full_name and email and username and password and roll_number and section_id):
            flash("All required student fields must be completed.", "danger")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already in use.", "warning")
        elif StudentProfile.query.filter_by(roll_number=roll_number).first():
            flash(f"Roll Number '{roll_number}' already registered.", "warning")
        else:
            user = User(
                username=username,
                email=email,
                role="student",
                full_name=full_name,
                is_active=True,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            profile = StudentProfile(
                user_id=user.id,
                roll_number=roll_number,
                branch_id=branch_id,
                academic_year_id=academic_year_id,
                semester_id=semester_id,
                section_id=section_id,
                is_active=True,
            )
            db.session.add(profile)
            db.session.commit()
            AuditLog.log(current_user.id, "create_student", "StudentProfile", profile.id, f"Added student {roll_number}")
            flash(f"Student '{full_name}' ({roll_number}) registered successfully.", "success")
        return redirect(url_for("admin.students"))

    all_students = StudentProfile.query.join(User).order_by(StudentProfile.roll_number).all()
    branches_list = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    years_list = AcademicYear.query.order_by(AcademicYear.year_label.desc()).all()
    semesters_list = Semester.query.order_by(Semester.number).all()
    sections_list = Section.query.filter_by(is_active=True).order_by(Section.name).all()

    return render_template(
        "admin/students.html",
        students=all_students,
        branches=branches_list,
        years=years_list,
        semesters=semesters_list,
        sections=sections_list,
    )


@admin_bp.route("/students/import-csv", methods=["POST"])
def import_students_csv():
    """CSV Import for bulk student creation with row-by-row validation and error reporting."""
    file = request.files.get("csv_file")
    if not file or not file.filename:
        flash("Please select a CSV file to upload.", "danger")
        return redirect(url_for("admin.students"))

    if not file.filename.lower().endswith(".csv"):
        flash("Invalid file format. Please upload a .csv file.", "danger")
        return redirect(url_for("admin.students"))

    success_count = 0
    errors = []

    try:
        stream = io.StringIO(file.stream.read().decode("UTF-8", errors="replace"))
        reader = csv.DictReader(stream)

        required_cols = {"roll_number", "full_name", "email", "username", "password", "branch_code", "section_name"}
        if not required_cols.issubset(set(col.strip().lower() for col in (reader.fieldnames or []))):
            flash(f"CSV header must contain: {', '.join(required_cols)}", "danger")
            return redirect(url_for("admin.students"))

        current_ay = AcademicYear.query.filter_by(is_current=True).first() or AcademicYear.query.first()
        current_sem = Semester.query.filter_by(number=5).first() or Semester.query.first()

        for row_idx, row in enumerate(reader, start=2):
            try:
                roll = row.get("roll_number", "").strip().upper()
                name = row.get("full_name", "").strip()
                email = row.get("email", "").strip().lower()
                uname = row.get("username", "").strip() or roll.lower()
                pwd = row.get("password", "").strip() or "Student@123"
                b_code = row.get("branch_code", "").strip().upper()
                sec_name = row.get("section_name", "").strip().upper()

                if not (roll and name and email and b_code and sec_name):
                    errors.append(f"Row {row_idx}: Missing required fields.")
                    continue

                branch = Branch.query.filter_by(code=b_code).first()
                if not branch:
                    errors.append(f"Row {row_idx}: Branch '{b_code}' not found.")
                    continue

                section = Section.query.filter_by(branch_id=branch.id, name=sec_name).first()
                if not section:
                    errors.append(f"Row {row_idx}: Section '{sec_name}' in branch '{b_code}' not found.")
                    continue

                if User.query.filter((User.username == uname) | (User.email == email)).first():
                    errors.append(f"Row {row_idx}: Username '{uname}' or email '{email}' already exists.")
                    continue

                if StudentProfile.query.filter_by(roll_number=roll).first():
                    errors.append(f"Row {row_idx}: Roll number '{roll}' already exists.")
                    continue

                user = User(username=uname, email=email, role="student", full_name=name, is_active=True)
                user.set_password(pwd)
                db.session.add(user)
                db.session.flush()

                profile = StudentProfile(
                    user_id=user.id,
                    roll_number=roll,
                    branch_id=branch.id,
                    academic_year_id=section.academic_year_id or current_ay.id,
                    semester_id=section.semester_id or current_sem.id,
                    section_id=section.id,
                    is_active=True,
                )
                db.session.add(profile)
                success_count += 1
            except Exception as row_err:
                errors.append(f"Row {row_idx}: Error processing row ({row_err})")

        db.session.commit()
        AuditLog.log(current_user.id, "import_students_csv", "StudentProfile", None, f"Imported {success_count} students")
        flash(f"Successfully imported {success_count} students.", "success")
        if errors:
            flash(f"Encountered {len(errors)} issues during import: " + " | ".join(errors[:5]), "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to process CSV file: {e}", "danger")

    return redirect(url_for("admin.students"))


# =========================================================================
# TIMETABLE IMAGE UPLOAD & OCR EXTRACTION
# =========================================================================
@admin_bp.route("/timetables")
def timetables():
    """List of all timetable versions."""
    all_versions = TimetableVersion.query.order_by(TimetableVersion.created_at.desc()).all()
    return render_template("admin/timetables_list.html", versions=all_versions)


@admin_bp.route("/timetables/upload", methods=["GET", "POST"])
def upload_timetable():
    if request.method == "POST":
        branch_id = request.form.get("branch_id", type=int)
        academic_year_id = request.form.get("academic_year_id", type=int)
        semester_id = request.form.get("semester_id", type=int)
        section_id = request.form.get("section_id", type=int)
        timetable_type = request.form.get("timetable_type", "regular")
        file = request.files.get("timetable_file")

        if not (branch_id and academic_year_id and semester_id and section_id and file and file.filename):
            flash("All fields and a valid timetable image file are required.", "danger")
            return redirect(url_for("admin.upload_timetable"))

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "pdf"}):
            flash("Unsupported file format. Please upload PNG, JPG, JPEG, or PDF.", "danger")
            return redirect(url_for("admin.upload_timetable"))

        # Save uploaded file safely
        safe_name = f"tt_{branch_id}_{section_id}_{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
        upload_dir = current_app.config["TIMETABLE_UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_name)
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        # Create UploadedTimetableImage record
        upload_record = UploadedTimetableImage(
            filename=safe_name,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type or f"image/{ext}",
            branch_id=branch_id,
            academic_year_id=academic_year_id,
            semester_id=semester_id,
            section_id=section_id,
            uploaded_by_id=current_user.id,
            status="processing",
        )
        db.session.add(upload_record)
        db.session.flush()

        # Execute OCR and parsing
        try:
            ocr_service = OCRService(tesseract_cmd=current_app.config.get("TESSERACT_CMD"))
            ocr_result = ocr_service.extract_text(file_path)
            raw_text = ocr_result.get("raw_text", "")
            upload_record.extracted_raw_text = raw_text

            # Fetch known domain entities for parsing
            known_subjects = Subject.query.filter_by(branch_id=branch_id, semester_id=semester_id).all()
            if not known_subjects:
                known_subjects = Subject.query.filter_by(branch_id=branch_id).all()
            known_faculty = FacultyProfile.query.filter_by(is_active=True).all()
            known_classrooms = Classroom.query.filter_by(is_active=True).all()

            parser = TimetableParser(
                known_subjects=known_subjects,
                known_faculty=known_faculty,
                known_classrooms=known_classrooms,
            )
            parsed_entries = parser.parse_raw_text(raw_text)

            # Determine next version number for this section
            latest_v = (
                TimetableVersion.query.filter_by(section_id=section_id)
                .order_by(TimetableVersion.version_number.desc())
                .first()
            )
            v_num = (latest_v.version_number + 1) if latest_v else 1

            # Create draft TimetableVersion
            version = TimetableVersion(
                branch_id=branch_id,
                academic_year_id=academic_year_id,
                semester_id=semester_id,
                section_id=section_id,
                version_number=v_num,
                status="draft",
                timetable_type=timetable_type,
                effective_date=date.today(),
                created_by_id=current_user.id,
                notes=f"Extracted from {file.filename}",
            )
            db.session.add(version)
            db.session.flush()

            upload_record.timetable_version_id = version.id
            upload_record.status = "parsed"

            # Create draft TimetableEntry rows
            for pe in parsed_entries:
                st_time = TimetableConflictValidator.parse_time(pe["start_time"])
                et_time = TimetableConflictValidator.parse_time(pe["end_time"])
                entry = TimetableEntry(
                    timetable_version_id=version.id,
                    day_of_week=pe["day"],
                    period_number=pe["period"],
                    start_time=st_time or time(9, 0),
                    end_time=et_time or time(9, 50),
                    subject_id=pe.get("subject_id"),
                    faculty_id=pe.get("faculty_id"),
                    classroom_id=pe.get("classroom_id"),
                    status="Upcoming",
                    is_uncertain=pe.get("is_uncertain", False),
                    confidence_score=pe.get("confidence", 1.0),
                    notes=pe.get("raw_cell", ""),
                )
                db.session.add(entry)

            db.session.commit()
            AuditLog.log(
                current_user.id,
                "upload_timetable",
                "UploadedTimetableImage",
                upload_record.id,
                f"Uploaded timetable {file.filename} for Section {section_id}",
            )
            flash(
                "Timetable image uploaded and processed successfully! Please review and verify the extracted entries below.",
                "info",
            )
            return redirect(url_for("admin.review_timetable", version_id=version.id))

        except Exception as ocr_err:
            db.session.rollback()
            upload_record.status = "failed"
            upload_record.error_message = str(ocr_err)
            db.session.commit()
            flash(f"Timetable processing error: {ocr_err}", "danger")
            return redirect(url_for("admin.upload_timetable"))

    branches_list = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    years_list = AcademicYear.query.order_by(AcademicYear.year_label.desc()).all()
    semesters_list = Semester.query.order_by(Semester.number).all()
    sections_list = Section.query.filter_by(is_active=True).order_by(Section.name).all()

    return render_template(
        "admin/upload_timetable.html",
        branches=branches_list,
        years=years_list,
        semesters=semesters_list,
        sections=sections_list,
    )


# =========================================================================
# EDITABLE REVIEW INTERFACE & PUBLISH WORKFLOW
# =========================================================================
@admin_bp.route("/timetables/<int:version_id>/review", methods=["GET", "POST"])
def review_timetable(version_id):
    """
    Editable review table matching the prompt requirements:
    Columns: Day | Period | Start | End | Subject | Faculty | Room | Status
    Allows inline editing of uncertain fields, saving drafts, and publishing.
    """
    version = TimetableVersion.query.get_or_404(version_id)
    subjects_list = Subject.query.filter_by(branch_id=version.branch_id).order_by(Subject.code).all()
    faculty_list = FacultyProfile.query.filter_by(is_active=True).all()
    classrooms_list = Classroom.query.filter_by(is_active=True).order_by(Classroom.room_number).all()

    if request.method == "POST":
        action = request.form.get("action")

        # Save updated entries from form table
        entry_ids = request.form.getlist("entry_id[]")
        for eid in entry_ids:
            entry = TimetableEntry.query.get(eid)
            if entry and entry.timetable_version_id == version.id:
                s_id = request.form.get(f"subject_{eid}", type=int)
                f_id = request.form.get(f"faculty_{eid}", type=int)
                r_id = request.form.get(f"classroom_{eid}", type=int)
                st_str = request.form.get(f"start_time_{eid}")
                et_str = request.form.get(f"end_time_{eid}")

                entry.subject_id = s_id if s_id else None
                entry.faculty_id = f_id if f_id else None
                entry.classroom_id = r_id if r_id else None
                if st_str:
                    entry.start_time = TimetableConflictValidator.parse_time(st_str)
                if et_str:
                    entry.end_time = TimetableConflictValidator.parse_time(et_str)
                entry.is_uncertain = False  # cleared once verified by admin

        db.session.commit()

        if action == "save_draft":
            flash("Timetable draft changes saved successfully.", "success")
            return redirect(url_for("admin.review_timetable", version_id=version.id))

        elif action == "publish":
            # Conflict validation
            entries_data = [
                {
                    "day": e.day_of_week,
                    "period": e.period_number,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                    "classroom_id": e.classroom_id,
                    "faculty_id": e.faculty_id,
                    "section_id": version.section_id,
                }
                for e in version.entries
            ]
            is_valid, conflicts = TimetableConflictValidator.validate_timetable_grid(
                entries_data, section_id=version.section_id, exclude_version_id=version.id
            )

            # Allow force override with admin confirmation flag if needed, but alert conflicts
            force_publish = request.form.get("force_publish") == "true"
            if not is_valid and not force_publish:
                flash(f"Cannot publish: {len(conflicts)} scheduling conflicts detected! Check conflict summary below.", "danger")
                return render_template(
                    "admin/review_timetable.html",
                    version=version,
                    subjects=subjects_list,
                    faculty=faculty_list,
                    classrooms=classrooms_list,
                    conflicts=conflicts,
                )

            # Archive older published versions of this section so there is only one active published version
            older_published = TimetableVersion.query.filter_by(
                section_id=version.section_id,
                status="published",
            ).all()
            for op in older_published:
                op.status = "archived"

            version.status = "published"
            version.approved_at = datetime.utcnow()
            db.session.commit()

            # Targeted notifications dispatch
            NotificationService.notify_timetable_published(version)
            AuditLog.log(
                current_user.id,
                "publish_timetable",
                "TimetableVersion",
                version.id,
                f"Published timetable {version.title}",
            )
            flash(f"Timetable for {version.title} published successfully! Dashboards have been updated.", "success")
            return redirect(url_for("admin.view_timetable", version_id=version.id))

    # Pre-run conflict check for review display
    entries_data = [
        {
            "day": e.day_of_week,
            "period": e.period_number,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "classroom_id": e.classroom_id,
            "faculty_id": e.faculty_id,
            "section_id": version.section_id,
        }
        for e in version.entries
    ]
    _, initial_conflicts = TimetableConflictValidator.validate_timetable_grid(entries_data, section_id=version.section_id)

    return render_template(
        "admin/review_timetable.html",
        version=version,
        subjects=subjects_list,
        faculty=faculty_list,
        classrooms=classrooms_list,
        conflicts=initial_conflicts,
    )


@admin_bp.route("/timetables/<int:version_id>/view")
def view_timetable(version_id):
    """Clean view of a timetable grid organized by Day and Period."""
    version = TimetableVersion.query.get_or_404(version_id)
    grid = {day: {} for day in DAYS_OF_WEEK}
    for entry in version.entries:
        grid.setdefault(entry.day_of_week, {})[entry.period_number] = entry

    return render_template(
        "admin/view_timetable.html",
        version=version,
        grid=grid,
        days=DAYS_OF_WEEK,
        periods=DEFAULT_PERIOD_SLOTS,
    )


# =========================================================================
# MANUAL TIMETABLE CREATOR
# =========================================================================
@admin_bp.route("/timetables/create-manual", methods=["GET", "POST"])
def create_manual_timetable():
    if request.method == "POST":
        branch_id = request.form.get("branch_id", type=int)
        academic_year_id = request.form.get("academic_year_id", type=int)
        semester_id = request.form.get("semester_id", type=int)
        section_id = request.form.get("section_id", type=int)

        latest_v = (
            TimetableVersion.query.filter_by(section_id=section_id)
            .order_by(TimetableVersion.version_number.desc())
            .first()
        )
        v_num = (latest_v.version_number + 1) if latest_v else 1

        version = TimetableVersion(
            branch_id=branch_id,
            academic_year_id=academic_year_id,
            semester_id=semester_id,
            section_id=section_id,
            version_number=v_num,
            status="draft",
            timetable_type="regular",
            effective_date=date.today(),
            created_by_id=current_user.id,
            notes="Manually created schedule",
        )
        db.session.add(version)
        db.session.flush()

        # Prepopulate standard periods for 6 days
        for day in DAYS_OF_WEEK:
            for slot in DEFAULT_PERIOD_SLOTS:
                entry = TimetableEntry(
                    timetable_version_id=version.id,
                    day_of_week=day,
                    period_number=slot["period"],
                    start_time=TimetableConflictValidator.parse_time(slot["start"]),
                    end_time=TimetableConflictValidator.parse_time(slot["end"]),
                    status="Upcoming",
                    is_uncertain=False,
                )
                db.session.add(entry)

        db.session.commit()
        flash("Draft timetable grid initialized. Fill in subjects and classrooms below.", "info")
        return redirect(url_for("admin.review_timetable", version_id=version.id))

    branches_list = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    years_list = AcademicYear.query.order_by(AcademicYear.year_label.desc()).all()
    semesters_list = Semester.query.order_by(Semester.number).all()
    sections_list = Section.query.filter_by(is_active=True).order_by(Section.name).all()
    return render_template(
        "admin/create_manual.html",
        branches=branches_list,
        years=years_list,
        semesters=semesters_list,
        sections=sections_list,
    )


# =========================================================================
# CLASSROOM CHANGE MANAGEMENT
# =========================================================================
@admin_bp.route("/room-changes", methods=["GET", "POST"])
def room_changes():
    """
    Change classroom workflow:
    1. Select timetable entry.
    2. Select new classroom.
    3. Server verifies room availability and scheduling conflicts.
    4. Save transactionally.
    5. Record room change history.
    6. Deliver targeted alerts to affected faculty and section's students.
    """
    if request.method == "POST":
        entry_id = request.form.get("entry_id", type=int)
        new_room_id = request.form.get("new_classroom_id", type=int)
        reason = request.form.get("reason", "").strip()

        entry = TimetableEntry.query.get_or_404(entry_id)
        new_room = Classroom.query.get_or_404(new_room_id)
        old_room = entry.classroom
        old_room_name = old_room.room_number if old_room else "Unassigned"

        if entry.classroom_id == new_room_id:
            flash(f"Class is already assigned to {new_room.room_number}.", "warning")
            return redirect(url_for("admin.room_changes"))

        # Conflict check for new classroom at this period & day
        conflict_query = (
            TimetableEntry.query.join(TimetableVersion)
            .filter(
                TimetableVersion.status == "published",
                TimetableEntry.day_of_week == entry.day_of_week,
                TimetableEntry.classroom_id == new_room_id,
                TimetableEntry.id != entry.id,
                TimetableEntry.status != "Cancelled",
            )
            .all()
        )

        has_conflict = False
        for ex in conflict_query:
            if TimetableConflictValidator.times_overlap(entry.start_time, entry.end_time, ex.start_time, ex.end_time):
                has_conflict = True
                conflict_sec = ex.version.section.display_name if ex.version and ex.version.section else "Another class"
                flash(
                    f"Conflict: Room {new_room.room_number} is already in use by {conflict_sec} "
                    f"on {entry.day_of_week} ({ex.start_time.strftime('%I:%M %p')}-{ex.end_time.strftime('%I:%M %p')}).",
                    "danger",
                )
                break

        if not has_conflict:
            # Record change history
            history = RoomChangeHistory(
                timetable_entry_id=entry.id,
                old_classroom_id=entry.classroom_id or new_room_id,
                new_classroom_id=new_room_id,
                changed_by_id=current_user.id,
                reason=reason or "Administrative room adjustment",
                effective_date=date.today(),
            )
            entry.classroom_id = new_room_id
            db.session.add(history)
            db.session.commit()

            # Send targeted alerts to faculty and section students
            NotificationService.notify_room_change(entry, old_room_name, new_room.room_number, reason)
            AuditLog.log(
                current_user.id,
                "change_classroom",
                "RoomChangeHistory",
                history.id,
                f"Changed room for Entry {entry.id} from {old_room_name} to {new_room.room_number}",
            )
            flash(
                f"Classroom successfully updated to {new_room.room_number}. Targeted notifications delivered to affected faculty and students.",
                "success",
            )
        return redirect(url_for("admin.room_changes"))

    # Active published entries for selection
    published_entries = (
        TimetableEntry.query.join(TimetableVersion)
        .filter(TimetableVersion.status == "published")
        .order_by(TimetableEntry.day_of_week, TimetableEntry.period_number)
        .all()
    )
    classrooms_list = Classroom.query.filter_by(is_active=True).order_by(Classroom.room_number).all()
    recent_history = RoomChangeHistory.query.order_by(RoomChangeHistory.change_timestamp.desc()).limit(20).all()

    return render_template(
        "admin/room_changes.html",
        entries=published_entries,
        classrooms=classrooms_list,
        history=recent_history,
    )


# =========================================================================
# CONFLICT ANALYZER REPORT
# =========================================================================
@admin_bp.route("/conflicts")
def conflicts_report():
    """Generates a complete conflict audit report across all active published schedules."""
    published_entries = (
        TimetableEntry.query.join(TimetableVersion)
        .filter(TimetableVersion.status == "published", TimetableEntry.status != "Cancelled")
        .all()
    )

    room_conflicts = []
    faculty_conflicts = []

    for i in range(len(published_entries)):
        e1 = published_entries[i]
        for j in range(i + 1, len(published_entries)):
            e2 = published_entries[j]
            if e1.day_of_week != e2.day_of_week:
                continue

            if TimetableConflictValidator.times_overlap(e1.start_time, e1.end_time, e2.start_time, e2.end_time):
                if e1.classroom_id and e1.classroom_id == e2.classroom_id:
                    room_conflicts.append((e1, e2))
                if e1.faculty_id and e1.faculty_id == e2.faculty_id:
                    faculty_conflicts.append((e1, e2))

    return render_template(
        "admin/conflicts.html",
        room_conflicts=room_conflicts,
        faculty_conflicts=faculty_conflicts,
        total_conflicts=len(room_conflicts) + len(faculty_conflicts),
    )


# =========================================================================
# NOTIFICATION BROADCAST & AUDIT LOGS
# =========================================================================
@admin_bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        target_role = request.form.get("target_role", "all")

        if title and message:
            query = User.query.filter_by(is_active=True)
            if target_role in ["faculty", "student", "admin"]:
                query = query.filter_by(role=target_role)
            target_users = query.all()

            for u in target_users:
                NotificationService.create_notification(
                    user_id=u.id,
                    title=title,
                    message=message,
                    notification_type="general",
                )
            AuditLog.log(current_user.id, "broadcast_notification", "Notification", None, f"Broadcast: {title}")
            flash(f"Notification broadcast sent to {len(target_users)} users.", "success")
        return redirect(url_for("admin.notifications"))

    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(30).all()
    return render_template("admin/notifications.html", notifications=recent_notifications)


@admin_bp.route("/audit-logs")
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template("admin/audit_logs.html", logs=logs)
