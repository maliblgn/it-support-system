import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiError, api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await api.me();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.me()
      .then((currentUser) => { if (active) setUser(currentUser); })
      .catch((error) => {
        if (active && error instanceof ApiError && error.status === 401) setUser(null);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const login = useCallback(async (payload) => {
    const currentUser = await api.login(payload);
    setUser(currentUser);
    return currentUser;
  }, []);

  const register = useCallback(async (payload) => {
    const currentUser = await api.register(payload);
    setUser(currentUser);
    return currentUser;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook ve sağlayıcının aynı modülde tutulması tüketici importlarını sadeleştirir.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth yalnızca AuthProvider içinde kullanılabilir.");
  return value;
}
