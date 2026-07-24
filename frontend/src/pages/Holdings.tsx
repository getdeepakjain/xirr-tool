import { useEffect, useState } from "react";
import api, { apiError } from "../api";
import Modal from "../components/Modal";
import { useProfiles } from "../profileStore";
import { ASSET_CLASSES } from "../types";
import type {
  Analytics,
  Holding,
  HoldingMetric,
  PriceRefreshResponse,
  PriceRefreshResult,
  Transaction,
} from "../types";
import { money, num, pct, signClass } from "../format";

const UNIT_PRICED = ["MF", "Stocks", "NPS", "Crypto"];

type SortKey =
  | "name"
  | "asset_class"
  | "units"
  | "latest_price"
  | "invested"
  | "current_value"
  | "gain"
  | "xirr_pct"
  | "txn_count";

const SORT_COLUMNS: { key: SortKey; label: string; num: boolean }[] = [
  { key: "name", label: "Name", num: false },
  { key: "asset_class", label: "Class", num: false },
  { key: "units", label: "Units", num: true },
  { key: "latest_price", label: "Latest", num: true },
  { key: "invested", label: "Invested", num: true },
  { key: "current_value", label: "Current", num: true },
  { key: "gain", label: "Gain", num: true },
  { key: "xirr_pct", label: "XIRR", num: true },
  { key: "txn_count", label: "Txns", num: true },
];

export default function Holdings() {
  const { selectedId } = useProfiles();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [filter, setFilter] = useState<string>("All");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Holding | null>(null);
  const [creating, setCreating] = useState(false);
  const [txnFor, setTxnFor] = useState<HoldingMetric | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("current_value");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [refreshing, setRefreshing] = useState(false);
  const [notice, setNotice] = useState<string>("");
  const [refreshLog, setRefreshLog] = useState<PriceRefreshResult[] | null>(null);

  async function reload() {
    if (!selectedId) return;
    setLoading(true);
    const { data } = await api.get<Analytics>(`/api/profiles/${selectedId}/analytics`);
    setAnalytics(data);
    setLoading(false);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const rows = (analytics?.holdings ?? [])
    .filter((h) => filter === "All" || h.asset_class === filter)
    .slice()
    .sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      let cmp: number;
      if (typeof av === "string" || typeof bv === "string") {
        cmp = String(av ?? "").localeCompare(String(bv ?? ""));
      } else {
        // null/undefined always sort to the bottom regardless of direction
        const an = av == null;
        const bn = bv == null;
        if (an && bn) cmp = 0;
        else if (an) return 1;
        else if (bn) return -1;
        else cmp = (av as number) - (bv as number);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "name" || key === "asset_class" ? "asc" : "desc");
    }
  }

  async function delHolding(id: number) {
    if (!confirm("Delete this holding and all its transactions?")) return;
    await api.delete(`/api/holdings/${id}`);
    reload();
  }

  async function openEdit(id: number) {
    const { data } = await api.get<Holding[]>(`/api/profiles/${selectedId}/holdings`);
    const h = data.find((x) => x.id === id) ?? null;
    setEditing(h);
  }

  async function downloadCsv(kind: "holdings" | "transactions") {
    if (!selectedId) return;
    try {
      const params = filter !== "All" ? { asset_class: filter } : undefined;
      const { data } = await api.get(
        `/api/profiles/${selectedId}/export/${kind}.csv`,
        { responseType: "blob", params }
      );
      const url = URL.createObjectURL(new Blob([data], { type: "text/csv" }));
      const suffix = filter !== "All" ? `_${filter}` : "";
      const a = document.createElement("a");
      a.href = url;
      a.download = `${kind}${suffix}_${selectedId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setNotice(apiError(err, "Export failed"));
    }
  }

  async function refreshPrices() {
    if (!selectedId) return;
    setRefreshing(true);
    setNotice("");
    setRefreshLog(null);
    try {
      const { data } = await api.post<PriceRefreshResponse>(
        `/api/profiles/${selectedId}/refresh-prices`
      );
      const c = data.counts;
      setNotice(
        `Prices refreshed - ${c.updated ?? 0} updated, ${c.unchanged ?? 0} unchanged, ` +
          `${c.not_found ?? 0} not found, ${c.error ?? 0} errored.`
      );
      // Surface problems (errors / unmatched) first so they're easy to see.
      const order: Record<string, number> = { error: 0, not_found: 1, updated: 2, unchanged: 3 };
      setRefreshLog(
        [...data.results].sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9))
      );
      await reload();
    } catch (err) {
      setNotice(apiError(err, "Price refresh failed"));
    } finally {
      setRefreshing(false);
    }
  }

  const refreshProblems = (refreshLog ?? []).filter(
    (r) => r.status === "error" || r.status === "not_found"
  );

  return (
    <>
      <div className="panel-head">
        <h1>Holdings</h1>
        <div className="row-actions">
          <button className="btn" disabled={refreshing} onClick={refreshPrices}>
            {refreshing ? "Refreshing…" : "↻ Refresh prices"}
          </button>
          <button className="btn" onClick={() => downloadCsv("holdings")}>
            ⬇ Holdings CSV{filter !== "All" ? ` (${filter})` : ""}
          </button>
          <button className="btn" onClick={() => downloadCsv("transactions")}>
            ⬇ Transactions CSV{filter !== "All" ? ` (${filter})` : ""}
          </button>
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            + Add Holding
          </button>
        </div>
      </div>

      {notice && (
        <div className="notice" style={{ marginBottom: "1rem" }}>
          {notice}
        </div>
      )}

      {refreshLog && refreshLog.length > 0 && (
        <div className="panel" style={{ marginBottom: "1rem" }}>
          <div className="panel-head">
            <h3 style={{ margin: 0 }}>
              Price refresh log
              {refreshProblems.length > 0 && (
                <span className="neg"> · {refreshProblems.length} need attention</span>
              )}
            </h3>
            <button className="btn btn-sm btn-ghost" onClick={() => setRefreshLog(null)}>
              Dismiss
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Holding</th>
                  <th>Class</th>
                  <th className="num">Old</th>
                  <th className="num">New</th>
                  <th>Status</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {refreshLog.map((r) => (
                  <tr key={r.holding_id}>
                    <td>{r.name}</td>
                    <td>
                      <span className="badge">{r.asset_class}</span>
                    </td>
                    <td className="num">{r.old_price != null ? num(r.old_price) : "—"}</td>
                    <td className="num">{r.new_price != null ? num(r.new_price) : "—"}</td>
                    <td>
                      <span className={`status-pill ${r.status}`}>
                        {r.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="wrap-cell">
                      <small>
                        {r.detail ||
                          (r.status === "not_found"
                            ? "No market match for this holding's name/symbol."
                            : "")}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="chip-row" style={{ marginBottom: "1rem" }}>
        {["All", ...ASSET_CLASSES].map((c) => (
          <button
            key={c}
            className={`chip ${filter === c ? "active" : ""}`}
            onClick={() => setFilter(c)}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="panel">
        {loading ? (
          <div className="spinner" />
        ) : rows.length === 0 ? (
          <div className="empty">No holdings in this view. Add one or upload an Excel file.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {SORT_COLUMNS.map((col) => (
                    <th
                      key={col.key}
                      className={`sortable ${col.num ? "num" : ""} ${
                        sortKey === col.key ? "sorted" : ""
                      }`}
                      onClick={() => toggleSort(col.key)}
                    >
                      {col.label}
                      <span className="sort-arrow">
                        {sortKey === col.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                      </span>
                    </th>
                  ))}
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((h) => (
                  <tr key={h.holding_id}>
                    <td>
                      {h.name}
                      {h.identifier ? <small> · {h.identifier}</small> : null}
                    </td>
                    <td>
                      <span className="badge">{h.asset_class}</span>
                    </td>
                    <td className="num">{h.units ? num(h.units, 3) : "—"}</td>
                    <td className="num">{h.latest_price ? num(h.latest_price) : "—"}</td>
                    <td className="num">{money(h.invested)}</td>
                    <td className="num">{money(h.current_value)}</td>
                    <td className={`num ${signClass(h.gain)}`}>{money(h.gain)}</td>
                    <td className={`num ${signClass(h.xirr_pct)}`}>{pct(h.xirr_pct)}</td>
                    <td className="num">{h.txn_count}</td>
                    <td>
                      <div className="row-actions">
                        <button className="btn btn-sm" onClick={() => setTxnFor(h)}>
                          Txns
                        </button>
                        <button className="btn btn-sm" onClick={() => openEdit(h.holding_id)}>
                          Edit
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => delHolding(h.holding_id)}
                        >
                          Del
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {creating && (
        <HoldingForm
          profileId={selectedId!}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            reload();
          }}
        />
      )}
      {editing && (
        <HoldingForm
          profileId={selectedId!}
          holding={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
      {txnFor && (
        <TransactionsModal
          holding={txnFor}
          onClose={() => {
            setTxnFor(null);
            reload();
          }}
        />
      )}
    </>
  );
}

function HoldingForm({
  profileId,
  holding,
  onClose,
  onSaved,
}: {
  profileId: number;
  holding?: Holding;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!holding;
  const [assetClass, setAssetClass] = useState(holding?.asset_class ?? "MF");
  const [name, setName] = useState(holding?.name ?? "");
  const [identifier, setIdentifier] = useState(holding?.identifier ?? "");
  const [latestPrice, setLatestPrice] = useState<string>(
    holding?.latest_price != null ? String(holding.latest_price) : ""
  );
  const [currentValue, setCurrentValue] = useState<string>(
    holding?.current_value != null ? String(holding.current_value) : ""
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const unitPriced = UNIT_PRICED.includes(assetClass);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const body = {
      asset_class: assetClass,
      name,
      identifier,
      latest_price: latestPrice ? Number(latestPrice) : null,
      current_value: currentValue ? Number(currentValue) : null,
    };
    try {
      if (isEdit) {
        await api.put(`/api/holdings/${holding!.id}`, {
          name,
          identifier,
          latest_price: body.latest_price,
          current_value: body.current_value,
        });
      } else {
        await api.post(`/api/profiles/${profileId}/holdings`, body);
      }
      onSaved();
    } catch (err) {
      setError(apiError(err, "Could not save holding"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={isEdit ? "Edit Holding" : "Add Holding"} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="form-row">
          <div className="field">
            <label>Asset Class</label>
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value)}
              disabled={isEdit}
            >
              {ASSET_CLASSES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Identifier (a/c no, exchange, tier…)</label>
            <input value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label>Name / Script / Scheme</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="form-row">
          {unitPriced ? (
            <div className="field">
              <label>Latest Price / NAV</label>
              <input
                type="number"
                step="any"
                value={latestPrice}
                onChange={(e) => setLatestPrice(e.target.value)}
              />
            </div>
          ) : (
            <div className="field">
              <label>Current Value</label>
              <input
                type="number"
                step="any"
                value={currentValue}
                onChange={(e) => setCurrentValue(e.target.value)}
              />
            </div>
          )}
        </div>
        {error && <div className="error-msg">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

const emptyTxn = {
  txn_date: new Date().toISOString().slice(0, 10),
  txn_type: "buy",
  quantity: "",
  price: "",
  amount: "",
  charges: "",
  dividend: "",
  notes: "",
};

function TransactionsModal({
  holding,
  onClose,
}: {
  holding: HoldingMetric;
  onClose: () => void;
}) {
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [form, setForm] = useState<typeof emptyTxn>({ ...emptyTxn });
  const [editId, setEditId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const { data } = await api.get<Transaction[]>(
      `/api/holdings/${holding.holding_id}/transactions`
    );
    setTxns(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function set<K extends keyof typeof emptyTxn>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const body = {
      txn_date: form.txn_date,
      txn_type: form.txn_type,
      quantity: Number(form.quantity) || 0,
      price: Number(form.price) || 0,
      amount: Number(form.amount) || 0,
      charges: Number(form.charges) || 0,
      dividend: Number(form.dividend) || 0,
      notes: form.notes,
    };
    try {
      if (editId) {
        await api.put(`/api/transactions/${editId}`, body);
      } else {
        await api.post(`/api/holdings/${holding.holding_id}/transactions`, body);
      }
      setForm({ ...emptyTxn });
      setEditId(null);
      load();
    } catch (err) {
      setError(apiError(err, "Could not save transaction"));
    }
  }

  function edit(t: Transaction) {
    setEditId(t.id);
    setForm({
      txn_date: t.txn_date,
      txn_type: t.txn_type,
      quantity: String(t.quantity),
      price: String(t.price),
      amount: String(t.amount),
      charges: String(t.charges),
      dividend: String(t.dividend),
      notes: t.notes,
    });
  }

  async function del(id: number) {
    if (!confirm("Delete this transaction?")) return;
    await api.delete(`/api/transactions/${id}`);
    load();
  }

  return (
    <Modal title={`Transactions · ${holding.name}`} onClose={onClose}>
      <form onSubmit={save}>
        <div className="form-row">
          <div className="field">
            <label>Date</label>
            <input type="date" required value={form.txn_date} onChange={(e) => set("txn_date", e.target.value)} />
          </div>
          <div className="field">
            <label>Type</label>
            <select value={form.txn_type} onChange={(e) => set("txn_type", e.target.value)}>
              <option value="buy">Buy / Invest</option>
              <option value="sell">Sell / Redeem</option>
              <option value="dividend">Dividend</option>
              <option value="cashback">Cashback</option>
            </select>
          </div>
        </div>
        <div className="form-row">
          <div className="field">
            <label>Quantity / Units</label>
            <input type="number" step="any" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
          </div>
          <div className="field">
            <label>Price / NAV</label>
            <input type="number" step="any" value={form.price} onChange={(e) => set("price", e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="field">
            <label>Amount</label>
            <input type="number" step="any" required value={form.amount} onChange={(e) => set("amount", e.target.value)} />
          </div>
          <div className="field">
            <label>Charges</label>
            <input type="number" step="any" value={form.charges} onChange={(e) => set("charges", e.target.value)} />
          </div>
        </div>
        {error && <div className="error-msg">{error}</div>}
        <div className="modal-actions">
          {editId && (
            <button type="button" className="btn btn-ghost" onClick={() => { setEditId(null); setForm({ ...emptyTxn }); }}>
              Cancel edit
            </button>
          )}
          <button className="btn btn-primary btn-sm">{editId ? "Update" : "+ Add transaction"}</button>
        </div>
      </form>

      <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "1rem 0" }} />

      {loading ? (
        <div className="spinner" />
      ) : txns.length === 0 ? (
        <div className="empty">No transactions yet.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th className="num">Qty</th>
                <th className="num">Amount</th>
                <th>Src</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t) => (
                <tr key={t.id}>
                  <td>{t.txn_date}</td>
                  <td>{t.txn_type}</td>
                  <td className="num">{t.quantity ? num(t.quantity, 3) : "—"}</td>
                  <td className="num">{money(t.amount)}</td>
                  <td><small>{t.source}</small></td>
                  <td>
                    <div className="row-actions">
                      <button className="btn btn-sm" onClick={() => edit(t)}>Edit</button>
                      <button className="btn btn-sm btn-danger" onClick={() => del(t.id)}>Del</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}
