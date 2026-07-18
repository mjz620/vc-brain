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
  signal: number;
  coverage: number;
  has_memo: boolean;
  latency_total: number;
}
export interface Claim {
  id: string;
  text: string;
  trust: number;
  corroboration: string;
  source_url: string;
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

const j = (u: string) => fetch(u).then((r) => r.json());

export const getTheses = (): Promise<Thesis[]> => j("/api/theses");
export const getFounders = (thesis: string): Promise<FounderRow[]> =>
  j(`/api/founders?thesis=${encodeURIComponent(thesis)}`);
export const getFounder = (id: string, thesis: string): Promise<Brief> =>
  j(`/api/founders/${id}?thesis=${encodeURIComponent(thesis)}`);
export const getKilled = (): Promise<{ id: string; reason: string }[]> =>
  j("/api/killed");
