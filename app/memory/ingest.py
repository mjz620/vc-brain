"""Ingest: dedup hash, append-only signal ingest, founder upsert, claim store.

Dedup key is (source, source_url, normalized content) — the brief's dedup requirement.
Signal ids are derived from that hash so identity is content-stable and deterministic
across replay runs.
"""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone

from .models import Claim, Founder, ScoreEntry, Signal


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dedup_hash(source: str, source_url: str, content: str) -> str:
    norm = re.sub(r"\s+", " ", content.strip().lower())
    key = f"{source}\x00{source_url}\x00{norm}"
    return hashlib.sha256(key.encode()).hexdigest()


def ingest_signal(conn: sqlite3.Connection, signal: Signal) -> tuple[str, bool]:
    """Insert a signal. Returns (signal_id, inserted).

    inserted=False means an identical signal already existed and the duplicate was
    rejected (append-only: the original row is untouched).
    """
    h = dedup_hash(signal.source, signal.source_url, signal.content)
    sig_id = "sig-" + h[:12]
    existing = conn.execute("SELECT id FROM signals WHERE dedup_hash = ?", (h,)).fetchone()
    if existing:
        return existing["id"], False
    conn.execute(
        "INSERT INTO signals (id, founder_id, source, source_url, content, "
        "observed_at, ingested_at, dedup_hash) VALUES (?,?,?,?,?,?,?,?)",
        (sig_id, signal.founder_id, signal.source, signal.source_url, signal.content,
         signal.observed_at, _now(), h),
    )
    conn.commit()
    return sig_id, True


def upsert_founder(conn: sqlite3.Connection, founder: Founder) -> None:
    now = _now()
    conn.execute(
        "INSERT INTO founders (id, name, aliases, entity_keys, founder_score, "
        "first_seen, last_updated) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, aliases=excluded.aliases, "
        "entity_keys=excluded.entity_keys, last_updated=excluded.last_updated",
        (founder.id, founder.name, json.dumps(founder.aliases),
         json.dumps(founder.entity_keys), founder.founder_score.model_dump_json(),
         founder.first_seen or now, now),
    )
    conn.commit()


def append_score(conn: sqlite3.Connection, founder_id: str, entry: ScoreEntry,
                 dimensions: dict[str, float] | None = None,
                 coverage: float | None = None) -> None:
    """Append a score point to a founder's history (never overwrite). Trend for free."""
    row = conn.execute("SELECT founder_score FROM founders WHERE id = ?",
                       (founder_id,)).fetchone()
    if row is None:
        raise KeyError(f"unknown founder {founder_id}")
    score = json.loads(row["founder_score"] or "{}")
    score.setdefault("history", []).append(entry.model_dump())
    if dimensions is not None:
        score["dimensions"] = dimensions
    if coverage is not None:
        score["coverage"] = coverage
    conn.execute(
        "UPDATE founders SET founder_score = ?, last_updated = ? WHERE id = ?",
        (json.dumps(score), _now(), founder_id),
    )
    conn.commit()


def store_claim(conn: sqlite3.Connection, founder_id: str, claim: Claim,
                signal_ids: list[str] | None = None) -> None:
    """Store a ledger claim (incl. negative results). >=1 signal per claim expected.

    If the caller doesn't pass signal_ids, they are resolved mechanically by matching
    the claim's evidence_url against the signals table — the claim→signal chain the
    trace endpoint walks must never depend on string matching at read time.
    """
    if signal_ids is None:
        rows = conn.execute("SELECT id, content, ingested_at FROM signals "
                            "WHERE source_url = ?", (claim.evidence_url,)).fetchall()
        signal_ids = [r["id"] for r in rows]
        if rows and claim.retrieved_at is None:
            claim.retrieved_at = rows[0]["ingested_at"]
        if rows and claim.evidence_title is None:
            claim.evidence_title = rows[0]["content"].split("|")[0].strip()[:120]
    conn.execute(
        "INSERT OR REPLACE INTO claims (claim_id, founder_id, subject, axis, text, stance, "
        "evidence, evidence_url, evidence_title, evidence_excerpt, retrieved_at, "
        "source_type, corroboration, trust, observed_at, signal_ids) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (claim.id, founder_id, claim.subject, claim.axis, claim.text, claim.stance,
         claim.evidence,
         claim.evidence_url, claim.evidence_title, claim.evidence_excerpt,
         claim.retrieved_at, claim.source_type, claim.corroboration, claim.trust,
         claim.observed_at, json.dumps(signal_ids)),
    )
    conn.commit()


def get_claims(conn: sqlite3.Connection, founder_id: str) -> list[Claim]:
    rows = conn.execute("SELECT * FROM claims WHERE founder_id = ?", (founder_id,)).fetchall()
    # claims.claim_id maps to Claim.id; other fields share their column name.
    return [Claim(id=r["claim_id"],
                  **{k: r[k] for k in Claim.model_fields if k != "id"})
            for r in rows]
