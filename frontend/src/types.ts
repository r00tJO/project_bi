export type Cell = string | number | null;
export type Row = Record<string, Cell>;
export type ColumnKind = "number" | "date" | "category" | "text";

export interface Column {
  key: string;
  kind: ColumnKind;
  distinct: number;
  min: number | null;
  max: number | null;
  options: string[];
}
export interface Dataset {
  name: string;
  columns: Column[];
  rows: Row[];
}
export interface Filters {
  search: string;
  from: string;
  to: string;
  cats: Record<string, string>;
}
export type Agg = "sum" | "avg";
export interface Selection {
  measure: string | null;
  dimension: string | null;
  dateKey: string | null;
  agg: Agg;
}