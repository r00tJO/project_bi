import type { Agg, Filters, Row } from "../types";
import { fmt } from "./format";

const num = (c: unknown): number | null => (typeof c === "number" && Number.isFinite(c) ? c : null);
export const safeDiv = (a: number, b: number) => (b === 0 ? 0 : a / b);

export function applyFilters(rows: Row[], f: Filters, dateKey: string | null): Row[] {
  const q = f.search.trim().toLowerCase();
  const from = f.from ? Date.parse(f.from) : null;
  const to = f.to ? Date.parse(f.to) + 86_399_999 : null;
  const cats = Object.entries(f.cats).filter(([, v]) => v);
  return rows.filter((r) => {
    if (dateKey && (from !== null || to !== null)) {
      const d = num(r[dateKey]);
      if (d === null || (from !== null && d < from) || (to !== null && d > to)) return false;
    }
    for (const [k, v] of cats) if (r[k] !== v) return false;
    if (q && !Object.values(r).some((c) => typeof c === "string" && c.toLowerCase().includes(q))) return false;
    return true;
  });
}

const values = (rows: Row[], key: string | null) =>
  key ? rows.map((r) => num(r[key])).filter((x): x is number => x !== null) : [];

export function stats(rows: Row[], key: string | null) {
  const v = values(rows, key);
  const count = v.length;
  const sum = v.reduce((a, b) => a + b, 0);
  const avg = safeDiv(sum, count);
  const s = [...v].sort((a, b) => a - b);
  const median = count ? (count % 2 ? s[(count - 1) / 2] : (s[count / 2 - 1] + s[count / 2]) / 2) : 0;
  const sd = Math.sqrt(safeDiv(v.reduce((a, b) => a + (b - avg) ** 2, 0), count));

  return { rows: rows.length, count, sum, avg, median, sd, min: count ? s[0] : 0, max: count ? s[count - 1] : 0 };
}

const pairs = (rows: Row[], dateKey: string | null, measure: string | null) =>
  dateKey && measure
    ? rows
        .map((r) => [num(r[dateKey]), num(r[measure])] as const)
        .filter((p): p is readonly [number, number] => p[0] !== null && p[1] !== null)
    : [];

export function trend(rows: Row[], dateKey: string | null, measure: string | null, agg: Agg) {
  const pts = pairs(rows, dateKey, measure);
  if (!pts.length) return [];
  const lo = pts.reduce((a, p) => Math.min(a, p[0]), Infinity);
  const hi = pts.reduce((a, p) => Math.max(a, p[0]), -Infinity);
  const days = (hi - lo) / 864e5;
  const len = days > 730 ? 4 : days > 92 ? 7 : 10; // year / month / day buckets
  const m = new Map<string, { sum: number; n: number }>();
  for (const [t, v] of pts) {
    const k = new Date(t).toISOString().slice(0, len);
    const e = m.get(k) ?? { sum: 0, n: 0 };
    e.sum += v; e.n++;
    m.set(k, e);
  }
  return [...m]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([label, e]) => ({ label, value: agg === "sum" ? e.sum : safeDiv(e.sum, e.n) }));
}

export function groupBy(rows: Row[], dim: string | null, measure: string | null, agg: Agg) {
  if (!dim) return [];
  const m = new Map<string, { sum: number; n: number }>();
  for (const r of rows) {
    const k = r[dim];
    if (k === null || k === undefined) continue;
    const e = m.get(String(k)) ?? { sum: 0, n: 0 };
    e.n++;
    const x = measure ? num(r[measure]) : null;
    if (x !== null) e.sum += x;
    m.set(String(k), e);
  }
  return [...m]
    .map(([name, e]) => ({ name, count: e.n, value: !measure ? e.n : agg === "sum" ? e.sum : safeDiv(e.sum, e.n) }))
    .sort((a, b) => b.value - a.value);
}

/** Second half of the visible date range vs. the first half. */
export function periodChange(rows: Row[], dateKey: string | null, measure: string | null) {
  const pts = pairs(rows, dateKey, measure);
  if (pts.length < 2) return null;
  const lo = pts.reduce((a, p) => Math.min(a, p[0]), Infinity);
  const hi = pts.reduce((a, p) => Math.max(a, p[0]), -Infinity);
  if (lo === hi) return null;
  const mid = (lo + hi) / 2;
  let prev = 0, cur = 0;
  for (const [t, v] of pts) (t < mid ? (prev += v) : (cur += v));
  return { prev, cur, pct: prev === 0 ? null : (cur - prev) / Math.abs(prev) };
}

export function histogram(rows: Row[], measure: string | null, bins = 12) {
  const v = values(rows, measure);
  if (!v.length) return [];
  const lo = v.reduce((a, b) => Math.min(a, b));
  const hi = v.reduce((a, b) => Math.max(a, b));
  if (lo === hi) return [{ label: fmt(lo), count: v.length }];
  const w = (hi - lo) / bins;
  const c = new Array<number>(bins).fill(0);
  for (const x of v) c[Math.min(bins - 1, Math.floor((x - lo) / w))]++;
  return c.map((count, i) => ({ label: fmt(lo + i * w), count }));
}