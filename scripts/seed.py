"""CLI for the seed loader (logic lives in app/seed.py).

  python scripts/seed.py --snapshot   # dump local vc_brain.db -> fixtures/seed_db.sqlite
  python scripts/seed.py              # seed the active backend if empty (idempotent)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import seed  # noqa: E402

if __name__ == "__main__":
    if "--snapshot" in sys.argv:
        seed.snapshot()
    else:
        print("seeded" if seed.ensure_seeded() else "already seeded — no-op")
