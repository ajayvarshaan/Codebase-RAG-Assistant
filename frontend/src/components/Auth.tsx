import { useState } from "react";
import ReactDOM from "react-dom";
import { login, signup } from "../api/auth";
import type { User } from "../api/auth";
import "./Auth.css";

interface AuthProps {
  onLogin: (user: User) => void;
}

export default function Auth({ onLogin }: AuthProps) {
  const [isSignup, setIsSignup] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isSignup) {
        await signup(username, email, password);
        const result = await login(email, password);
        onLogin(result.user);
      } else {
        const result = await login(email, password);
        onLogin(result.user);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleToggle() {
    setIsSignup(v => !v);
    setError("");
    setUsername("");
    setEmail("");
    setPassword("");
  }

  const content = (
    <div className="auth-shell">

      {/* Background layers */}
      <div className="auth-bg-grid" />
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />
      <div className="auth-blob auth-blob-3" />
      <div className="auth-particles" />
      <div className="auth-meteor" />

      {/* Centered card */}
      <div className={`auth-card${error ? " auth-card--error" : ""}`}>

        <div className="auth-card-border" />
        <div className="auth-card-glint auth-card-glint--tr" />
        <div className="auth-card-glint auth-card-glint--bl" />

        {/* Emblem */}
        <div className="auth-emblem">
          <div className="auth-emblem-ring auth-emblem-ring--1" />
          <div className="auth-emblem-ring auth-emblem-ring--2" />
          <div className="auth-emblem-ring auth-emblem-ring--3" />
          <div className="auth-emblem-core" />
          <div className="auth-emblem-sat auth-emblem-sat--1" />
          <div className="auth-emblem-sat auth-emblem-sat--2" />
        </div>

        <h1 className="auth-title">Codebase RAG Assistant</h1>
        <div className="auth-title-bar" />

        <p className="auth-subtitle">
          {isSignup ? "Create your account" : "Sign in to continue"}
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>

          {isSignup && (
            <div className="auth-field">
              <span className="auth-field-icon auth-field-icon--user" />
              <input
                className="auth-input"
                type="text"
                placeholder="Username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
              <div className="auth-field-glow" />
            </div>
          )}

          <div className="auth-field">
            <span className="auth-field-icon auth-field-icon--email" />
            <input
              className="auth-input"
              type="email"
              placeholder="Email address"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <div className="auth-field-glow" />
          </div>

          <div className="auth-field">
            <span className="auth-field-icon auth-field-icon--lock" />
            <input
              className="auth-input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete={isSignup ? "new-password" : "current-password"}
            />
            <div className="auth-field-glow" />
          </div>

          {error && (
            <div className="auth-error">
              <span className="auth-error-icon">⚠</span>
              {error}
            </div>
          )}

          <button className="auth-submit" type="submit" disabled={loading}>
            {loading && <span className="auth-spinner" />}
            {loading ? "Please wait…" : isSignup ? "Create Account" : "Sign In"}
            <span className="auth-submit-sheen" />
          </button>

        </form>

        <button className="auth-toggle" type="button" onClick={handleToggle}>
          <span className="auth-toggle-arrow">⇄</span>
          {isSignup ? "Already have an account? Sign in" : "No account yet? Sign up"}
          <span className="auth-toggle-line" />
        </button>

      </div>
    </div>
  );

  // Portal renders directly into document.body — completely outside #root
  // so no #root padding, margin, or flex layout can affect centering.
  return ReactDOM.createPortal(content, document.body);
}
