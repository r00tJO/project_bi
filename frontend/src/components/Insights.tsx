import type { Cell, Column, ColumnKind, Dataset, Row } from "../types";
import { parseCsv } from "./csv";

const NULLS = new Set(["", "na", "n/a", "null", "nan", "none", "-"]);

export function toNumber(s: string): number | null {
  const v = s.trim();
  if (NULLS.has(v.toLowerCase())) return null;
  const c = v.replace(/[$€£%\s]/g, "").replace(/,(?=\d{3}(\D|$))/g, "");
  return /^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(c) ? Number(c) : null;
}

/** ISO (YYYY-MM[-DD][T..]) and day-first DD/MM/YYYY. Returns UTC epoch ms. */
export function toDate(s: string): number | null {
  const v = s.trim();
  const m = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(v);
  if (m) {
    const a = +m[1], b = +m[2];
    const [d, mo] = b > 12 ? [b, a] : [a, b];
    return Date.UTC(+m[3], mo - 1, d);
  }
  if (!/^\d{4}-\d{2}(-\d{2})?([T ]|$)/.test(v)) return null;
  const t = Date.parse(v.length === 7 ? `${v}-01` : v);
  return Number.isNaN(t) ? null : t;
}

const YEAR = /^(1[6-9]|20)\d{2}$/;
const toYear = (s: string): number | null => (YEAR.test(s.trim()) ? Date.UTC(+s.trim(), 0, 1) : null);

function kindOf(name: string, vals: string[], total: number): ColumnKind {
  const filled = vals.filter((v) => !NULLS.has(v.toLowerCase()));
  if (!filled.length) return "text";
  const ratio = (f: (s: string) => unknown) => filled.filter((v) => f(v) !== null).length / filled.length;
  if (ratio(toDate) >= 0.9) return "date";
  if (/(^|[_\s-])year$/i.test(name) && filled.every((v) => YEAR.test(v))) return "date";
  const distinct = new Set(filled).size;
  if (ratio(toNumber) >= 0.9) return /(^|[_\s-])(id|code|zip|ref)$/i.test(name) ? "text" : "number";
  return distinct <= Math.max(40, total * 0.05) ? "category" : "text";
}

export function buildDataset(text: string, name: string): Dataset {
  const table = parseCsv(text);
  if (table.length < 2) throw new Error("The file needs a header row and at least one data row.");
  const header = table[0].map((h, i) => h.trim() || `column_${i + 1}`);
  const body = table.slice(1);
  const columns: Column[] = [];
  const parsers: ((s: string) => Cell)[] = [];

  header.forEach((key, j) => {
    const vals = body.map((r) => (r[j] ?? "").trim());
    const kind = kindOf(key, vals, body.length);
    const parse = (s: string): Cell =>
      NULLS.has(s.toLowerCase())
        ? null
        : kind === "number" ? toNumber(s)
        : kind === "date" ? (toDate(s) ?? toYear(s))
        : s;
    parsers.push(parse);
    const parsed = vals.map(parse).filter((v): v is string | number => v !== null);
    const nums = kind === "number" || kind === "date" ? (parsed as number[]) : [];
    columns.push({
      key, kind,
      distinct: new Set(parsed).size,
      min: nums.length ? nums.reduce((a, b) => Math.min(a, b)) : null,
      max: nums.length ? nums.reduce((a, b) => Math.max(a, b)) : null,
      options: kind === "category" ? [...new Set(parsed as string[])].sort() : [],
    });
  });

  const rows: Row[] = body.map((r) => {
    const o: Row = {};
    header.forEach((k, j) => (o[k] = parsers[j]((r[j] ?? "").trim())));
    return o;
  });
  return { name, columns, rows };
}