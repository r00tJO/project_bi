import type { Row, Selection } from "../types";
import { groupBy, periodChange, safeDiv, stats, trend } from "../lib/aggregate";
import { fmt, fmtPct, label } from "../lib/format";

export default function Insights({ rows, sel }: { rows: Row[]; sel: Selection }) {
  const out: string[] = [];
  const m = sel.measure ? label(sel.measure) : null;
  const s = stats(rows, sel.measure);
  const g = groupBy(rows, sel.dimension, sel.measure, sel.agg);
  const t = trend(rows, sel.dateKey, sel.measure, sel.agg);
  const ch = periodChange(rows, sel.dateKey, sel.measure);
  

  if (m && g.length > 1 && sel.dimension) {
    const total = g.reduce((a, b) => a + b.value, 0);
    out.push(`${g[0].name} leads ${label(sel.dimension)} on ${m} (${fmt(g[0].value)}${sel.agg === "sum" ? `, ${(safeDiv(g[0].value, total) * 100).toFixed(1)}% of the total` : ""}); ${g[g.length - 1].name} is lowest at ${fmt(g[g.length - 1].value)}.`);
  }
  if (t.length > 1) {
    const hi = t.reduce((a, b) => (b.value > a.value ? b : a));
    const lo = t.reduce((a, b) => (b.value < a.value ? b : a));
    out.push(`${m} peaks in ${hi.label} (${fmt(hi.value)}) and is weakest in ${lo.label} (${fmt(lo.value)}).`);
  }
  if (ch && ch.pct !== null) out.push(`${m} moved ${fmtPct(ch.pct)} between the earlier and later half of the selected period.`);
  if (m && s.count > 2 && s.sd > 0) {
    const n = rows.filter((r) => typeof r[sel.measure!] === "number" && Math.abs((r[sel.measure!] as number) - s.avg) > 2 * s.sd).length;
    out.push(n ? `${n.toLocaleString()} records sit more than two standard deviations from the average ${m} (${fmt(s.avg)}). Check them in Data Explorer.` : `No ${m} outliers beyond two standard deviations.`);
  }
  if (s.rows - s.count > 0 && m) out.push(`${(s.rows - s.count).toLocaleString()} records have no ${m} value and are excluded from the numbers above.`);

  if (!out.length) return <p className="empty">Not enough data under the current filters to summarise.</p>;
  return <ul className="insights">{out.map((x, i) => <li key={i}>{x}</li>)}</ul>;
}