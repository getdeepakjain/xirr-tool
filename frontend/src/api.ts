import axios from "axios";

// Absolute base URL of the backend API.
// - Local dev: leave VITE_BACKEND_URL unset -> "" -> requests are same-origin
//   and handled by the Vite dev proxy (see vite.config.ts).
// - Production (e.g. frontend on Vercel, backend on Render/Railway/Fly): set
//   VITE_BACKEND_URL to the deployed backend origin; calls go there directly
//   (CORS is allowed via the backend's FRONTEND_ORIGINS setting).
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

const api = axios.create({ baseURL: BACKEND_URL || "/" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && !location.pathname.startsWith("/login")) {
      localStorage.removeItem("token");
      location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export function apiError(err: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(err)) {
    // No response at all -> network failure or CORS block (browser hid the body).
    if (!err.response) {
      return "Cannot reach the backend. Check that VITE_BACKEND_URL points to your API and that the backend's FRONTEND_ORIGINS allows this site.";
    }
    const { status, data } = err.response;
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg || String(d)).join(", ");
    // Got a response but not the JSON we expected (e.g. HTML from a misrouted
    // request when VITE_BACKEND_URL is unset and the SPA rewrite answered).
    if (typeof data === "string" || status === 404 || status === 405) {
      return `Unexpected response (HTTP ${status}) from the API URL. Verify VITE_BACKEND_URL is set to the backend origin and redeploy.`;
    }
  }
  return fallback;
}

export default api;
