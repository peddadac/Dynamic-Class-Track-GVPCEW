"""Tests for Application startup, Landing page portal cards, Authentication, and Role Protection."""

import pytest
from flask import url_for
from app.models.user import User


def test_1_application_starts_successfully(client):
    """Req 1: Verify the application initializes and responds to root request."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dynamic Class Track" in response.data


def test_2_landing_page_displays_all_three_portals(client):
    """Req 2: Verify the landing page prominently displays Admin, Faculty, and Student portals."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Admin Portal" in response.data
    assert b"Faculty Portal" in response.data
    assert b"Student Portal" in response.data
    assert b"Admin Login" in response.data
    assert b"Faculty Login" in response.data
    assert b"Student Login" in response.data


def test_3_login_works_for_each_role(client):
    """Req 3: Verify login functions correctly for admin, faculty, and student roles."""
    # 1. Admin login
    res_admin = client.post(
        "/login",
        data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"},
        follow_redirects=True,
    )
    assert res_admin.status_code == 200
    assert b"Administrative Overview" in res_admin.data or b"Admin Console" in res_admin.data

    # Logout
    client.get("/logout", follow_redirects=True)

    # 2. Faculty login
    res_fac = client.post(
        "/login",
        data={"username_or_email": "fac_sharma", "password": "Faculty@123", "role": "faculty"},
        follow_redirects=True,
    )
    assert res_fac.status_code == 200
    assert b"Teaching Schedule" in res_fac.data or b"Dr. Ananya Sharma" in res_fac.data

    # Logout
    client.get("/logout", follow_redirects=True)

    # 3. Student login
    res_st = client.post(
        "/login",
        data={"username_or_email": "student_sneha", "password": "Student@123", "role": "student"},
        follow_redirects=True,
    )
    assert res_st.status_code == 200
    assert b"Your Classes Today" in res_st.data or b"Sneha Reddy" in res_st.data


def test_4_unauthorized_users_cannot_access_protected_dashboards(client):
    """Req 4: Verify unauthenticated users are redirected from protected endpoints."""
    # Unauthenticated attempts
    res_admin = client.get("/admin/dashboard", follow_redirects=False)
    assert res_admin.status_code in [302, 401, 403]
    assert "/login" in res_admin.headers.get("Location", "")

    res_fac = client.get("/faculty/dashboard", follow_redirects=False)
    assert res_fac.status_code in [302, 401, 403]

    res_st = client.get("/student/dashboard", follow_redirects=False)
    assert res_st.status_code in [302, 401, 403]

    # Student trying to access admin dashboard
    client.post(
        "/login",
        data={"username_or_email": "student_sneha", "password": "Student@123", "role": "student"},
    )
    res_cross = client.get("/admin/dashboard", follow_redirects=True)
    # Should redirect away with permission warning
    assert b"permission" in res_cross.data.lower() or b"student" in res_cross.data.lower()
