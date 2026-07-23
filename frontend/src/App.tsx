import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { ProfileProvider } from "./profileStore";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import Holdings from "./pages/Holdings";
import Upload from "./pages/Upload";
import Insights from "./pages/Insights";
import Profiles from "./pages/Profiles";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="center-screen">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/auth/callback" element={<AuthCallback />} />
      {!user ? (
        <>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </>
      ) : (
        <Route
          element={
            <ProfileProvider>
              <Layout />
            </ProfileProvider>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/holdings" element={<Holdings />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/profiles" element={<Profiles />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  );
}
