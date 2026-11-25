import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt } from "../lib/format";

const BLUE = "#2563eb", GRID = "#e2e8f0", MUTED = "#64748b";
const tip = { formatter: (v: unknown) => fmt(Number(v)), contentStyle: { borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13 } };

export const Empty = ({ text }: { text: string }) => <p className="empty">{text}</p>;

export function TrendChart({ data, name }: { data: { label: string; value: number }[]; name: string }) {
  if (!data.length) return <Empty text="No dated values match the current filters." />;
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ left: 0, right: 12, top: 8 }}>
        <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={BLUE} stopOpacity={0.25} /><stop offset="100%" stopColor={BLUE} stopOpacity={0} />
        </linearGradient></defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={{ fill: MUTED, fontSize: 12 }} minTickGap={32} />
        <YAxis tick={{ fill: MUTED, fontSize: 12 }} tickFormatter={(v) => fmt(Number(v))} width={52} />
        <Tooltip {...tip} />
        <Area type="monotone" dataKey="value" name={name} stroke={BLUE} strokeWidth={2} fill="url(#g)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function BreakdownChart({ data, name }: { data: { name: string; value: number }[]; name: string }) {
  if (!data.length) return <Empty text="No category column to group by." />;
  const top = data.slice(0, 10);
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, top.length * 32 + 30)}>
      <BarChart data={top} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={{ fill: MUTED, fontSize: 12 }} tickFormatter={(v) => fmt(Number(v))} />
        <YAxis type="category" dataKey="name" width={110} tick={{ fill: "#1e293b", fontSize: 12 }} />
        <Tooltip {...tip} cursor={{ fill: "#f1f5f9" }} />
        <Bar dataKey="value" name={name} fill={BLUE} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function Histogram({ data }: { data: { label: string; count: number }[] }) {
  if (!data.length) return <Empty text="No numeric values to plot." />;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ right: 12 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={{ fill: MUTED, fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fill: MUTED, fontSize: 12 }} width={40} />
        <Tooltip formatter={(v) => Number(v).toLocaleString()} contentStyle={tip.contentStyle} cursor={{ fill: "#f1f5f9" }} />
        <Bar dataKey="count" name="Records" fill="#0f766e" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RankList({ title, items, tone }: { title: string; items: { name: string; value: number }[]; tone: "good" | "bad" }) {
  const max = Math.max(...items.map((i) => Math.abs(i.value)), 0);
  return (
    <div>
      <h4 className="rank-title">{title}</h4>
      {!items.length && <Empty text="Nothing to rank." />}
      <ol className="rank">
        {items.map((i) => (
          <li key={i.name}>
            <span className="rank-name" title={i.name}>{i.name}</span>
            <span className="rank-bar"><i className={tone} style={{ width: `${max ? (Math.abs(i.value) / max) * 100 : 0}%` }} /></span>
            <b>{fmt(i.value)}</b>
          </li>
        ))}
      </ol>
    </div>
  );
}