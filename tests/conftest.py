"""Shared pytest fixtures for E2E API tests."""

import os
import random
import string

import psycopg2
import psycopg2.extras
import pytest

# Point to a test database before importing the app
os.environ.setdefault("DB_NAME", "terminal_accounting_test")

from app import create_app
from app.config import TestingConfig


@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask test application."""
    application = create_app(config_class=TestingConfig)
    yield application


@pytest.fixture(scope="session")
def client(app):
    """A Flask test client shared across the session."""
    return app.test_client()


@pytest.fixture(scope="session")
def db_conn():
    """A raw psycopg2 connection to the test database for cleanup."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    database = os.environ.get("DB_NAME", "terminal_accounting_test")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    if password:
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        url = f"postgresql://{user}@{host}:{port}/{database}"

    conn = psycopg2.connect(url)
    conn.autocommit = True
    yield conn
    conn.close()


def _rand_suffix(length=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


@pytest.fixture()
def username():
    """Generate a unique username per test."""
    return f"testuser_{_rand_suffix()}"


@pytest.fixture()
def register_user(client, username):
    """Register a user and return the response JSON."""
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
    })
    return resp.get_json()


@pytest.fixture()
def admin_user(client):
    """Create an admin user (first user is auto-admin)."""
    uname = f"admin_{_rand_suffix()}"
    resp = client.post("/api/auth/register", json={
        "username": uname,
        "password": "admin123456",
    })
    data = resp.get_json()
    return {"username": uname, **data}


@pytest.fixture()
def approved_user(client, admin_user, username):
    """Register a user and approve them via admin."""
    reg = client.post("/api/auth/register", json={
        "username": username,
        "password": "password123",
    })
    reg_data = reg.get_json()
    user_id = reg_data.get("id")

    # Approve via admin
    client.post(
        f"/api/auth/approve-user/{user_id}",
        headers={"X-Username": admin_user["username"]},
    )
    return {"username": username, "id": user_id}


@pytest.fixture()
def auth_headers(approved_user):
    """Return headers dict with X-Username for an approved user."""
    return {"X-Username": approved_user["username"]}


@pytest.fixture()
def admin_headers(admin_user):
    """Return headers dict with X-Username for the admin."""
    return {"X-Username": admin_user["username"]}


@pytest.fixture()
def category_id(client, auth_headers):
    """Create a cost category and return its id."""
    resp = client.post("/api/categories", json={
        "name": f"TestCategory_{_rand_suffix()}",
        "type": "cost",
    }, headers=auth_headers)
    return resp.get_json()["id"]


@pytest.fixture()
def income_category_id(client, auth_headers):
    """Create an income category and return its id."""
    resp = client.post("/api/categories", json={
        "name": f"TestIncome_{_rand_suffix()}",
        "type": "income",
    }, headers=auth_headers)
    return resp.get_json()["id"]


@pytest.fixture()
def wallet_id(client, auth_headers):
    """Create a wallet and return its id."""
    resp = client.post("/api/wallets", json={
        "name": f"TestWallet_{_rand_suffix()}",
        "currency": "IRR",
        "wallet_type": "personal",
        "amount": 10000000,
    }, headers=auth_headers)
    return resp.get_json()["id"]
