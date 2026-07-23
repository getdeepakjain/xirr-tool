import { useState } from "react";
import api, { apiError } from "../api";
import Modal from "../components/Modal";
import { useProfiles } from "../profileStore";
import type { Profile } from "../types";

export default function Profiles() {
  const { profiles, refresh, select, selectedId } = useProfiles();
  const [editing, setEditing] = useState<Profile | null>(null);
  const [creating, setCreating] = useState(false);

  async function del(p: Profile) {
    if (profiles.length <= 1) {
      alert("You need at least one profile.");
      return;
    }
    if (!confirm(`Delete profile "${p.name}" and all its holdings?`)) return;
    await api.delete(`/api/profiles/${p.id}`);
    await refresh();
  }

  return (
    <>
      <div className="panel-head">
        <h1>Profiles</h1>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          + Add Profile
        </button>
      </div>

      <div className="grid cards">
        {profiles.map((p) => (
          <div key={p.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0 }}>{p.name}</h3>
              {p.id === selectedId && <span className="badge">active</span>}
            </div>
            <p style={{ color: "var(--muted)", fontSize: "0.88rem", minHeight: "1.2rem" }}>
              {p.description || "—"}
            </p>
            <div className="row-actions" style={{ marginTop: "0.5rem" }}>
              <button className="btn btn-sm" onClick={() => select(p.id)}>
                Select
              </button>
              <button className="btn btn-sm" onClick={() => setEditing(p)}>
                Edit
              </button>
              <button className="btn btn-sm btn-danger" onClick={() => del(p)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {creating && (
        <ProfileForm
          onClose={() => setCreating(false)}
          onSaved={async () => {
            setCreating(false);
            await refresh();
          }}
        />
      )}
      {editing && (
        <ProfileForm
          profile={editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await refresh();
          }}
        />
      )}
    </>
  );
}

function ProfileForm({
  profile,
  onClose,
  onSaved,
}: {
  profile?: Profile;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(profile?.name ?? "");
  const [description, setDescription] = useState(profile?.description ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (profile) {
        await api.put(`/api/profiles/${profile.id}`, { name, description });
      } else {
        await api.post(`/api/profiles`, { name, description });
      }
      onSaved();
    } catch (err) {
      setError(apiError(err, "Could not save profile"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={profile ? "Edit Profile" : "Add Profile"} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label>Name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label>Description</label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
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
