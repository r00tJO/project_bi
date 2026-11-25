import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";
import type { Dataset, Row } from "../types";
import { fmt, fmtDate, label } from "../lib/format";

const PAGE = 15;
const hue = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);

export default function DataTable({ ds, rows }: { ds: Dataset; rows: Row[] }) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const { key, dir } = sort;
    return [...rows].sort((a, b) => {
      const x = a[key], y = b[key];
      if (x === null || x === undefined) return 1; // nulls always last
      if (y === null || y === undefined) return -1;
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * dir;
    });
  }, [rows, sort]);

  // per-column scale + 10th/90th percentile for highlighting
  const scale = useMemo(() => {
    const o: Record<string, { max: number; lo: number; hi: number }> = {};
    for (const c of ds.columns.filter((c) => c.kind === "number")) {
      const v = rows.map((r) => r[c.key]).filter((x): x is number => typeof x === "number").sort((a, b) => a - b);
      if (v.length) o[c.key] = { max: Math.max(...v.map(Math.abs)), lo: v[Math.floor(v.length * 0.1)], hi: v[Math.floor(v.length * 0.9)] };
    }
    return o;
  }, [ds.columns, rows]);

  const pages = Math.max(1, Math.ceil(sorted.length / PAGE));
  const p = Math.min(page, pages - 1);
  const slice = sorted.slice(p * PAGE, p * PAGE + PAGE);
  const toggle = (key: string) =>
    setSort((s) => (s?.key === key ? (s.dir === 1 ? { key, dir: -1 } : null) : { key, dir: 1 }));

  if (!rows.length) return <p className="empty">No records match the current filters. Reset the filters to see all data.</p>;

  return (
    <>
      <div className="table-wrap">
        <table>
          <thead><tr>
            {ds.columns.map((c) => (
              <th key={c.key} className={c.kind === "number" ? "r" : ""} onClick={() => toggle(c.key)}>
                {label(c.key)}
                {sort?.key === c.key && (sort.dir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
              </th>
            ))}
          </tr></thead>
          <tbody>
            {slice.map((r, i) => (
              <tr key={i}>
                {ds.columns.map((c) => {
                  const v = r[c.key];
                  if (v === null || v === undefined) return <td key={c.key} className="null">–</td>;
                  if (c.kind === "number") {
                    const s = scale[c.key];
                    const n = v as number;
                    const tone = s && s.hi !== s.lo ? (n >= s.hi ? "hi" : n <= s.lo ? "lo" : "") : "";
                    return (
                      <td key={c.key} className={`r num ${tone}`}>
                        <span className="cellbar" style={{ width: `${s?.max ? (Math.abs(n) / s.max) * 100 : 0}%` }} />
                        <span className="cellval">{fmt(n)}</span>
                      </td>
                    );
                  }
                  if (c.kind === "date") return <td key={c.key}>{fmtDate(v as number)}</td>;
                  if (c.kind === "category")
                    return <td key={c.key}><span className="badge" style={{ background: `hsl(${hue(String(v))} 70% 93%)`, color: `hsl(${hue(String(v))} 55% 28%)` }}>{String(v)}</span></td>;
                  return <td key={c.key} className="text" title={String(v)}>{String(v)}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pager">
        <span>{p * PAGE + 1}–{Math.min((p + 1) * PAGE, sorted.length)} of {sorted.length.toLocaleString()}</span>
        <button className="btn ghost" disabled={p === 0} onClick={() => setPage(p - 1)} aria-label="Previous page"><ChevronLeft size={16} /></button>
        <span>Page {p + 1} / {pages}</span>
        <button className="btn ghost" disabled={p >= pages - 1} onClick={() => setPage(p + 1)} aria-label="Next page"><ChevronRight size={16} /></button>
      </div>
    </>
  );
}