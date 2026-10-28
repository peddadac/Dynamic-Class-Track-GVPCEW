"""Classroom model with capacity, block, and assignment relationships."""

from datetime import datetime
from app.extensions import db


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., C-204, LH-101
    building_block = db.Column(db.String(100), nullable=True)                        # e.g., Main Block, CSE Block
    capacity = db.Column(db.Integer, default=60, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    timetable_entries = db.relationship("TimetableEntry", back_populates="classroom")

    def __repr__(self):
        return f"<Classroom {self.room_number}>"
