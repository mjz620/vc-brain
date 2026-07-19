import { useCallback, useEffect, useState } from "react";
import * as api from "../api";
import type { Channel, Outreach, RunStatus, SourcedFounder, SourcingFeed } from "../api";
import { Err, Skeleton } from "../components";

const SCAN_SOURCES = ["github", "hn", "arxiv", "producthunt", "yc"];

/* Page 1 — "It finds founders before they raise."
   Outbound: ranked thesis-matched feed + channel yields + live Scan now + Activate.
   Inbound: the apply form (deck + name is the minimum bar) — both tracks converge. */
export default function Sourcing({ thesis, openFounder, openMemo }:
  { thesis: string; openFounder: (id: string) => void; openMemo: (id: string) => void }) {
  const [feed, setFeed] = useState<SourcingFeed | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [outreach, setOutreach] = useState<{ fid: string; draft: Outreach } | null>(null);
  const [drafting, setDrafting] = useState<string | null>(null);
  const [prevIds, setPrevIds] = useState<Set<string> | null>(null);

  const load = useCallback(() => {
    api.getSourcing(thesis).then(setFeed).catch((e) => setErr(e.message));
    api.getChannels().then((c) => { setChannels(c.channels); setSuggestion(c.suggestion); })
      .catch((e) => setErr(e.message));
  }, [thesis]);

  useEffect(() => { setFeed(null); setPrevIds(null); load(); }, [load]);

  // After a live scan: remember what was already known so new rows get flagged.
  const onScanDone = () => {
    setPrevIds(new Set((feed?.founders || []).map((f) => f.id)));
    load();
  };

  const activate = async (f: SourcedFounder) => {
    setDrafting(f.id);
    try {
      const drafts = f.has_outreach ? await api.getOutreach(f.id) : [];
      const draft = drafts[0] || (await api.postActivate(f.id, thesis));
      setOutreach({ fid: f.id, draft });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setDrafting(null);
    }
  };

  return (
    <div>
      <div className="page-h">
        <h1>Sourcing</h1>
        <p className="page-sub">
          Outbound scanner finds founders <b>before they raise</b>; inbound applications
          land in the same funnel. Nothing discarded
          {feed ? <> — <b>{feed.droplog_count}</b> unresolved signals retained in the drop-log</> : null}.
        </p>
      </div>

      <div className="section-h"><h2>Channel yield — sourcing graph</h2></div>
      <ScanNow thesis={thesis} onDone={onScanDone} />
      {channels.length === 0 ? <Skeleton lines={2} /> : (
        <div className="chan-row">
          {channels.filter((c) => !["deck", "web", "manual"].includes(c.source)).map((c) => (
            <div key={c.source} className="chan">
              <div className="chan-name">{c.source}</div>
              <div className="chan-funnel">
                <span title="signals scanned">{c.signals}</span> →{" "}
                <span title="resolved to founders">{c.resolved}</span> →{" "}
                <span title="screened">{c.screened}</span>
              </div>
              <div className="chan-rate">{Math.round(c.resolve_rate * 100)}% resolve</div>
            </div>
          ))}
        </div>
      )}
      {suggestion && <div className="suggestion">💡 {suggestion}</div>}

      <div className="twocol">
        <div>
          <div className="section-h"><h2>Outbound — ranked by thesis fit</h2>
            <span className="count">{feed ? `${feed.founders.length} resolved founders` : ""}</span>
          </div>
          {err && <Err msg={err} />}
          {!feed && !err && <Skeleton lines={8} />}
          {feed && (
            <table className="funnel">
              <thead>
                <tr><th>Founder</th><th>Channels</th><th>Fit</th><th>Signal / Cov</th><th></th></tr>
              </thead>
              <tbody>
                {feed.founders.slice(0, 25).map((f) => (
                  <tr key={f.id}>
                    <td className="fname" onClick={() => f.screened && openFounder(f.id)}
                        style={{ cursor: f.screened ? "pointer" : "default" }}>
                      {f.name}
                      {prevIds && !prevIds.has(f.id) && (
                        <span className="src" style={{ marginLeft: 5 }}
                          title="resolved by the last live scan">new</span>
                      )}
                      {f.signal != null && f.signal >= 7 && f.coverage < 0.3 && (
                        <span className="coldstart" title="high verified signal, thin record — the cold-start case">cold-start</span>
                      )}
                    </td>
                    <td>{f.sources.map((s) => <span key={s} className="src" style={{ marginRight: 3 }}>{s}</span>)}</td>
                    <td className="cov">{f.thesis_topic_match} topics · {f.signal_count} sig</td>
                    <td><b>{f.signal ?? "—"}</b> · <span className="cov">{Math.round(f.coverage * 100)}%</span></td>
                    <td>
                      <button className="minibtn" disabled={drafting === f.id}
                        onClick={() => activate(f)}>
                        {drafting === f.id ? "…" : f.has_outreach ? "outreach ✓" : "activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div>
          <div className="section-h"><h2>Inbound — apply</h2></div>
          <ApplyForm openMemo={openMemo} />
          {outreach && (
            <div className="outreach-card">
              <div className="section-h" style={{ margin: "0 0 8px" }}>
                <h2>Activate draft — {outreach.fid.replace("founder-", "")}</h2>
                <button className="x" onClick={() => setOutreach(null)}>×</button>
              </div>
              <div className="o-subject">{outreach.draft.subject}</div>
              <p className="o-body">{outreach.draft.body}</p>
              <div className="o-cite">
                cites triggering signal:{" "}
                <a href={outreach.draft.triggering_signal_url || outreach.draft.cited_signal_url}
                   target="_blank" rel="noreferrer">
                  {outreach.draft.triggering_signal_url || outreach.draft.cited_signal_url}
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ScanNow({ thesis, onDone }: { thesis: string; onDone: () => void }) {
  const [source, setSource] = useState("hn");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const go = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await api.postScan(source, thesis);
      const n = r.counts[source];
      setMsg(typeof n === "string"
        ? `⚠ ${source}: ${n}`
        : `${n} signals fetched live from ${source} — ${r.resolved} resolved, `
          + `${r.dropped} to drop-log`
          + (r.new_founders.length
            ? `; new founders: ${r.new_founders.map((f) => f.name).join(", ")}`
            : ""));
      onDone();
    } catch (e) {
      setMsg(`⚠ ${(e as Error).message}`);
    }
    setBusy(false);
  };
  return (
    <div style={{ margin: "0 0 12px", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <select className="control" value={source} onChange={(e) => setSource(e.target.value)}
        title="source to scan live (one per call — rate-limited)">
        {SCAN_SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
      <button className="minibtn primary" onClick={go} disabled={busy}>
        {busy ? "scanning live…" : "Scan now (live)"}
      </button>
      {msg && <span className="muted" style={{ fontSize: 12.5 }}>{msg}</span>}
    </div>
  );
}

const STATUS_MARK: Record<string, string> = { ok: "✓", error: "✗", running: "…", queued: "·" };

function ApplyForm({ openMemo }: { openMemo: (id: string) => void }) {
  const [company, setCompany] = useState("");
  const [deck, setDeck] = useState("");
  const [state, setState] = useState<string | null>(null);
  const [fid, setFid] = useState<string | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);

  const submit = async () => {
    setState("submitting… (screening runs before this returns)");
    setFid(null); setRun(null);
    try {
      const r = await api.postApply(company, deck);
      setState(r.screen_error
        ? `⚠ ${r.founder_id}: ${r.screen_error}`
        : r.killed
          ? `application ${r.founder_id} screened — killed at first pass (see run below)`
          : `application ${r.founder_id} ingested + screened — full diligence running`);
      setFid(r.founder_id);
    } catch (e) {
      setState(`⚠ ${(e as Error).message}`);
    }
  };

  // Poll the run every 1.5s until it reaches done/error — a watchable pipeline.
  useEffect(() => {
    if (!fid) return;
    if (run && run.state !== "running") return;
    const t = setInterval(() => { api.getRun(fid).then(setRun).catch(() => {}); }, 1500);
    return () => clearInterval(t);
  }, [fid, run]);

  return (
    <div className="apply">
      <p className="muted" style={{ margin: "0 0 8px", fontSize: 12.5 }}>
        Deck + company name is the whole bar — over-collecting works against you.
      </p>
      <input className="filter" placeholder="Company name" value={company}
        onChange={(e) => setCompany(e.target.value)} />
      <textarea className="filter" rows={6} placeholder="Paste deck text / summary…"
        value={deck} onChange={(e) => setDeck(e.target.value)} />
      <button className="minibtn primary" onClick={submit}
        disabled={!company.trim() || !deck.trim()}>Submit application</button>
      {state && <div className="muted" style={{ marginTop: 8, fontSize: 12.5 }}>{state}</div>}
      {fid && run && (
        <div style={{ marginTop: 10 }}>
          {run.stages.map((s) => (
            <div key={s.stage} className="muted" style={{ fontSize: 12.5 }}>
              {STATUS_MARK[s.status] || "·"} {s.stage} — {s.status}
              {s.seconds != null ? ` (${s.seconds.toFixed(1)}s)` : ""}
              {s.detail ? ` — ${s.detail}` : ""}
            </div>
          ))}
          {run.state === "ok" && run.has_memo && (
            <button className="minibtn primary" style={{ marginTop: 8 }}
              onClick={() => openMemo(fid)}>Open memo &amp; decision →</button>
          )}
        </div>
      )}
    </div>
  );
}
