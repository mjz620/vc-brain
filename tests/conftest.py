"""Tests always run on local SQLite — never on a deployed DATABASE_URL.

Set to empty (not popped): app.config's load_dotenv(override=False) would
re-import the value from .env, but it never replaces an existing variable.
"""
import os

os.environ["DATABASE_URL"] = ""

import pytest


@pytest.fixture(autouse=True)
def _reset_ratelimit():
    """The limiter's hit counters are process-global and keyed by client IP, which
    is the same 'testclient' for every test. Without this reset, one test's applies
    spend the next test's budget and it 429s for reasons unrelated to itself."""
    from app import ratelimit
    ratelimit._hits.clear()
    yield
