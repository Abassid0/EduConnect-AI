import { createContext, useContext, useEffect, useState } from "react";
import { auth } from "../api/client";

const AuthContext = createContext(null);

const ROLE_HIERARCHY = {
  super_admin: 5,
  admin: 4,
  support_agent: 3,
  finance: 2,
  academic: 1,
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      auth
        .me()
        .then((res) => {
          if (res.data && typeof res.data === "object" && res.data.id) {
            setUser(res.data);
          } else {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
          }
        })
        .catch(() => {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const { data } = await auth.login(email, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    const me = await auth.me();
    setUser(me.data);
    return me.data;
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  const hasRole = (...roles) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const hasMinRole = (minRole) => {
    if (!user) return false;
    return (ROLE_HIERARCHY[user.role] || 0) >= (ROLE_HIERARCHY[minRole] || 0);
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, hasRole, hasMinRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
