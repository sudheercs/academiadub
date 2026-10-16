"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch, initializeCsrf } from "@/lib/api";
import styles from "./login.module.css";

export default function LoginPage() {
  const [loginMethod, setLoginMethod] = useState<"email" | "code">("email");

  // Email state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Code state
  const [classCode, setClassCode] = useState("");
  const [studentSecret, setStudentSecret] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      let url = "";
      let body = {};
      
      if (loginMethod === "email") {
        url = `${apiBase}/api/auth/login/`;
        body = { email, password };
      } else {
        url = `${apiBase}/api/classes/login-with-code/`;
        body = { class_code: classCode, student_secret: studentSecret };
      }

      await initializeCsrf(apiBase);
      const res = await apiFetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || data.error || "Invalid login credentials.");
        return;
      }

      // Tokens are set by the backend as HttpOnly cookies. The browser keeps them
      // without exposing them to JavaScript, which matches the secure auth model.
      window.location.href = "/";
    } catch {
      setError("Could not connect to server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={`${styles.card} glass`}>
        <div className={styles.header}>
          <h2>Welcome Back</h2>
          <p>Sign in to continue your learning journey.</p>
        </div>

        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${loginMethod === "email" ? styles.activeTab : ""}`}
            onClick={() => setLoginMethod("email")}
          >
            Email Login
          </button>
          <button
            className={`${styles.tab} ${loginMethod === "code" ? styles.activeTab : ""}`}
            onClick={() => setLoginMethod("code")}
          >
            Class Code Login
          </button>
        </div>

        <form className={styles.form} onSubmit={handleLogin}>
          {error && <p className={styles.errorMsg}>{error}</p>}

          {loginMethod === "email" ? (
            <>
              <div className={styles.inputGroup}>
                <label htmlFor="email">Email address</label>
                <input
                  type="email"
                  id="email"
                  placeholder="student@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className={styles.inputGroup}>
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </>
          ) : (
            <>
              <div className={styles.inputGroup}>
                <label htmlFor="classCode">Class Code</label>
                <input
                  type="text"
                  id="classCode"
                  placeholder="e.g. B6PRHG7K"
                  value={classCode}
                  onChange={(e) => setClassCode(e.target.value)}
                  required
                />
              </div>

              <div className={styles.inputGroup}>
                <label htmlFor="studentSecret">Secret PIN</label>
                <input
                  type="password"
                  id="studentSecret"
                  placeholder="e.g. 180934"
                  value={studentSecret}
                  onChange={(e) => setStudentSecret(e.target.value)}
                  required
                />
              </div>
            </>
          )}

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? "Signing in..." : "Log In"}
          </button>
        </form>

        <p className={styles.footer}>
          Don&apos;t have an account? <Link href="/register">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
