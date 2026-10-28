"""CLI commands for database initialization, secure admin creation, and college demo data seeding."""

import click
from datetime import datetime, date, time
from flask.cli import with_appcontext
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
from app.models.timetable import (
    TimetableVersion,
    TimetableEntry,
    RoomChangeHistory,
)
from app.models.notification import Notification
from app.models.audit import AuditLog


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initializes all database tables."""
    db.create_all()
    click.echo("[SUCCESS] Database tables initialized successfully.")


@click.command("create-admin")
@click.option("--username", prompt="Admin username", default="admin", help="Admin login username")
@click.option("--email", prompt="Admin email", default="admin@gvpcew.ac.in", help="Admin email address")
@click.option("--full-name", prompt="Admin full name", default="Administrator", help="Admin full display name")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
@with_appcontext
def create_admin_command(username, email, full_name, password):
    """Securely creates an administrator account without exposing hardcoded credentials."""
    existing = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing:
        click.echo(f"[ERROR] User with username '{username}' or email '{email}' already exists.")
        return

    admin_user = User(
        username=username.strip(),
        email=email.strip().lower(),
        role="admin",
        full_name=full_name.strip(),
        is_active=True,
    )
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()

    AuditLog.log(
        user_id=admin_user.id,
        action="create_admin_cli",
        entity_type="User",
        entity_id=admin_user.id,
        details=f"Admin {username} created via CLI",
    )
    click.echo(f"[SUCCESS] Administrator '{username}' ({email}) created successfully!")


@click.command("seed-data")
@with_appcontext
def seed_data_command():
    """Seeds the database with GVPCEW branches, classrooms, faculty, students, and sample timetables."""
    click.echo("Seeding database with Gayatri Vidya Parishad College of Engineering for Women starter data...")

    # 1. Branches
    branches_data = [
        ("CSE", "Computer Science and Engineering"),
        ("CSM", "Computer Science and Engineering (AI & ML)"),
        ("ECE", "Electronics and Communication Engineering"),
        ("EEE", "Electrical and Electronics Engineering"),
        ("IT", "Information Technology"),
        ("MECH", "Mechanical Engineering"),
        ("CIVIL", "Civil Engineering"),
    ]
    branch_map = {}
    for code, name in branches_data:
        b = Branch.query.filter_by(code=code).first()
        if not b:
            b = Branch(code=code, name=name, is_active=True)
            db.session.add(b)
            db.session.flush()
        branch_map[code] = b

    # 2. Academic Years
    ay = AcademicYear.query.filter_by(year_label="2025-2026").first()
    if not ay:
        ay = AcademicYear(year_label="2025-2026", is_current=True)
        db.session.add(ay)
        db.session.flush()

    # 3. Semesters (1 to 8)
    sem_map = {}
    for num in range(1, 9):
        sem = Semester.query.filter_by(number=num).first()
        if not sem:
            sem = Semester(number=num, name=f"Semester {num}", is_active=True)
            db.session.add(sem)
            db.session.flush()
        sem_map[num] = sem

    # 4. Sections
    sections_data = [
        ("A", "CSE", 5),
        ("B", "CSE", 5),
        ("A", "CSM", 5),
        ("A", "ECE", 5),
        ("B", "ECE", 5),
    ]
    section_map = {}
    for sec_name, b_code, sem_num in sections_data:
        sec = Section.query.filter_by(
            name=sec_name,
            branch_id=branch_map[b_code].id,
            academic_year_id=ay.id,
            semester_id=sem_map[sem_num].id,
        ).first()
        if not sec:
            sec = Section(
                name=sec_name,
                branch_id=branch_map[b_code].id,
                academic_year_id=ay.id,
                semester_id=sem_map[sem_num].id,
                is_active=True,
            )
            db.session.add(sec)
            db.session.flush()
        section_map[f"{b_code}_{sem_num}_{sec_name}"] = sec

    # 5. Classrooms
    classrooms_data = [
        ("C-101", "Main Block", 60),
        ("C-102", "Main Block", 60),
        ("C-201", "CSE Block", 70),
        ("C-204", "CSE Block", 70),
        ("C-301", "R&D Block", 65),
        ("C-305", "R&D Block", 65),
        ("LH-1", "Lecture Hall Complex", 120),
        ("LH-2", "Lecture Hall Complex", 120),
        ("LAB-1", "Turing Computing Lab", 40),
        ("LAB-2", "Ada Lovelace AI Lab", 40),
    ]
    room_map = {}
    for r_num, block, cap in classrooms_data:
        rm = Classroom.query.filter_by(room_number=r_num).first()
        if not rm:
            rm = Classroom(room_number=r_num, building_block=block, capacity=cap, is_active=True)
            db.session.add(rm)
            db.session.flush()
        room_map[r_num] = rm

    # 6. Subjects for CSE Sem 5
    subjects_data = [
        ("CS501", "Database Management Systems", "CSE", 5),
        ("CS502", "Machine Learning & Applications", "CSE", 5),
        ("CS503", "Computer Networks & Protocols", "CSE", 5),
        ("CS504", "Web Application Development", "CSE", 5),
        ("CS505", "Software Engineering & DevOps", "CSE", 5),
        ("EC501", "Digital Signal Processing", "ECE", 5),
    ]
    subject_map = {}
    for code, name, b_code, sem_num in subjects_data:
        sub = Subject.query.filter_by(code=code, branch_id=branch_map[b_code].id).first()
        if not sub:
            sub = Subject(code=code, name=name, branch_id=branch_map[b_code].id, semester_id=sem_map[sem_num].id)
            db.session.add(sub)
            db.session.flush()
        subject_map[code] = sub

    # 7. Faculty Accounts & Profiles
    faculty_specs = [
        ("fac_sharma", "sharma@gvpcew.ac.in", "Dr. Ananya Sharma", "GVP-FAC-01", "CSE", "Associate Professor"),
        ("fac_rao", "rao@gvpcew.ac.in", "Prof. K. V. Rao", "GVP-FAC-02", "CSE", "Professor"),
        ("fac_lakshmi", "lakshmi@gvpcew.ac.in", "Dr. P. Lakshmi", "GVP-FAC-03", "ECE", "Assistant Professor"),
    ]
    faculty_map = {}
    for uname, email, fname, fid, bcode, desig in faculty_specs:
        u = User.query.filter_by(username=uname).first()
        if not u:
            u = User(username=uname, email=email, role="faculty", full_name=fname, is_active=True)
            u.set_password("Faculty@123")
            db.session.add(u)
            db.session.flush()

        fp = FacultyProfile.query.filter_by(faculty_id=fid).first()
        if not fp:
            fp = FacultyProfile(
                user_id=u.id,
                faculty_id=fid,
                department_branch_id=branch_map[bcode].id,
                phone="9876543210",
                designation=desig,
                is_active=True,
            )
            db.session.add(fp)
            db.session.flush()
        faculty_map[fid] = fp

    # 8. Student Accounts & Profiles
    student_specs = [
        ("student_sneha", "sneha@gvpcew.ac.in", "Sneha Reddy", "22L31A0501", "CSE_5_A", "CSE", 5),
        ("student_kavya", "kavya@gvpcew.ac.in", "Kavya Varma", "22L31A0502", "CSE_5_A", "CSE", 5),
        ("student_divya", "divya@gvpcew.ac.in", "Divya Teja", "22L31A0401", "ECE_5_A", "ECE", 5),
    ]
    for uname, email, sname, rnum, sec_key, bcode, sem_num in student_specs:
        u = User.query.filter_by(username=uname).first()
        if not u:
            u = User(username=uname, email=email, role="student", full_name=sname, is_active=True)
            u.set_password("Student@123")
            db.session.add(u)
            db.session.flush()

        sp = StudentProfile.query.filter_by(roll_number=rnum).first()
        if not sp:
            sec_obj = section_map[sec_key]
            sp = StudentProfile(
                user_id=u.id,
                roll_number=rnum,
                branch_id=branch_map[bcode].id,
                academic_year_id=ay.id,
                semester_id=sem_map[sem_num].id,
                section_id=sec_obj.id,
                is_active=True,
            )
            db.session.add(sp)

    # 9. Default Administrator Account (if none exists)
    admin_u = User.query.filter_by(role="admin").first()
    if not admin_u:
        admin_u = User(
            username="admin",
            email="admin@gvpcew.ac.in",
            role="admin",
            full_name="College Administrator",
            is_active=True,
        )
        admin_u.set_password("Admin@123")
        db.session.add(admin_u)
        db.session.flush()

    # 10. Sample Published Timetable for CSE-A
    csea_sec = section_map["CSE_5_A"]
    existing_tt = TimetableVersion.query.filter_by(section_id=csea_sec.id, status="published").first()
    if not existing_tt:
        tt_version = TimetableVersion(
            branch_id=branch_map["CSE"].id,
            academic_year_id=ay.id,
            semester_id=sem_map[5].id,
            section_id=csea_sec.id,
            version_number=1,
            status="published",
            timetable_type="regular",
            effective_date=date.today(),
            created_by_id=admin_u.id,
            approved_at=datetime.utcnow(),
            notes="Initial Semester 5 Timetable",
        )
        db.session.add(tt_version)
        db.session.flush()

        # Add entries for all 6 days, periods 1-7
        schedule_matrix = [
            ("Monday", 1, time(9, 0), time(9, 50), "CS501", "GVP-FAC-01", "C-204"),
            ("Monday", 2, time(9, 50), time(10, 40), "CS502", "GVP-FAC-02", "C-204"),
            ("Monday", 3, time(10, 50), time(11, 40), "CS503", "GVP-FAC-01", "C-204"),
            ("Monday", 4, time(11, 40), time(12, 30), "CS504", "GVP-FAC-02", "C-204"),
            ("Monday", 5, time(13, 20), time(14, 10), "CS505", "GVP-FAC-01", "C-204"),
            ("Monday", 6, time(14, 10), time(15, 0), "CS501", "GVP-FAC-01", "LAB-1"),
            ("Monday", 7, time(15, 0), time(15, 50), "CS501", "GVP-FAC-01", "LAB-1"),
            # Tuesday
            ("Tuesday", 1, time(9, 0), time(9, 50), "CS502", "GVP-FAC-02", "C-204"),
            ("Tuesday", 2, time(9, 50), time(10, 40), "CS503", "GVP-FAC-01", "C-204"),
            ("Tuesday", 3, time(10, 50), time(11, 40), "CS504", "GVP-FAC-02", "C-204"),
            ("Tuesday", 4, time(11, 40), time(12, 30), "CS505", "GVP-FAC-01", "C-204"),
            ("Tuesday", 5, time(13, 20), time(14, 10), "CS501", "GVP-FAC-01", "C-204"),
            ("Tuesday", 6, time(14, 10), time(15, 0), "CS502", "GVP-FAC-02", "LAB-2"),
            ("Tuesday", 7, time(15, 0), time(15, 50), "CS502", "GVP-FAC-02", "LAB-2"),
            # Wednesday
            ("Wednesday", 1, time(9, 0), time(9, 50), "CS503", "GVP-FAC-01", "C-204"),
            ("Wednesday", 2, time(9, 50), time(10, 40), "CS504", "GVP-FAC-02", "C-204"),
            ("Wednesday", 3, time(10, 50), time(11, 40), "CS505", "GVP-FAC-01", "C-204"),
            ("Wednesday", 4, time(11, 40), time(12, 30), "CS501", "GVP-FAC-01", "C-204"),
            ("Wednesday", 5, time(13, 20), time(14, 10), "CS502", "GVP-FAC-02", "C-204"),
            ("Wednesday", 6, time(14, 10), time(15, 0), "CS503", "GVP-FAC-01", "C-204"),
            ("Wednesday", 7, time(15, 0), time(15, 50), "CS504", "GVP-FAC-02", "C-204"),
            # Thursday
            ("Thursday", 1, time(9, 0), time(9, 50), "CS505", "GVP-FAC-01", "C-204"),
            ("Thursday", 2, time(9, 50), time(10, 40), "CS501", "GVP-FAC-01", "C-204"),
            ("Thursday", 3, time(10, 50), time(11, 40), "CS502", "GVP-FAC-02", "C-204"),
            ("Thursday", 4, time(11, 40), time(12, 30), "CS503", "GVP-FAC-01", "C-204"),
            ("Thursday", 5, time(13, 20), time(14, 10), "CS504", "GVP-FAC-02", "C-204"),
            ("Thursday", 6, time(14, 10), time(15, 0), "CS505", "GVP-FAC-01", "C-204"),
            ("Thursday", 7, time(15, 0), time(15, 50), "CS501", "GVP-FAC-01", "C-204"),
            # Friday
            ("Friday", 1, time(9, 0), time(9, 50), "CS504", "GVP-FAC-02", "C-204"),
            ("Friday", 2, time(9, 50), time(10, 40), "CS505", "GVP-FAC-01", "C-204"),
            ("Friday", 3, time(10, 50), time(11, 40), "CS501", "GVP-FAC-01", "C-204"),
            ("Friday", 4, time(11, 40), time(12, 30), "CS502", "GVP-FAC-02", "C-204"),
            ("Friday", 5, time(13, 20), time(14, 10), "CS503", "GVP-FAC-01", "C-204"),
            ("Friday", 6, time(14, 10), time(15, 0), "CS504", "GVP-FAC-02", "C-204"),
            ("Friday", 7, time(15, 0), time(15, 50), "CS505", "GVP-FAC-01", "C-204"),
            # Saturday
            ("Saturday", 1, time(9, 0), time(9, 50), "CS501", "GVP-FAC-01", "C-204"),
            ("Saturday", 2, time(9, 50), time(10, 40), "CS502", "GVP-FAC-02", "C-204"),
            ("Saturday", 3, time(10, 50), time(11, 40), "CS503", "GVP-FAC-01", "C-204"),
            ("Saturday", 4, time(11, 40), time(12, 30), "CS504", "GVP-FAC-02", "C-204"),
            ("Saturday", 5, time(13, 20), time(14, 10), "CS505", "GVP-FAC-01", "C-204"),
            ("Saturday", 6, time(14, 10), time(15, 0), "CS501", "GVP-FAC-01", "C-204"),
            ("Saturday", 7, time(15, 0), time(15, 50), "CS502", "GVP-FAC-02", "C-204"),
        ]

        first_entry = None
        for day, p_num, st, et, s_code, f_id, r_num in schedule_matrix:
            entry = TimetableEntry(
                timetable_version_id=tt_version.id,
                day_of_week=day,
                period_number=p_num,
                start_time=st,
                end_time=et,
                subject_id=subject_map[s_code].id,
                faculty_id=faculty_map[f_id].id,
                classroom_id=room_map[r_num].id,
                status="Upcoming",
                is_uncertain=False,
            )
            db.session.add(entry)
            if not first_entry:
                first_entry = entry

        db.session.flush()

        # Seed sample room change history and initial welcome notifications
        if first_entry:
            hist = RoomChangeHistory(
                timetable_entry_id=first_entry.id,
                old_classroom_id=room_map["C-101"].id,
                new_classroom_id=room_map["C-204"].id,
                changed_by_id=admin_u.id,
                reason="Relocated to higher capacity lab",
                effective_date=date.today(),
            )
            db.session.add(hist)

            # Notifications for faculty and students
            notif_fac = Notification(
                user_id=faculty_map["GVP-FAC-01"].user_id,
                title="Classroom Change: Database Management Systems (CSE-A)",
                message="Classroom Change: Database Management Systems, CSE-A, Period 1, 09:00 AM - 09:50 AM. Previous room: C-101. New room: C-204.",
                notification_type="room_change",
                related_entry_id=first_entry.id,
                delivery_status="delivered",
            )
            db.session.add(notif_fac)

            # Notify students
            st_sneha = User.query.filter_by(username="student_sneha").first()
            if st_sneha:
                notif_sneha = Notification(
                    user_id=st_sneha.id,
                    title="Classroom Change: Database Management Systems (CSE-A)",
                    message="Classroom Change: Database Management Systems, CSE-A, Period 1, 09:00 AM - 09:50 AM. Previous room: C-101. New room: C-204.",
                    notification_type="room_change",
                    related_entry_id=first_entry.id,
                    delivery_status="delivered",
                )
                db.session.add(notif_sneha)

    db.session.commit()
    click.echo("[SUCCESS] GVPCEW starter data successfully populated!")
    click.echo("\n--- Ready to Test Credentials ---")
    click.echo("Admin Portal:   admin / Admin@123")
    click.echo("Faculty Portal: fac_sharma / Faculty@123  (or fac_rao / Faculty@123)")
    click.echo("Student Portal: student_sneha / Student@123  (CSE-A)")
