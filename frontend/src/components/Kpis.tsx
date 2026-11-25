import { TrendingDown, TrendingUp } from "lucide-react";
import type { Row, Selection } from "../types";
import { periodChange, stats } from "../lib/aggregate";
import { fmt, fmtPct, label } from "../lib/format";

export default function Kpis({ rows, sel }: { rows: Row[]; sel: Selection }) {
  const s = stats(rows, sel.measure);
  const ch = periodChange(rows, sel.dateKey, sel.measure);
  const m = sel.measure ? label(sel.measure) : "";
  const cards = [
    { name: "Records", value: s.rows.toLocaleString(), note: sel.measure ? `${s.count.toLocaleString()} with ${m}` : "" },
    ...(sel.measure
      ? [
          { name: `Total ${m}`, value: fmt(s.sum), note: "" },
          { name: `Average ${m}`, value: fmt(s.avg), note: `Median ${fmt(s.median)}` },
          { name: `Peak ${m}`, value: fmt(s.max), note: `Lowest ${fmt(s.min)}` },
        ]
      : []),
  ];
  return (
    <div className="kpis">
      {cards.map((c) => (
        <div className="card kpi" key={c.name}>
          <span className="kpi-name">{c.name}</span>
          <strong className="kpi-value">{c.value}</strong>
          <span className="kpi-note">{c.note}</span>
        </div>
      ))}
      {ch && (
        <div className="card kpi">
          <span className="kpi-name">Later half vs. earlier half</span>
          <strong className={`kpi-value ${ch.pct === null ? "" : ch.pct >= 0 ? "up" : "down"}`}>
            {ch.pct !== null && (ch.pct >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />)} {fmtPct(ch.pct)}
          </strong>
          <span className="kpi-note">{fmt(ch.prev)} → {fmt(ch.cur)}</span>
        </div>
      )}
    </div>
  );
}