const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const plain = new Intl.NumberFormat("en", { maximumFractionDigits: 2 });

export const fmt = (n: number | null | undefined): string =>
  n === null || n === undefined || !Number.isFinite(n)
    ? "–"
    : Math.abs(n) >= 10000 ? compact.format(n) : plain.format(n);

export const fmtPct = (n: number | null): string =>
  n === null || !Number.isFinite(n) ? "n/a" : `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)}%`;

export const fmtDate = (t: number): string => new Date(t).toISOString().slice(0, 10);

export const label = (key: string): string =>
  key.replace(/[_-]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").trim();