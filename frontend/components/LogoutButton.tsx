"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, initializeCsrf } from "@/lib/api";
import styles from "./Navbar.module.css";

export default function LogoutButton() {
  const router = useRouter();
  const [error, setError] = useState("");

  const handleLogout = async () => {
    setError("");
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await initializeCsrf(apiBase);
      const response = await apiFetch(`${apiBase}/api/auth/logout/`, { method: "POST" });
      if (!response.ok) throw new Error(`Logout failed (${response.status}).`);
      router.refresh();
    } catch {
      setError("Could not log out. Please try again.");
    }
  };

  return (
    <>
      <button onClick={handleLogout} className={styles.loginBtn}>Log Out</button>
      {error && <span role="alert">{error}</span>}
    </>
  );
}
