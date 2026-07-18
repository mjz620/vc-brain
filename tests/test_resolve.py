"""Entity resolution + drop-log (Block 2 gate: drop-log is populated, >=2-key rule)."""
import pytest

from app.memory import db, ingest, resolve
from app.memory.models import Signal


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    return c


def _ingest(conn, source, url, content):
    sid, _ = ingest.ingest_signal(conn, Signal(source=source, source_url=url,
                                               content=content))
    return sid


def test_two_keys_resolve_one_key_drops(conn):
    # GitHub repo: handle + linked domain (2 keys) -> resolves.
    gh = _ingest(conn, "github", "https://github.com/nferris/tracewell", "repo")
    # HN Show HN sharing the same domain -> links into the same founder.
    hn = _ingest(conn, "hn", "https://news.ycombinator.com/item?id=1", "show hn")
    # A repo with only a handle (no domain) -> insufficient keys -> drop-logged.
    solo = _ingest(conn, "github", "https://github.com/someacct/x", "repo")

    summary = resolve.resolve(conn, [
        {"signal_id": gh, "keys": {"github": "nferris", "domain": "tracewell.dev"}},
        {"signal_id": hn, "keys": {"hn": "nferris", "domain": "tracewell.dev"}},
        {"signal_id": solo, "keys": {"github": "someacct", "domain": ""}},
    ])

    assert summary["resolved"] == 2  # gh + hn
    assert summary["founders"] == 1  # merged via shared domain
    dropped_ids = {sid for sid, _ in summary["dropped"]}
    assert solo in dropped_ids
    # drop-log row persisted with its reason
    row = conn.execute("SELECT reason FROM droplog WHERE signal_id=?", (solo,)).fetchone()
    assert row["reason"] == "insufficient_entity_keys"
    # both resolved signals point at the same founder
    fids = {r["founder_id"] for r in conn.execute("SELECT founder_id FROM resolutions")}
    assert len(fids) == 1


def test_ambiguous_same_name_collision_is_drop_logged(conn):
    a = _ingest(conn, "github", "https://github.com/a/1", "repo a")
    b = _ingest(conn, "github", "https://github.com/b/2", "repo b")
    collide = _ingest(conn, "web", "https://example.com/c", "bio")
    # a and b establish two distinct founders on disjoint key pairs...
    resolve.resolve(conn, [
        {"signal_id": a, "keys": {"github": "alice", "domain": "alice.dev"}},
        {"signal_id": b, "keys": {"github": "bob", "domain": "bob.dev"}},
    ])
    # ...then a signal whose keys match BOTH founders is ambiguous -> drop-logged.
    summary = resolve.resolve(conn, [
        {"signal_id": collide, "keys": {"domain": "alice.dev", "github": "bob"}},
    ])
    assert summary["resolved"] == 0
    row = conn.execute("SELECT reason FROM droplog WHERE signal_id=?",
                       (collide,)).fetchone()
    assert row["reason"] == "ambiguous_multi_founder_match"


def test_no_linkedin_source_exists():
    # Guardrail: no LinkedIn adapter anywhere in the sources package.
    import pkgutil

    import app.sources as sources
    names = {m.name for m in pkgutil.iter_modules(sources.__path__)}
    assert "linkedin" not in names
    assert "github" in names and "hn" in names
