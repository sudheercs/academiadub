"use client";

import { useCallback, useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import styles from "./classes.module.css";

interface Classroom {
  id: string;
  name: string;
  join_code: string;
  is_active: boolean;
  instructor?: { id: string; email: string };
}

export default function ClassesPage() {
  const [classes, setClasses] = useState<Classroom[]>([]);
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchClasses = useCallback(async () => {
    try {
      const res = await apiFetch(`${apiBase}/api/classes/classrooms/`, {});
      const data = await res.json();
      if (res.ok) {
        setClasses(data.results || data);
      } else {
        setError(data.error || "Failed to load classes.");
      }
    } catch {
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchClasses();
  }, [fetchClasses]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinCode.trim()) return;

    try {
      const res = await apiFetch(`${apiBase}/api/classes/join/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ join_code: joinCode }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.detail || "Joined successfully!");
        setJoinCode("");
        fetchClasses(); // refresh list
      } else {
        alert(data.error || "Failed to join.");
      }
    } catch {
      alert("Network error.");
    }
  };

  if (loading) return <div className={styles.loading}>Loading...</div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>My Classes</h1>
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.joinSection}>
        <h3>Join a Class</h3>
        <form onSubmit={handleJoin} className={styles.joinForm}>
          <input
            type="text"
            placeholder="Enter Class Code (e.g., CS101)"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            className={styles.joinInput}
          />
          <button type="submit" className={styles.joinBtn}>
            Join
          </button>
        </form>
      </div>

      <div className={styles.classesGrid}>
        {classes.length === 0 ? (
          <p>You are not enrolled in any classes yet.</p>
        ) : (
          classes.map((cls) => (
            <Link key={cls.id} href={`/classes/${cls.id}`} className={styles.classCard}>
              <h2>{cls.name}</h2>
              <p>Code: <strong>{cls.join_code}</strong></p>
              {cls.instructor && <p>Instructor: {cls.instructor.email}</p>}
              <span className={cls.is_active ? styles.activeBadge : styles.inactiveBadge}>
                {cls.is_active ? "Active" : "Inactive"}
              </span>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
