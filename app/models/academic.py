"""Academic models: Branch, AcademicYear, Semester, Section, Subject, and Profiles."""

from datetime import datetime
from app.extensions import db


class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g., CSE, CSM, ECE
    name = db.Column(db.String(120), nullable=False)                         # e.g., Computer Science and Engineering
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sections = db.relationship("Section", back_populates="branch", cascade="all, delete-orphan")
    subjects = db.relationship("Subject", back_populates="branch", cascade="all, delete-orphan")
    faculty_members = db.relationship("FacultyProfile", back_populates="department_branch")
    students = db.relationship("StudentProfile", back_populates="branch")
    timetable_versions = db.relationship("TimetableVersion", back_populates="branch")

    def __repr__(self):
        return f"<Branch {self.code}>"


class AcademicYear(db.Model):
    __tablename__ = "academic_years"

    id = db.Column(db.Integer, primary_key=True)
    year_label = db.Column(db.String(30), unique=True, nullable=False)  # e.g., 2025-2026
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sections = db.relationship("Section", back_populates="academic_year", cascade="all, delete-orphan")
    students = db.relationship("StudentProfile", back_populates="academic_year")
    timetable_versions = db.relationship("TimetableVersion", back_populates="academic_year")

    def __repr__(self):
        return f"<AcademicYear {self.year_label}>"


class Semester(db.Model):
    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)         # 1 to 8
    name = db.Column(db.String(50), nullable=False)                     # Semester 1, etc.
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    sections = db.relationship("Section", back_populates="semester", cascade="all, delete-orphan")
    subjects = db.relationship("Subject", back_populates="semester", cascade="all, delete-orphan")
    students = db.relationship("StudentProfile", back_populates="semester")
    timetable_versions = db.relationship("TimetableVersion", back_populates="semester")

    def __repr__(self):
        return f"<Semester {self.number}>"


class Section(db.Model):
    __tablename__ = "sections"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)  # e.g., A, B, C
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Composite uniqueness constraint: A branch + academic year + semester + section name must be unique
    __table_args__ = (
        db.UniqueConstraint("name", "branch_id", "academic_year_id", "semester_id", name="uq_section_identity"),
    )

    # Relationships
    branch = db.relationship("Branch", back_populates="sections")
    academic_year = db.relationship("AcademicYear", back_populates="sections")
    semester = db.relationship("Semester", back_populates="sections")
    students = db.relationship("StudentProfile", back_populates="section")
    timetable_versions = db.relationship("TimetableVersion", back_populates="section")

    @property
    def display_name(self):
        return f"{self.branch.code} Sem {self.semester.number} - Sec {self.name} ({self.academic_year.year_label})"

    def __repr__(self):
        return f"<Section {self.display_name}>"


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, index=True)         # e.g., CS501
    name = db.Column(db.String(150), nullable=False)                    # e.g., Data Structures & Algorithms
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    branch = db.relationship("Branch", back_populates="subjects")
    semester = db.relationship("Semester", back_populates="subjects")
    timetable_entries = db.relationship("TimetableEntry", back_populates="subject")

    __table_args__ = (
        db.UniqueConstraint("code", "branch_id", "semester_id", name="uq_subject_code_branch_sem"),
    )

    def __repr__(self):
        return f"<Subject {self.code} - {self.name}>"


class FacultyProfile(db.Model):
    __tablename__ = "faculty_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    faculty_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., GVP-FAC-01
    department_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    phone = db.Column(db.String(25), nullable=True)
    designation = db.Column(db.String(80), default="Assistant Professor")
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="faculty_profile")
    department_branch = db.relationship("Branch", back_populates="faculty_members")
    timetable_entries = db.relationship("TimetableEntry", back_populates="faculty")

    @property
    def full_name(self):
        return self.user.full_name if self.user else ""

    def __repr__(self):
        return f"<FacultyProfile {self.faculty_id} - {self.full_name}>"


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., 22L31A0501
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="student_profile")
    branch = db.relationship("Branch", back_populates="students")
    academic_year = db.relationship("AcademicYear", back_populates="students")
    semester = db.relationship("Semester", back_populates="students")
    section = db.relationship("Section", back_populates="students")

    @property
    def full_name(self):
        return self.user.full_name if self.user else ""

    def __repr__(self):
        return f"<StudentProfile {self.roll_number} - {self.full_name}>"
