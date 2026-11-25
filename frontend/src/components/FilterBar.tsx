import { RotateCcw, Search } from "lucide-react";
import type { Dataset, Filters, Selection } from "../types";
import { label } from "../lib/format";

interface Props {
  ds: Dataset;
  filters: Filters;
  sel: Selection;
  total: number;
  shown: number;
  onFilters: (f: Filters) => void;
  onSel: (s: Selection) => void;
  onReset: () => void;
}

export default function FilterBar({ ds, filters, sel, total, shown, onFilters, onSel, onReset }: Props) {
  const nums = ds.columns.filter((c) => c.kind === "number");
  const cats = ds.columns.filter((c) => c.kind === "category");
  const dates = ds.columns.filter((c) => c.kind === "date");
  const set = (p: Partial<Filters>) => onFilters({ ...filters, ...p });

  return (
    <div className="filterbar">
      <div className="filter-row">
        <label className="field grow">
          <span>Search</span>
          <div className="input-icon">
            <Search size={15} />
            <input value={filters.search} placeholder="Search text columns" onChange={(e) => set({ search: e.target.value })} />
          </div>
        </label>
        {sel.dateKey && (
          <>
            <label className="field"><span>From</span>
              <input type="date" value={filters.from} onChange={(e) => set({ from: e.target.value })} /></label>
            <label className="field"><span>To</span>
              <input type="date" value={filters.to} onChange={(e) => set({ to: e.target.value })} /></label>
          </>
        )}
        {cats.slice(0, 4).map((c) => (
          <label className="field" key={c.key}><span>{label(c.key)}</span>
            <select value={filters.cats[c.key] ?? ""} onChange={(e) => set({ cats: { ...filters.cats, [c.key]: e.target.value } })}>
              <option value="">All</option>
              {c.options.map((o) => <option key={o}>{o}</option>)}
            </select>
          </label>
        ))}
        <button className="btn ghost" onClick={onReset}><RotateCcw size={14} /> Reset filters</button>
      </div>

      <div className="filter-row view-row">
        <label className="field"><span>Measure</span>
          <select value={sel.measure ?? ""} disabled={!nums.length} onChange={(e) => onSel({ ...sel, measure: e.target.value || null })}>
            {nums.map((c) => <option key={c.key} value={c.key}>{label(c.key)}</option>)}
          </select></label>
        <label className="field"><span>Group by</span>
          <select value={sel.dimension ?? ""} disabled={!cats.length} onChange={(e) => onSel({ ...sel, dimension: e.target.value || null })}>
            {cats.map((c) => <option key={c.key} value={c.key}>{label(c.key)}</option>)}
          </select></label>
        {dates.length > 1 && (
          <label className="field"><span>Date column</span>
            <select value={sel.dateKey ?? ""} onChange={(e) => onSel({ ...sel, dateKey: e.target.value || null })}>
              {dates.map((c) => <option key={c.key} value={c.key}>{label(c.key)}</option>)}
            </select></label>
        )}
        <div className="field"><span>Aggregate</span>
          <div className="seg">
            {(["sum", "avg"] as const).map((a) => (
              <button key={a} className={sel.agg === a ? "on" : ""} onClick={() => onSel({ ...sel, agg: a })}>{a === "sum" ? "Total" : "Average"}</button>
            ))}
          </div></div>
        <p className="count">{shown.toLocaleString()} of {total.toLocaleString()} records</p>
      </div>
    </div>
  );
}