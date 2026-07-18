Parse an investor's compound natural-language founder query into structured criteria. Memory can evaluate ONLY these criterion kinds:
- keyword: a sector/technology/traction term matched against signal text. Expand investor shorthand into the terms that actually appear in signals: "AI infra" -> keywords "llm", "infra", "agents", "inference"; "enterprise traction" -> "enterprise", "customers".
- source: restrict to a sourcing channel: github, hn, arxiv, producthunt, yc. Map: "top-tier accelerator" -> yc; "published research" / "papers" -> arxiv; "technical founder" / "ships code" -> github; "launched publicly" -> producthunt or hn.
- score: a minimum Founder Score 0-10; value is the number ("strong signal" -> 7).

HONESTY RULE: anything Memory cannot evaluate — geography, prior VC backing, headcount, education, demographics, revenue thresholds — MUST be kind=not_evaluable with a one-line reason in value ("no funding-history source ingested; cannot verify absence of VC backing"). Never force a non-evaluable fragment into a keyword: a keyword match on "berlin" against repo text is a false filter, worse than an honest flag.

Split the query exhaustively: every fragment of the investor's query lands in exactly one criterion, text = the fragment verbatim.
