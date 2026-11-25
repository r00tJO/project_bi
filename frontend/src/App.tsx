import { useCallback, useEffect, useMemo, useState } from "react";
import { Upload } from "lucide-react";
import Sidebar from "./components/Sidebar";
import FilterBar from "./components/FilterBar";
import Kpis from "./components/Kpis";
import { BreakdownChart, Histogram, RankList, TrendChart } from "./components/Charts";
import DataTable from "./components/DataTable";
import Insights from "./components/Insights";
import { applyFilters, groupBy, histogram, trend } from "./lib/aggregate";
import { buildDataset } from "./lib/infer";
import { fmtDate, label } from "./lib/format";
import type { Dataset, Filters, Selection } from "./types";

const NO_FILTERS: Filters = { search: "", from: "", to: "", cats: {} };
const firstOf = (ds: Dataset, kind: string) => ds.columns.find((c) => c.kind === kind)?.key ?? null;
const defaults = (ds: Dataset): Selection => ({
  measure: firstOf(ds, "number"), dimension: firstOf(ds, "category"), dateKey: firstOf(ds, "date"), agg: "sum",
});

// Regions and income groups (World, High income, OECD members...) are not countries
const AGG = /\b(world|income|IDA|IBRD|OECD|euro area|european union|small states|least developed|indebted|demographic|dividend|excluding|Middle East|East Asia|South Asia|Latin America|North America|Sub-Saharan|Europe & Central Asia|Central Europe|Africa Eastern|Africa Western|Caribbean)\b/i;
const entityKey = (ds: Dataset | null) =>
  ds?.columns.find((c) => c.kind === "category" && /^(country|nation|economy)( name)?$/i.test(c.key))?.key ?? null;

function Panel({ title, sub, children, wide }: { title: string; sub?: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <section className={`card panel ${wide ? "wide" : ""}`}>
      <header><h3>{title}</h3>{sub && <p>{sub}</p>}</header>
      {children}
    </section>
  );
}

function Loader({ onFile, hint }: { onFile: (f: File) => void; hint: string }) {
  return (
    <div className="card loader">
      <Upload size={28} />
      <h3>Load your dataset</h3>
      <p>{hint}</p>
      <label className="btn primary">
        Choose CSV file
        <input type="file" accept=".csv,.tsv,.txt" hidden onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      </label>
      <small>Or place it at <code>public/data.csv</code> and it loads automatically.</small>
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [ds, setDs] = useState<Dataset | null>(null);
  const [sel, setSel] = useState<Selection>({ measure: null, dimension: null, dateKey: null, agg: "sum" });
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [base, setBase] = useState<Filters>(NO_FILTERS);
  const [countriesOnly, setCountriesOnly] = useState(false);
  const [status, setStatus] = useState<"loading" | "ready" | "empty">("loading");
  const [error, setError] = useState("");

  const load = useCallback((text: string, name: string) => {
    try {
      const d = buildDataset(text, name);
      // pick one indicator by default so different units are never added together
      const pick = d.columns.find(
        (c) => c.kind === "category" && c.options.length > 1 && c.options.length <= 8 && /indicator|series|metric|measure/i.test(c.key),
      );
      const start: Filters = pick ? { ...NO_FILTERS, cats: { [pick.key]: pick.options[0] } } : NO_FILTERS;
      setDs(d);
      setSel({ ...defaults(d), agg: pick ? "avg" : "sum" });
      setBase(start);
      setFilters(start);
      setCountriesOnly(!!entityKey(d));
      setError("");
      setStatus("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read this file.");
      setStatus((s) => (s === "loading" ? "empty" : s));
    }
  }, []);

  useEffect(() => {
    fetch("/data.csv")
      .then((r) => (r.ok ? r.text() : ""))
      .then((t) => (t && !/^\s*<!doctype html/i.test(t) ? load(t, "data.csv") : setStatus("empty")))
      .catch(() => setStatus("empty"));
  }, [load]);

  const onFile = (f: File) => f.text().then((t) => load(t, f.name));
  const eKey = useMemo(() => entityKey(ds), [ds]);
  const rows = useMemo(() => {
    if (!ds) return [];
    const r = applyFilters(ds.rows, filters, sel.dateKey);
    return countriesOnly && eKey ? r.filter((x) => !AGG.test(String(x[eKey] ?? ""))) : r;
  }, [ds, filters, sel.dateKey, countriesOnly, eKey]);

  const m = sel.measure ? label(sel.measure) : "Records";
  const trendData = useMemo(() => trend(rows, sel.dateKey, sel.measure, sel.agg), [rows, sel]);
  const groups = useMemo(() => groupBy(rows, sel.dimension, sel.measure, sel.agg), [rows, sel]);
  const hist = useMemo(() => histogram(rows, sel.measure), [rows, sel.measure]);
  const aggName = `${sel.agg === "sum" ? "Total" : "Average"} ${m}`;
  const dim = sel.dimension ? label(sel.dimension) : "";

  let body: React.ReactNode;
  if (status === "loading") body = <p className="empty">Loading data…</p>;
  else if (!ds) body = <Loader onFile={onFile} hint={error || "No dataset found yet. Upload a CSV and the dashboard builds itself from its columns."} />;
  else if (activePage === "Settings")
    body = (
      <>
        <Panel title="Detected columns" sub={`${ds.name} · ${ds.rows.length.toLocaleString()} rows`} wide>
          <div className="table-wrap"><table>
            <thead><tr><th>Column</th><th>Type</th><th className="r">Distinct</th><th>Range</th></tr></thead>
            <tbody>{ds.columns.map((c) => (
              <tr key={c.key}><td>{c.key}</td><td><span className="badge neutral">{c.kind}</span></td><td className="r">{c.distinct.toLocaleString()}</td>
                <td>{c.min === null || c.max === null ? "–" : c.kind === "date" ? `${fmtDate(c.min)} → ${fmtDate(c.max)}` : `${c.min} → ${c.max}`}</td></tr>
            ))}</tbody>
          </table></div>
        </Panel>
        <Loader onFile={onFile} hint={error || "Replace the current dataset with another CSV."} />
      </>
    );
  else
    body = (
      <>
        <FilterBar ds={ds} filters={filters} sel={sel} total={ds.rows.length} shown={rows.length}
          onFilters={setFilters} onSel={setSel}
          onReset={() => { setFilters(base); setCountriesOnly(!!eKey); }} />
        {eKey && (
          <label className="toggle">
            <input type="checkbox" checked={countriesOnly} onChange={(e) => setCountriesOnly(e.target.checked)} />
            Countries only (hide regions and income groups)
          </label>
        )}
        {activePage === "Dashboard" && (
          <>
            <Kpis rows={rows} sel={sel} />
            <div className="grid">
              <Panel title={`${aggName} over time`} sub={sel.dateKey ? `By ${label(sel.dateKey)}` : undefined} wide>
                {sel.dateKey ? <TrendChart data={trendData} name={aggName} /> : <p className="empty">This dataset has no date column.</p>}
              </Panel>
              <Panel title={`${aggName} by ${dim || "segment"}`} sub="Top 10"><BreakdownChart data={groups} name={aggName} /></Panel>
              <Panel title={`${m} distribution`} sub="Records per value range"><Histogram data={hist} /></Panel>
            </div>
          </>
        )}
        {activePage === "Analytics" && (
          <div className="grid">
            <Panel title={`${aggName} by ${dim || "segment"}`} wide><BreakdownChart data={groups} name={aggName} /></Panel>
            <Panel title="Top performers"><RankList title={`Highest ${dim}`} tone="good" items={groups.slice(0, 5)} /></Panel>
            <Panel title="Bottom performers"><RankList title={`Lowest ${dim}`} tone="bad" items={[...groups].reverse().slice(0, 5)} /></Panel>
            <Panel title={`${m} distribution`} wide><Histogram data={hist} /></Panel>
          </div>
        )}
        {activePage === "Data Explorer" && <Panel title="Records" sub="Click a header to sort. Green and red cells mark the top and bottom 10%." wide><DataTable ds={ds} rows={rows} /></Panel>}
        {activePage === "Reports" && <Panel title="Key takeaways" sub="Generated from the records under the current filters" wide><Insights rows={rows} sel={sel} /></Panel>}
      </>
    );

  return (
    <div className="app-layout">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="main-content">
        <header className="top-header">
          <h2>{activePage}</h2>
          <span>{ds ? `${ds.name} · ${ds.rows.length.toLocaleString()} records` : "No dataset loaded"}</span>
        </header>
        <section className="page-content">{body}</section>
      </main>
    </div>
  );
}

export default App;