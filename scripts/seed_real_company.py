"""Seed ONE real, researchable company as the market-research showcase.

Unlike the fictional fixtures, this company exists on the open web, so the Tavily
market-research stage finds real TAM / competitors / comparable rounds and the memo
fills the full Appendix-1 template with externally-cited evidence.

Deck text is factual public-info positioning only — NO invented metrics; market
figures come from research, not the deck. Runs live once (OpenAI + Tavily), caching
everything so the demo replays deterministically.

Usage: VC_DB_PATH=<db> .venv/bin/python scripts/seed_real_company.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402
from app.diligence import pipeline  # noqa: E402
from app.memory import db, ingest  # noqa: E402
from app.memory.models import Founder, Signal  # noqa: E402
from app.screening import axes as axes_mod  # noqa: E402
from app.screening import thesis as thesis_mod  # noqa: E402

FID = "founder-langfuse"
NAME = "Langfuse"
DECK = (
    "Langfuse is an open-source LLM engineering platform providing observability, "
    "tracing, prompt management, and evaluations for teams building LLM and agent "
    "applications. Developers self-host the open-source core or use the managed cloud "
    "to debug, monitor, and evaluate LLM pipelines in production. Founded 2022 by Marc "
    "Klingen, Clemens Rawert, and Max Deichmann; went through Y Combinator (W23). "
    "Category: LLMOps — LLM observability and evaluation. Early-stage: strong "
    "open-source developer adoption, building out an enterprise offering. Raising to "
    "grow adoption and ship enterprise evaluation features."
)


def main():
    conn = db.connect()
    db.init_db(conn)
    thesis = thesis_mod.load_thesis(config.ROOT / "config/thesis_preseed_ai_infra.yaml")

    ingest.upsert_founder(conn, Founder(id=FID, name=NAME,
                                        entity_keys={"domain": "langfuse.com"}))
    ingest.ingest_signal(conn, Signal(source="deck", source_url=f"application://{FID}",
                                      content=DECK, observed_at=config.DEMO_TODAY,
                                      founder_id=FID))
    print("[screen] running first-pass + 3 axes...")
    res = axes_mod.screen(conn, FID, thesis, replay=False)
    if res.get("killed"):
        print("KILLED at first pass:", res.get("kill_reason"))
        return
    print("[diligence] running with live market research (Tavily)...")
    out = pipeline.run_diligence(conn, FID, thesis, replay=False, news=False, market=True)
    print(f"[done] decision={out['recommendation'].decision} claims={out['claims']} "
          f"contested={out['contested']} validator_ok={out['violations'].ok}")
    print("\n===== MEMO =====\n")
    print(out["memo"])


if __name__ == "__main__":
    main()
