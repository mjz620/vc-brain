"""Inbound PDF intake: a deck PDF parses to plain text and enters the SAME funnel
as a pasted summary. Extraction is verbatim — page furniture is dropped, nothing is
summarized, and a deck with no text layer is rejected rather than ingested empty."""
import io

import pytest

from app import config, deck_pdf
from app.memory import db, ingest
from app.memory.models import Founder


def _pdf(*paragraphs: str) -> bytes:
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate
    buf = io.BytesIO()
    style = getSampleStyleSheet()["Normal"]
    SimpleDocTemplate(buf).build([Paragraph(p, style) for p in paragraphs])
    return buf.getvalue()


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    c = db.connect()
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Seed"))
    c.commit()
    return c


def test_extract_drops_page_furniture_and_keeps_descriptor_first():
    text = deck_pdf.extract(_pdf(
        "Northwind Robotics - autonomous warehouse picking",
        "12",
        "CONFIDENTIAL",
        "14 paying enterprise customers and 2.1M ARR growing 22 percent month over "
        "month. Two ex-Boston Dynamics engineers founded the company in 2024 and "
        "have raised no institutional capital to date. Deployed in nine warehouses "
        "across three logistics operators."))
    # First non-blank line is what pipeline.py uses as the news-search descriptor.
    assert text.splitlines()[0] == "Northwind Robotics - autonomous warehouse picking"
    assert "12" not in text.splitlines()
    assert "CONFIDENTIAL" not in text.splitlines()
    assert "2.1M ARR" in text  # deck copy survives verbatim


def test_extract_rejects_non_pdf_and_textless_deck():
    with pytest.raises(deck_pdf.DeckPdfError, match="not a PDF"):
        deck_pdf.extract(b"just some bytes" * 20, "x.pdf")
    # An image-only deck extracts to ~nothing: fail loudly, never ingest empty.
    with pytest.raises(deck_pdf.DeckPdfError, match="no extractable text layer"):
        deck_pdf.extract(_pdf("hi"), "scan.pdf")
    with pytest.raises(deck_pdf.DeckPdfError, match="10MB"):
        deck_pdf.extract(b"%PDF-" + b"x" * (11 * 1024 * 1024), "big.pdf")


def test_apply_pdf_enters_same_funnel_and_dedups(conn, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    from fastapi.testclient import TestClient

    from app.server import app
    client = TestClient(app)
    pdf = _pdf("Northwind Robotics - warehouse picking",
               "14 paying enterprise customers and 2.1M ARR growing 22 percent month "
               "over month. Two ex-Boston Dynamics engineers, no institutional capital "
               "to date, deployed across nine warehouses and three logistics operators.")

    def post(name="deck.pdf", company="Northwind Robotics"):
        return client.post("/api/apply/pdf", data={"company": company},
                           files={"file": (name, pdf, "application/pdf")})

    r = post().json()
    assert r["founder_id"] == "founder-northwind-robotics"
    assert r["duplicate"] is False
    assert post().json()["duplicate"] is True  # same file re-uploaded dedups

    # The deck landed as a self-reported signal with the filename as provenance.
    row = conn.execute(
        "SELECT source, source_url, content FROM signals WHERE founder_id=?",
        ("founder-northwind-robotics",)).fetchone()
    assert row["source"] == "deck"
    assert row["source_url"].endswith("/deck.pdf")
    assert "2.1M ARR" in row["content"]

    # Rejections are cheap and must NOT burn the apply budget — the limiter guards
    # LLM spend, and neither of these reaches a model.
    assert client.post("/api/apply/pdf", data={"company": " "},
                       files={"file": ("d.pdf", pdf, "application/pdf")}).status_code == 422
    assert client.post("/api/apply/pdf", data={"company": "Bad"},
                       files={"file": ("d.pdf", b"nope" * 40, "application/pdf")}
                       ).status_code == 422
    assert post(name="again.pdf").status_code == 200  # budget survived both rejections
