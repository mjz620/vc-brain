# TODO(mingjia): founder "what are they building" summary prompt.
#
# Human-owned override for the founder-summary panel (Sourcing / Screening).
# Until this stub is filled with real (non-comment) content, the code falls back to
# the embedded default in app/server.py (_SUMMARY_DEFAULT).
#
# The LLM is called with tier "screen" (haiku) and must return the _FounderSummary
# schema: `headline` (one line) + `summary` (2-3 sentences), grounded ONLY in the
# founder's signals. Must not invent funding/customers/metrics absent from the signals.
