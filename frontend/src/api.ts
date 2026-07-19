export interface Axis {
  axis: string;
  score?: number;
  stance?: string;
  coverage?: number;
  trend?: string;
  status?: string;
}
export interface ScorePoint {
  timestamp: string;
  score: number;
  trigger: string;
}
export interface FounderRow {
  id: string;
  name: string;
  source: string;
  axes: Axis[];
  signal: number | null;
  coverage: number;
  score_history_points: number;
  score_history: ScorePoint[];
  has_memo: boolean;
  latency_total: number;
}
export interface Claim {
  id: string;
  text: string;
  trust: number;
  corroboration: string;
  evidence_url: string;
  evidence_title?: string | null;
  evidence_excerpt?: string | null;
  retrieved_at?: string | null;
  source_type: string;
  evidence: string;
  stance: string;
  axis: string;
}
export interface Gap {
  field: string;
  status: string;
  rendered?: string;
  claim_ids?: string[];
}
export interface Brief {
  founder_id: string;
  decision: string | null;
  recommendation: {
    amount_usd?: number;
    claims_it_turns_on?: string[];
    what_would_change_our_mind?: string;
    open_items?: string[];
  } | null;
  axes: Axis[];
  gaps: Gap[];
  latency: { stages: [string, number][]; total_seconds: number };
  memo_md: string | null;
  claims: Claim[];
  score_history: ScorePoint[];
  signal: number | null;
  coverage: number;
}
export interface AskResult {
  question: string;
  answer: string;
  cited_claim_ids: string[];
  invalid_citations: string[];
  refused: boolean;
  validated: boolean;
}
export interface Thesis {
  file: string;
  name: string;
}
export interface SourcedFounder {
  id: string;
  name: string;
  signal: number | null;
  coverage: number;
  dimensions: Record<string, number | null>;
  entity_keys: Record<string, string>;
  sources: string[];
  signal_count: number;
  latest_signal_at: string | null;
  thesis_topic_match: number;
  screened: boolean;
  has_outreach: boolean;
}
export interface SourcingFeed {
  thesis: string;
  founders: SourcedFounder[];
  droplog_count: number;
}
export interface Channel {
  source: string;
  signals: number;
  resolved: number;
  founders: number;
  screened: number;
  resolve_rate: number;
}
export interface Trace {
  claim: Claim & { observed_at: string | null };
  signals: {
    id: string;
    source: string;
    source_url: string;
    content: string;
    observed_at: string | null;
    ingested_at: string;
  }[];
  rubric_trust: number;
  adjudication: {
    prosecution: string;
    defense: string;
    corroboration: string;
    trust: number;
    rationale: string;
    decided_at: string;
  } | null;
}
export interface RunStage {
  stage: string;
  status: string; // queued | running | ok | error
  detail: string;
  updated_at: string;
  seconds: number | null;
}
export interface RunStatus {
  founder_id: string;
  stages: RunStage[];
  has_memo: boolean;
  state: string; // running | ok | error | none
}
export interface ScanResult {
  source: string;
  topics: string[];
  counts: Record<string, number | string>;
  resolved: number;
  dropped: number;
  new_signals: number;
  new_founders: { id: string; name: string; new_signals: number }[];
}
export interface ApplyResult {
  founder_id: string;
  signal_id: string;
  duplicate: boolean;
  screened: boolean;
  screen_error: string | null;
  killed: boolean;
  run_started: boolean;
}
export interface QueryResult {
  query: string;
  error?: string; // parse failure — explained, nothing guessed
  criteria: { text: string; kind: string; value: string }[];
  ignored_criteria: { text: string; reason: string }[];
  results: {
    id: string;
    name: string;
    signal: number | null;
    coverage: number;
    sources: string[];
    matched_keywords: string[];
  }[];
}
export interface Methodology {
  signal: {
    name: string; what_it_is: string; formula: string;
    weights: Record<string, number>; dimensions: Record<string, string>;
  };
  coverage: { name: string; what_it_is: string; formula: string; areas: string[] };
  axes: {
    name: string; what_it_is: string; provider: string;
    kill_screen: { rubric: string; model: string };
    rubrics: Record<string, { rubric: string; model: string }>;
  };
  trust: {
    name: string; what_it_is: string; rubric: Record<string, number>;
    contested_tiers: string[]; tier_definitions: Record<string, string>;
  };
  for_founder?: {
    founder_id: string;
    signal: {
      value: number | null;
      dimensions: {
        name: string; value: number | null; weight: number; assessed: boolean;
        renormalized_weight: number | null; derivation: string | null;
      }[];
    };
    coverage: { value: number; areas: { area: string; covered: boolean }[] };
    claim_count: number; signal_count: number;
  };
}
export interface Quality {
  channels: Record<string, { ingested: number; resolved: number;
    distinct_founders: number; dropped: number }>;
  drop_reasons: Record<string, number>;
  kill_log: number;
  dedup_protected_signals: number;
  arxiv_pool: { ingested: number; resolved: number; awaiting_second_key: number; status: string };
  audit: { founders_with_blacklisted_keys: string[]; unlinked_infra_merge_signals: number;
    infra_domain_drops_at_resolve: number };
  notes: string;
}
export interface Outreach {
  subject: string;
  body: string;
  created_at?: string;
  triggering_signal_url?: string;
  triggering_signal?: string;
  cited_signal_url?: string;
}

/* Errors explain in a sentence — never a raw status code. Server-provided
   detail (incl. rate-limit messages) is always surfaced verbatim. */
const FRIENDLY: Record<number, string> = {
  404: "Nothing on record for this yet — it may not have been sourced or screened.",
  422: "The server couldn't process that input — check what you entered and try again.",
  500: "The server hit an internal error handling this request — try again in a moment.",
};
async function j<T>(u: string, init?: RequestInit): Promise<T> {
  const r = await fetch(u, init);
  if (!r.ok) {
    const detail = await r.json().catch(() => null);
    throw new Error(detail?.detail || FRIENDLY[r.status]
      || `The server couldn't complete this request (${r.status}) — try again in a moment.`);
  }
  return r.json();
}

export const getTheses = () => j<Thesis[]>("/api/theses");
export const getFounders = (thesis: string) =>
  j<FounderRow[]>(`/api/founders?thesis=${encodeURIComponent(thesis)}`);
export const getFounder = (id: string, thesis: string) =>
  j<Brief>(`/api/founders/${id}?thesis=${encodeURIComponent(thesis)}`);
export const getKilled = () => j<{ id: string; reason: string }[]>("/api/killed");
export const getSourcing = (thesis: string) =>
  j<SourcingFeed>(`/api/sourcing?thesis=${encodeURIComponent(thesis)}`);
export const getQuality = () => j<Quality>("/api/quality");
export const getChannels = () =>
  j<{ channels: Channel[]; suggestion: string | null }>("/api/channels");
export const getTrace = (fid: string, cid: string) =>
  j<Trace>(`/api/trace/${fid}/${cid}`);
/* Traces are immutable within a session: cache so the spotlight verdict line and
   the trace panel never fetch the same claim twice. */
const traceCache = new Map<string, Promise<Trace>>();
export const getTraceCached = (fid: string, cid: string): Promise<Trace> => {
  const k = `${fid}/${cid}`;
  let p = traceCache.get(k);
  if (!p) {
    p = getTrace(fid, cid);
    p.catch(() => traceCache.delete(k));
    traceCache.set(k, p);
  }
  return p;
};
export const postAsk = (fid: string, question: string) =>
  j<AskResult>(`/api/ask/${fid}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
export const getOutreach = (fid: string) => j<Outreach[]>(`/api/outreach/${fid}`);
export const postActivate = (fid: string, thesis: string) =>
  j<Outreach>(`/api/activate/${fid}?thesis=${encodeURIComponent(thesis)}`, { method: "POST" });
export const runQuery = (q: string) =>
  j<QueryResult>(`/api/query?q=${encodeURIComponent(q)}`);
export const postApply = (company: string, deck_text: string) =>
  j<ApplyResult>("/api/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, deck_text }),
  });
export const getRun = (fid: string) => j<RunStatus>(`/api/runs/${fid}`);
export const postScan = (source: string, thesis: string) =>
  j<ScanResult>(
    `/api/scan?source=${encodeURIComponent(source)}&thesis=${encodeURIComponent(thesis)}`,
    { method: "POST" },
  );
/* The global methodology (formulas/weights/rubrics) never changes within a
   session; a founder's breakdown only changes if their data changes. Cache both
   so opening the info panel on 5 different founder cards doesn't re-fetch. */
const methodologyCache = new Map<string, Promise<Methodology>>();
export const getMethodology = (founderId?: string): Promise<Methodology> => {
  const key = founderId || "__global__";
  let p = methodologyCache.get(key);
  if (!p) {
    const qs = founderId ? `?founder_id=${encodeURIComponent(founderId)}` : "";
    p = j<Methodology>(`/api/methodology${qs}`);
    p.catch(() => methodologyCache.delete(key));
    methodologyCache.set(key, p);
  }
  return p;
};
export const saveThesis = (cfg: object) =>
  j<Thesis>("/api/thesis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
