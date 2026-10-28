"""Notification and Web Push Subscription models."""

from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(30), default="general", nullable=False, index=True)
    # types: room_change, timetable_update, class_reminder, substitution, cancellation, general
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    related_entry_id = db.Column(db.Integer, db.ForeignKey("timetable_entries.id"), nullable=True)
    delivery_status = db.Column(db.String(20), default="delivered", nullable=False)  # pending, delivered, failed

    # Relationships
    user = db.relationship("User", back_populates="notifications")
    related_entry = db.relationship("TimetableEntry")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime("%b %d, %Y %I:%M %p"),
            "timestamp": self.created_at.isoformat(),
            "related_entry_id": self.related_entry_id,
        }

    def __repr__(self):
        return f"<Notification {self.id}: {self.title} (User={self.user_id})>"


class PushSubscription(db.Model):
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh_key = db.Column(db.String(255), nullable=False)
    auth_key = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="push_subscriptions")

    def __repr__(self):
        return f"<PushSubscription User={self.user_id}>"
