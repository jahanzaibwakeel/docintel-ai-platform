"use client";

import { useEffect, useState } from "react";
import { AuthPanel } from "@/components/AuthPanel";
import { Dashboard } from "@/components/Dashboard";
import { api } from "@/lib/api";
import type { AuthTokens } from "@/lib/types";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem("docintel_token");
    const refreshToken = localStorage.getItem("docintel_refresh_token");
    if (storedToken) {
      setToken(storedToken);
    } else if (refreshToken) {
      api.refresh(refreshToken)
        .then((tokens) => {
          localStorage.setItem("docintel_token", tokens.access_token);
          localStorage.setItem("docintel_refresh_token", tokens.refresh_token);
          setToken(tokens.access_token);
        })
        .catch(() => {
          localStorage.removeItem("docintel_refresh_token");
        });
    }
  }, []);

  async function logout() {
    const refreshToken = localStorage.getItem("docintel_refresh_token");
    if (token) {
      await api.logout(token, refreshToken).catch(() => undefined);
    }
    localStorage.removeItem("docintel_token");
    localStorage.removeItem("docintel_refresh_token");
    setToken(null);
  }

  function storeTokens(tokens: AuthTokens) {
    localStorage.setItem("docintel_token", tokens.access_token);
    localStorage.setItem("docintel_refresh_token", tokens.refresh_token);
    setToken(tokens.access_token);
  }

  if (!token) {
    return <AuthPanel onToken={storeTokens} />;
  }

  return <Dashboard token={token} onLogout={logout} />;
}
