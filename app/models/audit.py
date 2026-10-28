"""Audit logging model for administrative operations and security events."""

from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=True)
    entity_id = db.Column(db.String(80), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="audit_logs")

    @classmethod
    def log(cls, user_id, action, entity_type=None, entity_id=None, details=None, ip_address=None):
        """Helper to create and commit an audit log entry."""
        entry = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
        db.session.add(entry)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return entry

    def __repr__(self):
        return f"<AuditLog {self.action} by User={self.user_id} at {self.timestamp}>"
