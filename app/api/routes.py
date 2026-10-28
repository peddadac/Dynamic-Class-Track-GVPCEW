"""API endpoints for asynchronous dropdowns, notification polling, and WebPush subscriptions."""

from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.academic import Section, Subject
from app.models.notification import Notification, PushSubscription

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/sections-by-branch/<int:branch_id>")
def get_sections_by_branch(branch_id):
    """Dynamic section dropdown filtered by selected branch."""
    sem_id = request.args.get("semester_id", type=int)
    query = Section.query.filter_by(branch_id=branch_id, is_active=True)
    if sem_id:
        query = query.filter_by(semester_id=sem_id)
    sections = query.all()
    return jsonify([{"id": s.id, "name": s.name, "display": s.display_name} for s in sections])


@api_bp.route("/subjects-by-branch-sem/<int:branch_id>/<int:semester_id>")
def get_subjects_by_branch_sem(branch_id, semester_id):
    """Dynamic subject dropdown filtered by branch and semester."""
    subjects = Subject.query.filter_by(branch_id=branch_id, semester_id=semester_id, is_active=True).all()
    return jsonify([{"id": s.id, "code": s.code, "name": s.name} for s in subjects])


@api_bp.route("/notifications/unread")
@login_required
def get_unread_notifications():
    """Live polling endpoint for bell icon count and unread notification items."""
    notifs = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )
    return jsonify({
        "count": len(notifs),
        "notifications": [n.to_dict() for n in notifs],
    })


@api_bp.route("/notifications/mark-read/<int:notif_id>", methods=["POST"])
@login_required
def mark_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if notif:
        notif.is_read = True
        notif.read_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404


@api_bp.route("/push/subscribe", methods=["POST"])
@login_required
def push_subscribe():
    """Saves browser WebPush subscription keys for push notifications."""
    data = request.get_json()
    if not data or not data.get("endpoint"):
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    endpoint = data.get("endpoint")
    keys = data.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not (endpoint and p256dh and auth):
        return jsonify({"success": False, "error": "Missing subscription keys"}), 400

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not existing:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh_key=p256dh,
            auth_key=auth,
        )
        db.session.add(sub)
        db.session.commit()

    return jsonify({"success": True})


@api_bp.route("/push/vapid-public-key")
def get_vapid_public_key():
    key = current_app.config.get("VAPID_PUBLIC_KEY", "")
    return jsonify({"publicKey": key})
