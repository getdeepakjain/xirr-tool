import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api";
import { useProfiles } from "../profileStore";
import type { Analytics } from "../types";
import { money, pct, signClass } from "../format";

const COLORS = [
  "#6d8bff", "#34d399", "#fbbf24", "#f87171", "#a78bfa",
  "#22d3ee", "#f472b6", "#facc15", "#4ade80", "#fb923c",
];

export default function Dashboard() {
  const { selectedId, loading: profilesLoading } = useProfiles();
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    api
      .get<Analytics>(`/api/profiles/${selectedId}/analytics`)
      .then(({ data }) => setData(data))
      .finally(() => setLoading(false));
  }, [selectedId]);

  if (profilesLoading || loading) {
    return (
      <div className="center-screen">
        <div className="spinner" />
      </div>
    );
  }
  if (!data) return <div className="empty">No data yet.</div>;

  const p = data.portfolio;
  const allocation = Object.entries(data.by_asset_class)
    .map(([name, a]) => ({ name, value: a.current_value }))
    .filter((d) => d.value > 0);
  const xirrByClass = Object.entries(data.by_asset_class)
    .map(([name, a]) => ({ name, xirr: a.xirr_pct ?? 0 }))
    .filter((d) => d.xirr !== 0);

  const empty = p.count === 0;

  return (
    <>
      <h1>Portfolio Overview</h1>
      <small>As of {data.as_of}</small>

      {empty ? (
        <div className="empty">
          No holdings yet. Head to <b>Upload Excel</b> to import, or add them manually under{" "}
          <b>Holdings</b>.
        </div>
      ) : (
        <>
          <div className="grid cards" style={{ marginTop: "1rem" }}>
            <div className="card">
              <div className="stat-label">Invested</div>
              <div className="stat-value">{money(p.invested)}</div>
            </div>
            <div className="card">
              <div className="stat-label">Current Value</div>
              <div className="stat-value">{money(p.current_value)}</div>
            </div>
            <div className="card">
              <div className="stat-label">Total Gain</div>
              <div className={`stat-value ${signClass(p.gain)}`}>{money(p.gain)}</div>
              <div className={`stat-sub ${signClass(p.absolute_return_pct)}`}>
                {pct(p.absolute_return_pct)} absolute
              </div>
            </div>
            <div className="card">
              <div className="stat-label">Portfolio XIRR</div>
              <div className={`stat-value ${signClass(p.xirr_pct)}`}>{pct(p.xirr_pct)}</div>
              <div className="stat-sub">
                <small>{p.count} holdings</small>
              </div>
            </div>
          </div>

          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: "1.2rem" }}>
            <div className="panel">
              <h3>Asset Allocation</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={allocation} dataKey="value" nameKey="name" outerRadius={100} label>
                    {allocation.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => money(v)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="panel">
              <h3>XIRR by Asset Class</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={xirrByClass}>
                  <XAxis dataKey="name" stroke="#97a2c9" fontSize={12} />
                  <YAxis stroke="#97a2c9" fontSize={12} unit="%" />
                  <Tooltip formatter={(v: number) => `${v}%`} cursor={{ fill: "#1d2749" }} />
                  <Bar dataKey="xirr" radius={[6, 6, 0, 0]}>
                    {xirrByClass.map((d, i) => (
                      <Cell key={i} fill={d.xirr >= 0 ? "#34d399" : "#f87171"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="panel">
            <h3>By Asset Class</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Asset Class</th>
                    <th className="num">Holdings</th>
                    <th className="num">Invested</th>
                    <th className="num">Current</th>
                    <th className="num">Gain</th>
                    <th className="num">Abs %</th>
                    <th className="num">XIRR</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.by_asset_class).map(([ac, a]) => (
                    <tr key={ac}>
                      <td>
                        <span className="badge">{ac}</span>
                      </td>
                      <td className="num">{a.count}</td>
                      <td className="num">{money(a.invested)}</td>
                      <td className="num">{money(a.current_value)}</td>
                      <td className={`num ${signClass(a.gain)}`}>{money(a.gain)}</td>
                      <td className={`num ${signClass(a.absolute_return_pct)}`}>
                        {pct(a.absolute_return_pct)}
                      </td>
                      <td className={`num ${signClass(a.xirr_pct)}`}>{pct(a.xirr_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
