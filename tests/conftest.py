"""Tests always run on local SQLite — never on a deployed DATABASE_URL.

Set to empty (not popped): app.config's load_dotenv(override=False) would
re-import the value from .env, but it never replaces an existing variable.
"""
import os

os.environ["DATABASE_URL"] = ""
