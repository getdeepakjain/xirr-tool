import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import api from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  setToken: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>(null as unknown as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadUser() {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get<User>("/api/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem("token");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUser();
  }, []);

  async function setToken(token: string) {
    localStorage.setItem("token", token);
    setLoading(true);
    await loadUser();
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
    location.href = "/login";
  }

  return (
    <AuthContext.Provider value={{ user, loading, setToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
