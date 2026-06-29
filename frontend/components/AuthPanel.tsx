"use client";

import { FormEvent, useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { AuthTokens } from "@/lib/types";

export function AuthPanel({ onToken }: { onToken: (tokens: AuthTokens) => void }) {
  const [mode, setMode] = useState<"login" | "register" | "reset">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("reset_token");
    if (token) {
      setResetToken(token);
      setMode("reset");
      setInfo("Enter a new password to finish resetting your account.");
    }
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      if (mode === "reset") {
        if (resetToken.trim()) {
          await api.confirmPasswordReset(resetToken.trim(), password);
          setInfo("Password updated. You can sign in with the new password.");
          setPassword("");
          setResetToken("");
          setMode("login");
          return;
        }

        const response = await api.requestPasswordReset(email);
        if (response.reset_token) {
          setResetToken(response.reset_token);
          setInfo("Reset token generated for local development. Enter a new password and submit again.");
        } else {
          setInfo(response.message);
        }
        return;
      }

      const response =
        mode === "login" ? await api.login(email, password) : await api.register(fullName, email, password);
      localStorage.setItem("docintel_token", response.access_token);
      localStorage.setItem("docintel_refresh_token", response.refresh_token);
      onToken(response);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth panel stack">
      <div className="brand">
        <FileText size={28} />
        <span>DocIntel</span>
      </div>
      <div className="tabs">
        <button className={`tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>Sign in</button>
        <button className={`tab ${mode === "register" ? "active" : ""}`} onClick={() => setMode("register")}>Create account</button>
        <button className={`tab ${mode === "reset" ? "active" : ""}`} onClick={() => setMode("reset")}>Reset</button>
      </div>
      <form className="stack" onSubmit={submit}>
        {mode === "register" && (
          <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Full name" required />
        )}
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" type="email" required />
        {mode === "reset" && (
          <input value={resetToken} onChange={(event) => setResetToken(event.target.value)} placeholder="Reset token" />
        )}
        <input
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder={mode === "reset" ? "New password" : "Password"}
          type="password"
          minLength={8}
          required={mode !== "reset" || Boolean(resetToken.trim())}
        />
        {info && <div className="message">{info}</div>}
        {error && <div className="message error">{error}</div>}
        <button disabled={loading}>
          {loading ? "Working..." : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : resetToken.trim() ? "Set new password" : "Request reset"}
        </button>
      </form>
    </main>
  );
}
