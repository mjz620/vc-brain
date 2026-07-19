"""Evidence-extraction workers (spec §2.4). Parallel-in-spirit, one per focus area;
founder is deepest (integrity + timeline cross-check). These stay grounded and
non-adversarial — they extract claims from the founder's signals, they do not argue."""
from .. import llm
from ..promptlib import load_prompt
from .schemas import ClaimDraft, WorkerOutput

# (axis, id-prefix, focus). founder is deepest.
WORKERS = [
    ("founder", "team",
     "founder background, career timeline, execution track record, and INTEGRITY. "
     "Cross-check every claimed history item against dated external evidence (talks, "
     "filings, negative-result searches). Flag any claim the external record contradicts, "
     "and any timeline where two claimed full-time roles overlap."),
    ("market", "mkt", "market size, willingness to pay, and demand."),
    ("risk", "risk", "competition, defensibility, and the key risks to the business."),
    ("traction", "trac",
     "product existence, customers, revenue, and usage. Deck-only figures with no external "
     "corroboration are self_reported."),
    # news worker only runs when tavily signals exist in the evidence (see extract_all) —
    # skipping the call for tavily-free founders avoids wasted tokens AND cache-key churn.
    ("news", "news",
     "claims found in tavily news/web evidence: funding, launches, customers, coverage. "
     "Assign each claim its real axis (founder/market/traction/risk); source_type='tavily'; "
     "a lone article is single_source, an article agreeing with a deck claim is corroborated."),
]

_DEFAULT = (
    "You are a venture diligence analyst extracting the {axis} claims from a founder's "
    "evidence. Focus: {focus}\n"
    "Extract discrete, factual claims. For each: a unique id like '{prefix}-01'; the axis; "
    "the claim text; stance (supports/contradicts/neutral toward an investment); a short "
    "evidence snippet; the source_url it came from (copy it from the evidence); source_type; "
    "and corroboration — 'self_reported' for a deck/self claim with no external backing "
    "(these cap low), 'single_source' for one external source, 'corroborated' when >=2 "
    "independent sources agree, 'contradicted' when external evidence conflicts with the "
    "claim. A negative-result search (looked, found nothing) IS a claim with "
    "stance=contradicts and corroboration reflecting the search. Do not invent facts not in "
    "the evidence; do not assign trust scores."
)


def run_worker(evidence: str, axis: str, prefix: str, focus: str, *, replay: bool
               ) -> list[ClaimDraft]:
    system = load_prompt(f"worker_{axis}", _DEFAULT.format(axis=axis, prefix=prefix, focus=focus))
    user = (f"--- Founder evidence ---\n{evidence}\n\n"
            f"Extract the {axis}-axis claims. Use id prefix '{prefix}-'.")
    return llm.call("worker", system, user, WorkerOutput, replay=replay, max_tokens=2000).claims


# Workers that must NOT see market-research web pages (they'd manufacture false
# founder contradictions / mis-attributed traction). Everyone else sees full evidence.
_FOUNDER_SCOPED = {"founder", "traction"}


def _has_news(evidence: str) -> bool:
    """True if the evidence has a tavily NEWS signal (a tavily block that is not a
    market-research page). Market research alone must not trigger the news worker."""
    return any(block.lstrip().startswith("[tavily]") and "[market research" not in block
               for block in evidence.split("\n\n"))


def extract_all(evidence: str, *, replay: bool, founder_evidence: str | None = None
                ) -> list[ClaimDraft]:
    """founder_evidence (market-research signals removed) is fed to the integrity and
    traction workers; the rest see full evidence. Falls back to `evidence` for both
    when no scoped view is supplied (preserves the fixture/replay behaviour)."""
    founder_ev = founder_evidence if founder_evidence is not None else evidence
    drafts: list[ClaimDraft] = []
    seen: set[str] = set()
    for axis, prefix, focus in WORKERS:
        ev = founder_ev if axis in _FOUNDER_SCOPED else evidence
        if axis == "news" and not _has_news(ev):
            continue  # no tavily NEWS signals: skip (market research doesn't count)
        for c in run_worker(ev, axis, prefix, focus, replay=replay):
            cid = c.id
            while cid in seen:  # guarantee unique ids across workers
                cid += "x"
            c.id = cid
            seen.add(cid)
            drafts.append(c)
    return drafts
