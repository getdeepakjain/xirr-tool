import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import api from "./api";
import type { Profile } from "./types";

interface ProfileState {
  profiles: Profile[];
  selectedId: number | null;
  selected: Profile | null;
  loading: boolean;
  select: (id: number) => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<ProfileState>(null as unknown as ProfileState);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const { data } = await api.get<Profile[]>("/api/profiles");
    setProfiles(data);
    setSelectedId((cur) => {
      const stored = Number(localStorage.getItem("profileId"));
      if (cur && data.some((p) => p.id === cur)) return cur;
      if (stored && data.some((p) => p.id === stored)) return stored;
      return data[0]?.id ?? null;
    });
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  function select(id: number) {
    setSelectedId(id);
    localStorage.setItem("profileId", String(id));
  }

  const selected = profiles.find((p) => p.id === selectedId) ?? null;

  return (
    <Ctx.Provider value={{ profiles, selectedId, selected, loading, select, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useProfiles() {
  return useContext(Ctx);
}
