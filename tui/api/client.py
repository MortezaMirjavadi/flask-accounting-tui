"""API client functions for making HTTP requests."""

import requests
from tui.config import BASE_URL


def api_get(path, params=None, username=None):
    """Make GET request to API."""
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.get(
            f"{BASE_URL}{path}",
            params=params,
            headers=headers,
            timeout=10
        )
    except requests.RequestException:
        return None


def api_post(path, payload, username=None):
    """Make POST request to API."""
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.post(
            f"{BASE_URL}{path}",
            json=payload,
            headers=headers,
            timeout=10
        )
    except requests.RequestException:
        return None


def api_put(path, payload, username=None):
    """Make PUT request to API."""
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.put(
            f"{BASE_URL}{path}",
            json=payload,
            headers=headers,
            timeout=10
        )
    except requests.RequestException:
        return None


def api_delete(path, username=None):
    """Make DELETE request to API."""
    headers = {}
    if username:
        headers["X-Username"] = username
    try:
        return requests.delete(
            f"{BASE_URL}{path}",
            headers=headers,
            timeout=10
        )
    except requests.RequestException:
        return None
