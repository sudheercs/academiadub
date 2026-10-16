"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import styles from "./classes.module.css";

export default function JoinForm() {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;

    setLoading(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const res = await apiFetch(`${apiBase}/api/classes/join/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ join_code: code }),
      });

      if (res.ok) {
        const data = await res.json();
        alert(data.detail || "Joined successfully!");
        router.refresh();
      } else {
        const errData = await res.json();
        alert(errData.error || "Failed to join class.");
      }
    } catch {
      alert("An error occurred while joining the class.");
    } finally {
      setLoading(false);
      setCode("");
    }
  };

  return (
    <form className={styles.joinForm} onSubmit={handleJoin}>
      <input
        type="text"
        placeholder="Enter join code…"
        className={styles.joinInput}
        maxLength={10}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        disabled={loading}
      />
      <button type="submit" className={styles.joinBtn} disabled={loading}>
        {loading ? "Joining..." : "Join Class"}
      </button>
    </form>
  );
}
