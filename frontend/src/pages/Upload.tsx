import { useRef, useState } from "react";
import api, { apiError } from "../api";
import { useProfiles } from "../profileStore";
import type { ImportSummary } from "../types";

export default function Upload() {
  const { selectedId, selected } = useProfiles();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportSummary | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setError("");
    setResult(null);
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post<ImportSummary>(
        `/api/profiles/${selectedId}/upload`,
        fd,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResult(data);
    } catch (err) {
      setError(apiError(err, "Upload failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Upload Excel</h1>
      <small>
        Importing into <b>{selected?.name}</b>. Only new transactions are added — existing ones are
        skipped automatically.
      </small>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <div
          style={{
            border: "2px dashed var(--border)",
            borderRadius: 14,
            padding: "2.5rem 1rem",
            textAlign: "center",
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) upload(f);
          }}
        >
          <div style={{ fontSize: "2.2rem" }}>📄</div>
          <p style={{ color: "var(--muted)" }}>
            Drag &amp; drop your workbook here, or
          </p>
          <button className="btn btn-primary" disabled={busy} onClick={() => inputRef.current?.click()}>
            {busy ? "Importing…" : "Choose .xlsx file"}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xlsm"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
              e.target.value = "";
            }}
          />
          <p style={{ marginTop: "1rem" }}>
            <small>
              Supported tabs: Stocks, FD, PF, Gratuity, NPS - Tier I / II, MF, Policies, Bonds,
              Crypto
            </small>
          </p>
        </div>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {result && (
        <div className="panel">
          <h3>Import summary · {result.filename}</h3>
          <div className="grid cards">
            <div className="card">
              <div className="stat-label">Rows parsed</div>
              <div className="stat-value">{result.totals.parsed}</div>
            </div>
            <div className="card">
              <div className="stat-label">New transactions</div>
              <div className="stat-value pos">{result.totals.new_transactions}</div>
            </div>
            <div className="card">
              <div className="stat-label">Duplicates skipped</div>
              <div className="stat-value warn">{result.totals.duplicates}</div>
            </div>
            <div className="card">
              <div className="stat-label">New holdings</div>
              <div className="stat-value">{result.totals.holdings_created}</div>
            </div>
          </div>

          <div className="table-wrap" style={{ marginTop: "1rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Asset Class</th>
                  <th className="num">Parsed</th>
                  <th className="num">New</th>
                  <th className="num">Duplicates</th>
                  <th className="num">New Holdings</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.by_asset_class).map(([ac, s]) => (
                  <tr key={ac}>
                    <td><span className="badge">{ac}</span></td>
                    <td className="num">{s.parsed}</td>
                    <td className="num pos">{s.new_transactions}</td>
                    <td className="num warn">{s.duplicates}</td>
                    <td className="num">{s.holdings_created}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.errors.length > 0 && (
            <div className="error-msg" style={{ marginTop: "1rem" }}>
              {result.errors.map((e, i) => (
                <div key={i}>{e}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
