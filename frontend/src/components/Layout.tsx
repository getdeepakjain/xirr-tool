import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { useProfiles } from "../profileStore";

const NAV = [
  { to: "/", label: "Dashboard", icon: "📊", end: true },
  { to: "/holdings", label: "Holdings", icon: "💼" },
  { to: "/upload", label: "Upload Excel", icon: "⬆️" },
  { to: "/insights", label: "Insights", icon: "💡" },
  { to: "/profiles", label: "Profiles", icon: "👤" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { profiles, selectedId, select } = useProfiles();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          Portfolio<span>XIRR</span>
        </div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
            <span>{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
        <div className="sidebar-footer">
          <div className="user-info" style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            {user?.name || user?.email}
            <br />
            <small>{user?.email}</small>
          </div>
          <button className="btn btn-block btn-sm" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="profile-select">
            <label style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Profile</label>
            <select
              value={selectedId ?? ""}
              onChange={(e) => select(Number(e.target.value))}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
