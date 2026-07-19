import { useCallback, useEffect, useState } from "react";
import * as api from "./api";
import type { FounderRow, Thesis } from "./api";
import Sourcing from "./pages/Sourcing";
import Screening from "./pages/Screening";
import Diligence from "./pages/Diligence";
import Decision from "./pages/Decision";
import ThesisPage from "./pages/Thesis";
import Compare from "./pages/Compare";
import MethodologyPage from "./pages/Methodology";
import NetworkPage from "./pages/Network";
import Landing from "./pages/Landing";

/* Shell: left sidebar mirrors the brief's own pipeline — the nav teaches the
   architecture. Sourcing → Screening → Diligence → Decision, plus the Thesis lens. */

const PAGES = [
  { key: "sourcing", n: "1", label: "Sourcing" },
  { key: "screening", n: "2", label: "Screening" },
  { key: "diligence", n: "3", label: "Diligence" },
  { key: "decision", n: "4", label: "Memo & Decision" },
  { key: "thesis", n: "5", label: "Thesis & Query" },
  { key: "compare", n: "6", label: "Compare" },
  { key: "network", n: "7", label: "Sourcing Network" },
  { key: "methodology", n: "8", label: "Methodology" },
] as const;
type PageKey = (typeof PAGES)[number]["key"];

function useTheme(): [string, () => void] {
  const [t, setT] = useState(
    () => localStorage.getItem("theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("theme", t);
  }, [t]);
  return [t, () => setT(t === "dark" ? "light" : "dark")];
}

export default function App() {
  const [theme, toggle] = useTheme();
  const [entered, setEntered] = useState(() => sessionStorage.getItem("entered") === "1");
  const [page, setPage] = useState<PageKey>("sourcing");
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [thesis, setThesis] = useState("config/thesis_preseed_ai_infra.yaml");
  const [founderId, setFounderId] = useState<string | null>(null);
  const [memoFounders, setMemoFounders] = useState<{ id: string; name: string }[]>([]);

  const refreshTheses = useCallback(() => { api.getTheses().then(setTheses).catch(() => {}); }, []);
  useEffect(refreshTheses, [refreshTheses]);
  useEffect(() => {
    api.getFounders(thesis)
      .then((fs: FounderRow[]) =>
        setMemoFounders(fs.filter((f) => f.has_memo).map((f) => ({ id: f.id, name: f.name }))))
      .catch(() => {});
  }, [thesis, page]); // page dep: a live apply run may have landed a new memo

  // Empty id resets to the picker (the "all founders…" option in page switchers).
  const openDiligence = (id: string) => { setFounderId(id || null); setPage("diligence"); };
  const openDecision = (id: string) => { setFounderId(id || null); setPage("decision"); };

  if (!entered) {
    return <Landing onEnter={() => { sessionStorage.setItem("entered", "1"); setEntered(true); }} />;
  }

  return (
    <div className="shell">
      <nav className="side">
        <button className="brand brand-btn" onClick={() => setEntered(false)}
          title="back to the overview">FirstSignal<span className="dot">.</span></button>
        <div className="side-sub">the VC brain for evidence-grounded founder discovery</div>
        {PAGES.map((p) => (
          <button key={p.key} className={`nav ${page === p.key ? "on" : ""}`}
            onClick={() => setPage(p.key)}>
            <span className="nav-n">{p.n}</span>{p.label}
          </button>
        ))}
        <div className="side-foot">
          <select className="control" value={thesis}
            onChange={(e) => setThesis(e.target.value)} title="fund thesis lens">
            {theses.map((t) => <option key={t.file} value={t.file}>{t.name}</option>)}
          </select>
          <button className="control" onClick={toggle} title="toggle theme">
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </nav>

      <main className="main">
        {page === "sourcing" && (
          <Sourcing thesis={thesis} openFounder={openDiligence} openMemo={openDecision} />
        )}
        {page === "screening" && <Screening thesis={thesis} openFounder={openDecision} />}
        {page === "diligence" && (
          <Diligence thesis={thesis} founderId={founderId}
            founders={memoFounders} openFounder={openDiligence} />
        )}
        {page === "decision" && (
          <Decision thesis={thesis} founderId={founderId}
            founders={memoFounders} openFounder={openDecision} />
        )}
        {page === "thesis" && (
          <ThesisPage theses={theses} thesis={thesis} setThesis={setThesis}
            refreshTheses={refreshTheses} openFounder={openDecision} />
        )}
        {page === "compare" && <Compare thesis={thesis} openFounder={openDecision} />}
        {page === "network" && <NetworkPage />}
        {page === "methodology" && <MethodologyPage />}
      </main>
    </div>
  );
}
