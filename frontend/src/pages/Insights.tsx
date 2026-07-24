import { useEffect, useMemo, useState } from "react";
import api from "../api";
import { useProfiles } from "../profileStore";
import type { Insight } from "../types";

const LEVELS = ["critical", "warning", "info", "positive"] as const;
type Level = (typeof LEVELS)[number];

const LEVEL_LABEL: Record<Level, string> = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
  positive: "Positive",
};

// Higher = more urgent, used for severity sorting.
const SEVERITY: Record<Level, number> = { critical: 3, warning: 2, info: 1, positive: 0 };

type SortMode = "severity_desc" | "severity_asc" | "title";

export default function Insights() {
  const { selectedId } = useProfiles();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeLevel, setActiveLevel] = useState<Level | "all">("all");
  const [sortMode, setSortMode] = useState<SortMode>("severity_desc");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    api
      .get<{ insights: Insight[] }>(`/api/profiles/${selectedId}/insights`)
      .then(({ data }) => setInsights(data.insights))
      .finally(() => setLoading(false));
  }, [selectedId]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const i of insights) c[i.level] = (c[i.level] ?? 0) + 1;
    return c;
  }, [insights]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = insights.filter((i) => {
      if (activeLevel !== "all" && i.level !== activeLevel) return false;
      if (!q) return true;
      return (
        i.title.toLowerCase().includes(q) ||
        i.detail.toLowerCase().includes(q) ||
        (i.holding ?? "").toLowerCase().includes(q)
      );
    });
    list = [...list].sort((a, b) => {
      if (sortMode === "title") return a.title.localeCompare(b.title);
      const diff = SEVERITY[b.level as Level] - SEVERITY[a.level as Level];
      return sortMode === "severity_desc" ? diff : -diff;
    });
    return list;
  }, [insights, activeLevel, sortMode, query]);

  return (
    <>
      <h1>Insights &amp; Suggestions</h1>
      <small>Automated observations based on your current holdings and their XIRR.</small>

      {!loading && insights.length > 0 && (
        <div className="insights-toolbar">
          <div className="chip-row">
            <button
              className={`chip ${activeLevel === "all" ? "active" : ""}`}
              onClick={() => setActiveLevel("all")}
            >
              All · {insights.length}
            </button>
            {LEVELS.filter((l) => counts[l]).map((l) => (
              <button
                key={l}
                className={`chip chip-${l} ${activeLevel === l ? "active" : ""}`}
                onClick={() => setActiveLevel(l)}
              >
                {LEVEL_LABEL[l]} · {counts[l]}
              </button>
            ))}
          </div>
          <div className="insights-controls">
            <input
              className="insights-search"
              placeholder="Search insights…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <select value={sortMode} onChange={(e) => setSortMode(e.target.value as SortMode)}>
              <option value="severity_desc">Most urgent first</option>
              <option value="severity_asc">Least urgent first</option>
              <option value="title">Title (A–Z)</option>
            </select>
          </div>
        </div>
      )}

      <div style={{ marginTop: "1.2rem" }}>
        {loading ? (
          <div className="spinner" />
        ) : insights.length === 0 ? (
          <div className="empty">
            No insights yet. Add holdings and set their latest prices / values to get suggestions.
          </div>
        ) : visible.length === 0 ? (
          <div className="empty">No insights match the current filter.</div>
        ) : (
          visible.map((i, idx) => (
            <div key={idx} className={`insight ${i.level}`}>
              <div className="insight-top">
                <h4>{i.title}</h4>
                <span className={`status-pill ${i.level}`}>{LEVEL_LABEL[i.level as Level]}</span>
              </div>
              <p>{i.detail}</p>
              {i.holding && <small className="insight-holding">↳ {i.holding}</small>}
            </div>
          ))
        )}
      </div>
    </>
  );
}
