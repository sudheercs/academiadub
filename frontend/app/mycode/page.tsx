"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import styles from "./mycode.module.css";
import { apiFetch } from "@/lib/api";

/* ── Types ───────────────────────────────────────────────────────────────── */
interface CodeFolder {
  id: string;
  name: string;
  snippet_count: number;
  created_at: string;
}

interface CodeSnippet {
  id: string;
  title: string;
  language: string;
  folder: string | null;
  folder_name: string | null;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

interface CodeFile extends CodeSnippet {
  filename: string;
}

interface StorageInfo {
  used_bytes: number;
  total_bytes: number;
  used_mb: number;
  total_mb: number;
  used_pct: number;
}

const LANG_ICONS: Record<string, string> = {
  python: "🐍",
  javascript: "🟨",
  typescript: "🔷",
  bash: "💲",
  text: "📄",
};

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/* ── Page ────────────────────────────────────────────────────────────────── */
export default function MyCodePage() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [token,        setToken]        = useState(false);
  const [folders,      setFolders]      = useState<CodeFolder[]>([]);
  const [snippets,     setSnippets]     = useState<CodeSnippet[]>([]);
  const [files,        setFiles]        = useState<CodeFile[]>([]);
  const [storage,      setStorage]      = useState<StorageInfo | null>(null);
  const [activeFolderId, setActiveFolderId] = useState<string | "none" | "all">("all");

  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState<string | null>(null);

  // New folder dialog
  const [newFolderName, setNewFolderName] = useState("");
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [folderError,  setFolderError]  = useState<string | null>(null);

  // Rename/delete snippet/file
  const [deletingId,   setDeletingId]   = useState<string | null>(null);

  useEffect(() => {
    apiFetch(`${apiBase}/api/auth/me/`)
      .then((response) => setToken(response.ok))
      .catch(() => setToken(false));
  }, [apiBase]);

  const authHeaders = useCallback((): Record<string, string> => ({
    "Content-Type": "application/json",
  }), []);

  const loadAll = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const [fRes, sRes, fileRes, stRes] = await Promise.all([
        apiFetch(`${apiBase}/api/codelab/folders/`,          { headers: authHeaders() }),
        apiFetch(`${apiBase}/api/codelab/snippets/`,         { headers: authHeaders() }),
        apiFetch(`${apiBase}/api/codelab/files/`,            { headers: authHeaders() }),
        apiFetch(`${apiBase}/api/codelab/snippets/storage/`, { headers: authHeaders() }),
      ]);
      if (fRes.ok)  setFolders((await fRes.json()).results  || await fRes.json());
      if (sRes.ok)  setSnippets((await sRes.json()).results || await sRes.json());
      if (fileRes.ok) setFiles((await fileRes.json()).results || await fileRes.json());
      if (stRes.ok) setStorage(await stRes.json());
    } catch {
      setError("Failed to load your code library.");
    } finally {
      setLoading(false);
    }
  }, [token, apiBase, authHeaders]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Load snippets for active folder
  const loadSnippets = useCallback(async (folderId: string | "none" | "all") => {
    if (!token) return;
    let sUrl = `${apiBase}/api/codelab/snippets/`;
    let fUrl = `${apiBase}/api/codelab/files/`;
    if (folderId === "none") {
        sUrl += "?folder=none";
        fUrl += "?folder=none";
    }
    else if (folderId !== "all") {
        sUrl += `?folder=${folderId}`;
        fUrl += `?folder=${folderId}`;
    }
    const [sRes, fRes] = await Promise.all([
        apiFetch(sUrl, { headers: authHeaders() }),
        apiFetch(fUrl, { headers: authHeaders() })
    ]);
    if (sRes.ok) {
      const d = await sRes.json();
      setSnippets(d.results || d);
    }
    if (fRes.ok) {
      const d = await fRes.json();
      setFiles(d.results || d);
    }
  }, [token, apiBase, authHeaders]);

  const handleSelectFolder = (id: string | "none" | "all") => {
    setActiveFolderId(id);
    loadSnippets(id);
  };

  // Create folder
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    setCreatingFolder(true);
    setFolderError(null);
    try {
      const res = await apiFetch(`${apiBase}/api/codelab/folders/`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ name: newFolderName.trim() }),
      });
      const data = await res.json();
      if (res.ok) {
        setFolders((prev) => [...prev, data]);
        setNewFolderName("");
        setShowNewFolder(false);
      } else {
        setFolderError(data.name?.[0] || data.detail || "Failed to create folder.");
      }
    } finally {
      setCreatingFolder(false);
    }
  };

  // Delete folder
  const handleDeleteFolder = async (id: string) => {
    if (!confirm("Delete this folder? Snippets inside will become unfiled.")) return;
    await apiFetch(`${apiBase}/api/codelab/folders/${id}/`, {
      method: "DELETE", headers: authHeaders(),
    });
    setFolders((prev) => prev.filter((f) => f.id !== id));
    if (activeFolderId === id) handleSelectFolder("all");
    else loadSnippets(activeFolderId);
  };

  // Delete snippet
  const handleDeleteSnippet = async (id: string) => {
    if (!confirm("Delete this snippet permanently?")) return;
    setDeletingId(id);
    await apiFetch(`${apiBase}/api/codelab/snippets/${id}/`, {
      method: "DELETE", headers: authHeaders(),
    });
    setSnippets((prev) => prev.filter((s) => s.id !== id));
    // Refresh storage info
    const stRes = await apiFetch(`${apiBase}/api/codelab/snippets/storage/`, { headers: authHeaders() });
    if (stRes.ok) setStorage(await stRes.json());
    setDeletingId(null);
  };

  // Delete file
  const handleDeleteFile = async (id: string) => {
    if (!confirm("Delete this file permanently?")) return;
    setDeletingId(id);
    await apiFetch(`${apiBase}/api/codelab/files/${id}/`, {
      method: "DELETE", headers: authHeaders(),
    });
    setFiles((prev) => prev.filter((s) => s.id !== id));
    // Refresh storage info
    const stRes = await apiFetch(`${apiBase}/api/codelab/snippets/storage/`, { headers: authHeaders() });
    if (stRes.ok) setStorage(await stRes.json());
    setDeletingId(null);
  };

  // Download file
  const handleDownloadFile = async (id: string, filename: string) => {
    try {
        const res = await apiFetch(`${apiBase}/api/codelab/files/${id}/`, { headers: authHeaders() });
        const data = await res.json();
        if (res.ok && data.content_b64) {
            const link = document.createElement("a");
            link.href = `data:${data.mime_type || "application/octet-stream"};base64,${data.content_b64}`;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            alert("Failed to download file.");
        }
    } catch {
        alert("Failed to download file.");
    }
  };

  /* ── Render ─────────────────────────────────────────────────────────────── */
  if (!token) {
    return (
      <div className={styles.guestBox}>
        <span className={styles.guestIcon}>🔒</span>
        <h2>My Code — Personal Storage</h2>
        <p>Log in to save and organise your code snippets.</p>
        <Link href="/login" className={styles.loginBtn}>Log In</Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <p>Loading your code library…</p>
      </div>
    );
  }

  if (error) return <div className={styles.errorPage}>{error}</div>;

  const storageUsedPct = storage?.used_pct ?? 0;
  const storageColor   = storageUsedPct > 85 ? "#f87171" : storageUsedPct > 60 ? "#fb923c" : "#4ade80";

  return (
    <div className={styles.page}>
      {/* ── Top bar ── */}
      <div className={styles.topBar}>
        <div>
          <h1 className={styles.pageTitle}>📁 My Code</h1>
          <p className={styles.pageSubtitle}>Personal code library · up to 100 MB</p>
        </div>
        <Link href="/codelab" className={styles.newSnippetBtn}>
          ⚡ Open Code Lab
        </Link>
      </div>

      {/* ── Storage meter ── */}
      {storage && (
        <div className={styles.storageMeter}>
          <div className={styles.storageLabel}>
            <span>Storage</span>
            <span style={{ color: storageColor }}>
              {storage.used_mb} MB / {storage.total_mb} MB ({storage.used_pct}%)
            </span>
          </div>
          <div className={styles.storageBar}>
            <div
              className={styles.storageBarFill}
              style={{ width: `${storageUsedPct}%`, background: storageColor }}
            />
          </div>
        </div>
      )}

      {/* ── Layout ── */}
      <div className={styles.layout}>
        {/* ── Sidebar ── */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <span className={styles.sidebarTitle}>Folders</span>
            <button
              className={styles.newFolderBtn}
              onClick={() => setShowNewFolder((v) => !v)}
              title="New folder"
            >+</button>
          </div>

          {showNewFolder && (
            <div className={styles.newFolderForm}>
              <input
                className={styles.newFolderInput}
                placeholder="Folder name"
                value={newFolderName}
                autoFocus
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
              />
              {folderError && <p className={styles.folderError}>{folderError}</p>}
              <div className={styles.newFolderActions}>
                <button
                  className={styles.createBtn}
                  onClick={handleCreateFolder}
                  disabled={creatingFolder}
                >{creatingFolder ? "Creating…" : "Create"}</button>
                <button className={styles.cancelBtn} onClick={() => { setShowNewFolder(false); setNewFolderName(""); }}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          <ul className={styles.folderList}>
            <li
              className={`${styles.folderItem} ${activeFolderId === "all" ? styles.folderActive : ""}`}
              onClick={() => handleSelectFolder("all")}
            >
              <span>📂 All Files</span>
              <span className={styles.folderCount}>{snippets.length}</span>
            </li>
            <li
              className={`${styles.folderItem} ${activeFolderId === "none" ? styles.folderActive : ""}`}
              onClick={() => handleSelectFolder("none")}
            >
              <span>📄 Unfiled</span>
            </li>
            {folders.map((f) => (
              <li
                key={f.id}
                className={`${styles.folderItem} ${activeFolderId === f.id ? styles.folderActive : ""}`}
                onClick={() => handleSelectFolder(f.id)}
              >
                <span>📁 {f.name}</span>
                <span className={styles.folderMeta}>
                  <span className={styles.folderCount}>{f.snippet_count}</span>
                  <button
                    className={styles.deleteFolderBtn}
                    onClick={(e) => { e.stopPropagation(); handleDeleteFolder(f.id); }}
                    title="Delete folder"
                  >✕</button>
                </span>
              </li>
            ))}
          </ul>
        </aside>

        {/* ── Main content ── */}
        <main className={styles.main}>
          {snippets.length === 0 && files.length === 0 ? (
            <div className={styles.emptyState}>
              <span className={styles.emptyIcon}>💡</span>
              <h3>No snippets or files here yet</h3>
              <p>Open Code Lab, write some code, and click <strong>💾 Save</strong> to store it here.</p>
              <Link href="/codelab" className={styles.newSnippetBtn}>Go to Code Lab</Link>
            </div>
          ) : (
            <div className={styles.snippetGrid}>
              {snippets.map((s) => (
                <div key={s.id} className={styles.snippetCard}>
                  <div className={styles.snippetHeader}>
                    <span className={styles.langIcon}>{LANG_ICONS[s.language] || "📄"}</span>
                    <h3 className={styles.snippetTitle}>{s.title}</h3>
                  </div>
                  <div className={styles.snippetMeta}>
                    {s.folder_name && (
                      <span className={styles.folderTag}>📁 {s.folder_name}</span>
                    )}
                    <span className={styles.snippetSize}>{fmtSize(s.size_bytes)}</span>
                    <span className={styles.snippetDate}>
                      {new Date(s.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className={styles.snippetActions}>
                    <Link
                      href={`/codelab?lang=${s.language}`}
                      className={styles.openBtn}
                      title="Open in Code Lab"
                    >
                      ⚡ Open
                    </Link>
                    <button
                      className={styles.deleteSnippetBtn}
                      onClick={() => handleDeleteSnippet(s.id)}
                      disabled={deletingId === s.id}
                    >
                      {deletingId === s.id ? "…" : "🗑"}
                    </button>
                  </div>
                </div>
              ))}
              {/* Files */}
              {files.map((f: CodeFile) => (
                <div key={f.id} className={styles.snippetCard}>
                  <div className={styles.snippetHeader}>
                    <span className={styles.langIcon}>📄</span>
                    <h3 className={styles.snippetTitle}>{f.filename}</h3>
                  </div>
                  <div className={styles.snippetMeta}>
                    {f.folder_name && (
                      <span className={styles.folderTag}>📁 {f.folder_name}</span>
                    )}
                    <span className={styles.snippetSize}>{fmtSize(f.size_bytes)}</span>
                    <span className={styles.snippetDate}>
                      {new Date(f.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className={styles.snippetActions}>
                    <button
                      className={styles.openBtn}
                      onClick={() => handleDownloadFile(f.id, f.filename)}
                      title="Download file"
                    >
                      📥 Download
                    </button>
                    <button
                      className={styles.deleteSnippetBtn}
                      onClick={() => handleDeleteFile(f.id)}
                      disabled={deletingId === f.id}
                    >
                      {deletingId === f.id ? "…" : "🗑"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
