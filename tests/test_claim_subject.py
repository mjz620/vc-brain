"""A company has one founder_id but may have several founders. Without a per-claim
subject, extraction collapses them into one person and hangs one co-founder's
evidence (GitHub, education, employment) on another — after which the adjudicator
correctly reports a contradiction the pipeline itself manufactured.
"""
import pytest

from app import config
from app.diligence.ledger import to_claim
from app.diligence.schemas import ClaimDraft
from app.memory import db, ingest
from app.memory.models import Claim, Founder


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    c = db.connect()
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Skillset"))
    c.commit()
    return c


def _claim(cid, subject, text):
    return Claim(id=cid, subject=subject, axis="founder", text=text,
                 stance="supports", evidence="snippet",
                 evidence_url="https://github.com/arapat",
                 source_type="github", corroboration="single_source", trust=0.6)


def test_subject_round_trips_per_co_founder(conn):
    ingest.store_claim(conn, "f1", _claim(
        "team-01", "Julaiti Alafate", "Julaiti Alafate's 'sparrow' repo has 21 stars."), [])
    ingest.store_claim(conn, "f1", _claim(
        "team-02", "Sebastian Bosma", "Sebastian Bosma is Co-Founder & CEO."), [])

    by_id = {c.id: c for c in ingest.get_claims(conn, "f1")}
    # The GitHub evidence stays on the technical co-founder it actually belongs to.
    assert by_id["team-01"].subject == "Julaiti Alafate"
    assert by_id["team-02"].subject == "Sebastian Bosma"
    assert by_id["team-01"].subject != by_id["team-02"].subject


def test_company_level_claim_has_no_subject(conn):
    c = _claim("mkt-01", None, "The ITSM market is USD 4.5B.")
    ingest.store_claim(conn, "f1", c, [])
    assert ingest.get_claims(conn, "f1")[0].subject is None


def test_draft_subject_survives_the_ledger():
    draft = ClaimDraft(
        id="team-01", subject="Julaiti Alafate", axis="founder",
        text="PhD, UC San Diego.", stance="supports", evidence="snippet",
        source_url="https://scholar.google.com/citations?user=TuA50FUAAAAJ",
        source_type="web", corroboration="single_source", observed_at=None)
    assert to_claim(draft).subject == "Julaiti Alafate"


def test_migration_is_idempotent(conn):
    """init_db runs on every connect; a second pass must not fail or drop data."""
    ingest.store_claim(conn, "f1", _claim("team-01", "Julaiti Alafate", "x"), [])
    db.init_db(conn)
    db.init_db(conn)
    assert ingest.get_claims(conn, "f1")[0].subject == "Julaiti Alafate"
