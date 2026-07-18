import { useEffect, useState } from "react";
import * as api from "../api";
import type { Channel, Outreach, SourcedFounder, SourcingFeed } from "../api";
import { Err, Skeleton } from "../components";

/* Page 1 — "It finds founders before they raise."
   Outbound: ranked thesis-matched feed + channel yields + Activate.
   Inbound: the apply form (deck + name is the minimum bar) — both tracks converge. */
export default function Sourcing({ thesis, openFounder }:
  { thesis: string; openFounder: (id: string) => void }) {
  const [feed, setFeed] = useState<SourcingFeed | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [outreach, setOutreach] = useState<{ fid: string; draft: Outreach } | null>(null);
  const [drafting, setDrafting] = useState<string | null>(null);

  useEffect(() => {
    setFeed(null);
    api.getSourcing(thesis).then(setFeed).catch((e) => setErr(e.message));
    api.getChannels().then((c) => { setChannels(c.channels); setSuggestion(c.suggestion); })
      .catch((e) => setErr(e.message));
  }, [thesis]);

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
          <ApplyForm />
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

function ApplyForm() {
  const [company, setCompany] = useState("");
  const [deck, setDeck] = useState("");
  const [state, setState] = useState<string | null>(null);
  const submit = async () => {
    setState("submitting…");
    try {
      const r = await api.postApply(company, deck);
      setState(r.duplicate
        ? "already on file (dedup) — nothing re-ingested"
        : r.screened
          ? `application ${r.founder_id} ingested + screened — see Screening`
          : `application ${r.founder_id} ingested — screening pending`);
    } catch (e) {
      setState(`⚠ ${(e as Error).message}`);
    }
  };
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
    </div>
  );
}
