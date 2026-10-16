"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import styles from "./SearchBar.module.css";

interface SearchResult {
  id: number;
  type: string;
  title: string;
  url: string;
}

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.trim().length < 2) {
        setResults([]);
        setIsOpen(false);
        return;
      }

      setLoading(true);
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiBase}/api/catalogue/search/?q=${encodeURIComponent(query)}`);
        if (res.ok) {
          const data = await res.json();
          setResults(data.results);
          setIsOpen(true);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className={styles.container} ref={containerRef}>
      <input
        type="text"
        className={styles.input}
        placeholder="Search..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => query.trim().length >= 2 && setIsOpen(true)}
      />
      {isOpen && (
        <div className={styles.dropdown}>
          {loading ? (
            <div className={styles.empty}>Searching...</div>
          ) : results.length > 0 ? (
            <ul className={styles.list}>
              {results.map((result, idx) => (
                <li key={`${result.type}-${result.id}-${idx}`}>
                  <Link href={result.url} className={styles.resultItem} onClick={() => setIsOpen(false)}>
                    <span className={styles.typeLabel}>{result.type}</span>
                    <span className={styles.title}>{result.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.empty}>No results found.</div>
          )}
        </div>
      )}
    </div>
  );
}
