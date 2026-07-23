import { useEffect, useState } from "react";
import api from "../api";
import { useProfiles } from "../profileStore";
import type { Insight } from "../types";

export default function Insights() {
  const { selectedId } = useProfiles();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    api
      .get<{ insights: Insight[] }>(`/api/profiles/${selectedId}/insights`)
      .then(({ data }) => setInsights(data.insights))
      .finally(() => setLoading(false));
  }, [selectedId]);

  return (
    <>
      <h1>Insights &amp; Suggestions</h1>
      <small>Automated observations based on your current holdings and their XIRR.</small>

      <div style={{ marginTop: "1.2rem" }}>
        {loading ? (
          <div className="spinner" />
        ) : insights.length === 0 ? (
          <div className="empty">
            No insights yet. Add holdings and set their latest prices / values to get suggestions.
          </div>
        ) : (
          insights.map((i, idx) => (
            <div key={idx} className={`insight ${i.level}`}>
              <h4>{i.title}</h4>
              <p>{i.detail}</p>
            </div>
          ))
        )}
      </div>
    </>
  );
}
