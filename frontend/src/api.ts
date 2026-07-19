export interface Axis {
  axis: string;
  score?: number;
  stance?: string;
  coverage?: number;
  trend?: string;
  status?: string;
}
export interface FounderRow {
  id: string;
  name: string;
  source: string;
  axes: Axis[];
  signal: number | null;
  coverage: number;
  score_history_points: number;
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
export interface QueryResult {
  query: string;
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
export interface Outreach {
  subject: string;
  body: string;
  created_at?: string;
  triggering_signal_url?: string;
  triggering_signal?: string;
  cited_signal_url?: string;
}

async function j<T>(u: string, init?: RequestInit): Promise<T> {
  const r = await fetch(u, init);
  if (!r.ok) {
    const detail = await r.json().catch(() => null);
    throw new Error(detail?.detail || `${r.status} ${r.statusText}`);
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
export const getChannels = () =>
  j<{ channels: Channel[]; suggestion: string | null }>("/api/channels");
export const getTrace = (fid: string, cid: string) =>
  j<Trace>(`/api/trace/${fid}/${cid}`);
export const getOutreach = (fid: string) => j<Outreach[]>(`/api/outreach/${fid}`);
export const postActivate = (fid: string, thesis: string) =>
  j<Outreach>(`/api/activate/${fid}?thesis=${encodeURIComponent(thesis)}`, { method: "POST" });
export const runQuery = (q: string) =>
  j<QueryResult>(`/api/query?q=${encodeURIComponent(q)}`);
export const postApply = (company: string, deck_text: string) =>
  j<{ founder_id: string; screened: boolean; duplicate: boolean }>("/api/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, deck_text }),
  });
export const saveThesis = (cfg: object) =>
  j<Thesis>("/api/thesis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
