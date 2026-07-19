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


def test_infra_domain_never_counts_toward_two_key_bar(conn):
    # Two unrelated HN authors both posting github.com links must NOT merge —
    # the founder-armanified regression.
    a = _ingest(conn, "hn", "https://news.ycombinator.com/item?id=10", "post a")
    b = _ingest(conn, "hn", "https://news.ycombinator.com/item?id=11", "post b")
    summary = resolve.resolve(conn, [
        {"signal_id": a, "keys": {"hn": "armanified", "domain": "github.com"}},
        {"signal_id": b, "keys": {"hn": "kamranahmed_se", "domain": "github.com"}},
    ])
    assert summary["resolved"] == 0
    assert summary["founders"] == 0
    reasons = {r["reason"] for r in conn.execute("SELECT reason FROM droplog")}
    assert reasons == {"infra_domain_not_linking"}
    # the drop-log row preserves the original keys, infra domain included
    row = conn.execute("SELECT entity_keys FROM droplog WHERE signal_id=?", (a,)).fetchone()
    assert "github.com" in row["entity_keys"]


def test_stored_infra_domain_never_matches_new_signals(conn):
    # Legacy-polluted founder: infra domain already stored in entity_keys.
    import json
    from app.memory.ingest import upsert_founder
    from app.memory.models import Founder
    upsert_founder(conn, Founder(id="founder-legacy", name="legacy",
                                 entity_keys={"hn": "alice", "domain": "github.com"}))
    sig = _ingest(conn, "hn", "https://news.ycombinator.com/item?id=12", "post c")
    summary = resolve.resolve(conn, [
        {"signal_id": sig, "keys": {"hn": "bob", "domain": "github.com"}},
    ])
    assert summary["resolved"] == 0  # github.com must not link bob to alice
    keys = json.loads(conn.execute("SELECT entity_keys FROM founders WHERE "
                                   "id='founder-legacy'").fetchone()["entity_keys"])
    assert keys["hn"] == "alice"  # untouched


def test_audit_fix_unlinks_infra_merge_and_renames(conn):
    # Reproduce the pre-fix false-merge state directly, then run the audit fix.
    import importlib.util
    import json
    from pathlib import Path
    from app.memory.ingest import upsert_founder
    from app.memory.models import Founder

    spec = importlib.util.spec_from_file_location(
        "audit_merges",
        Path(__file__).resolve().parent.parent / "scripts" / "audit_merges.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

    a = _ingest(conn, "hn", "https://news.ycombinator.com/item?id=20",
                "Show HN: tiny LLM | author=armanified points=915")
    b = _ingest(conn, "hn", "https://news.ycombinator.com/item?id=21",
                "Show HN: dev tools | author=kamranahmed_se points=130")
    upsert_founder(conn, Founder(id="founder-armanified", name="armanified",
                                 entity_keys={"hn": "kamranahmed_se",
                                              "domain": "github.com"}))
    for sid in (a, b):
        conn.execute("INSERT INTO resolutions (signal_id, founder_id, method, "
                     "resolved_at) VALUES (?,?,?,?)",
                     (sid, "founder-armanified", "entity_key_cooccurrence", "t"))
    conn.commit()

    out = audit.fix(conn)
    assert "founder-armanified" in out["fixed"]
    # no signals remain attached; both landed in droplog with the unlink reason
    left = conn.execute("SELECT COUNT(*) c FROM resolutions WHERE "
                        "founder_id='founder-armanified'").fetchone()["c"]
    assert left == 0
    rows = conn.execute("SELECT signal_id FROM droplog WHERE reason=?",
                        (audit.UNLINK_REASON,)).fetchall()
    assert {r["signal_id"] for r in rows} == {a, b}
    # signals and the founder row still exist (append-only guardrail)
    assert conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"] == 2
    f = conn.execute("SELECT name, entity_keys FROM founders WHERE "
                     "id='founder-armanified'").fetchone()
    assert json.loads(f["entity_keys"]) == {}  # no key backed by resolved evidence
    assert f["name"] == "@armanified"  # bare-handle name made honest


def test_no_linkedin_source_exists():
    # Guardrail: no LinkedIn adapter anywhere in the sources package.
    import pkgutil

    import app.sources as sources
    names = {m.name for m in pkgutil.iter_modules(sources.__path__)}
    assert "linkedin" not in names
    assert "github" in names and "hn" in names
