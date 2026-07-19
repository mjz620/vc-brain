"""The outcome loop: this fund's own realised decisions joined back to the channel
that sourced each founder.

The honesty property under test is the null-vs-zero distinction. A channel with no
decisions must report decision_yield=None and an unlit node, NOT 0.0 — "we have not
decided anything from this channel yet" and "this channel produces bad companies"
must never render the same way.
"""
import pytest

from app import config
from app.api import network
from app.memory import db, ingest
from app.memory.models import Founder


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    c = db.connect()
    db.init_db(c)
    for fid in ("f-gh1", "f-gh2", "f-hn1"):
        ingest.upsert_founder(c, Founder(id=fid, name=fid))
    c.execute("INSERT INTO memos VALUES (?,?,?,?,?,?,?,?)",
              ("f-gh1", "t", "invest", "{}", "md", "b", "b", "now"))
    c.execute("INSERT INTO memos VALUES (?,?,?,?,?,?,?,?)",
              ("f-gh2", "t", "pass", "{}", "md", "b", "b", "now"))
    c.execute("INSERT INTO kill_log (founder_id, reason, thesis, logged_at) "
              "VALUES (?,?,?,?)", ("f-hn1", "thin", "t", "now"))
    c.commit()
    return c


LIVE = [
    {"id": "f-gh1", "name": "gh1", "source": "github", "score": 8.0},
    {"id": "f-gh2", "name": "gh2", "source": "github", "score": 6.0},
    {"id": "f-hn1", "name": "hn1", "source": "hn", "score": 4.0},
]


def test_decisions_attribute_to_the_sourcing_channel(conn):
    out = network._channel_outcomes(conn, LIVE)
    gh = out["github"]
    assert gh["founders"] == 2
    assert (gh["invested"], gh["passed"], gh["decided"]) == (1, 1, 2)
    assert gh["decision_yield"] == 0.5   # invest counts, pass does not
    assert gh["screen_killed"] == 0


def test_channel_without_decisions_reports_none_not_zero(conn):
    hn = network._channel_outcomes(conn, LIVE)["hn"]
    assert hn["decided"] == 0
    # None, never 0.0 — the whole point of the loop's honesty.
    assert hn["decision_yield"] is None
    assert hn["screen_killed"] == 1


def test_glow_tracks_median_signal_and_is_none_without_scores(conn):
    out = network._channel_outcomes(conn, LIVE)
    assert out["github"]["median_signal"] == 8.0   # sorted [6,8], upper median
    assert out["github"]["glow"] == 0.8
    assert out["hn"]["glow"] == 0.4

    unscored = network._channel_outcomes(
        conn, [{"id": "f-hn1", "name": "x", "source": "arxiv", "score": None}])
    assert unscored["arxiv"]["glow"] is None      # unlit, not dim
    assert unscored["arxiv"]["median_signal"] is None
