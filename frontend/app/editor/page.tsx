"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import styles from "./editor.module.css";

interface Topic {
  id: string;
  title: string;
  slug: string;
}

interface Block {
  type: string;
  content?: string;
  language?: string;
  url?: string;
  caption?: string;
}

export default function EditorPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [versionState, setVersionState] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    // Fetch topics for the editor
    apiFetch(`${apiBase}/api/catalogue/topics/`)
      .then((r) => r.json())
      .then((data) => setTopics(data.results || data))
      .catch(() => setError("Failed to load topics."));
  }, [apiBase]);

  const loadTopicVersions = async (topicId: string) => {
    setSelectedTopic(topicId);
    setVersionId(null);
    setVersionState(null);
    setError(null);

    try {
      const res = await apiFetch(`${apiBase}/api/catalogue/topics/${topicId}/versions/`);
      if (!res.ok) throw new Error("Could not load topic versions.");
      const data = await res.json();
      const versions = data.results || data;
      if (versions.length > 0) {
        setVersionId(versions[0].id);
        setVersionState(versions[0].state);
        setBlocks(versions[0].blocks || []);
      } else {
        setBlocks([]);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Failed to load topic versions.");
    }
  };

  const handleSave = async () => {
    if (!selectedTopic) return;
    setSaving(true);

    try {
      const res = await apiFetch(`${apiBase}/api/catalogue/topics/${selectedTopic}/versions/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          blocks: blocks,
        }),
      });

      if (res.ok) {
        const version = await res.json();
        setVersionId(version.id);
        setVersionState(version.state);
        setError(null);
      } else {
        const err = await res.json();
        setError(`Error saving: ${JSON.stringify(err)}`);
      }
    } catch {
      setError("Network error while saving draft.");
    } finally {
      setSaving(false);
    }
  };

  const transitionVersion = async (
    transition: "submit" | "review" | "publish" | "unpublish",
    approved?: boolean,
  ) => {
    if (!selectedTopic || !versionId) return;
    const body = transition === "review" ? { approved, review_note: "" } : {};
    try {
      const response = await apiFetch(
        `${apiBase}/api/catalogue/topics/${selectedTopic}/versions/${versionId}/${transition}/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || JSON.stringify(data));
      setVersionState(data.state);
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not transition version.");
    }
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>CMS Editor</h1>
      {error && <div className={styles.error}>{error}</div>}
      
      <div className={styles.layout}>
        <div className={styles.sidebar}>
          <h3>Topics</h3>
          <ul className={styles.topicList}>
            {topics.map((t) => (
              <li
                key={t.id}
                className={selectedTopic === t.id ? styles.active : ""}
                onClick={() => loadTopicVersions(t.id)}
              >
                {t.title}
              </li>
            ))}
          </ul>
        </div>
        
        <div className={styles.editorMain}>
          {selectedTopic ? (
            <>
              <div className={styles.editorToolbar}>
                <h3>Edit Blocks</h3>
                <div>
                  {(!versionState || versionState === "draft") && (
                    <button onClick={handleSave} disabled={saving} className={styles.saveBtn}>
                      {saving ? "Saving..." : "Save Draft"}
                    </button>
                  )}
                  {versionId && versionState === "draft" && (
                    <button onClick={() => transitionVersion("submit")}>Submit for review</button>
                  )}
                  {versionId && versionState === "in_review" && (
                    <>
                      <button onClick={() => transitionVersion("review", true)}>Approve</button>
                      <button onClick={() => transitionVersion("review", false)}>Return for edits</button>
                    </>
                  )}
                  {versionId && versionState === "approved" && (
                    <button onClick={() => transitionVersion("publish")}>Publish</button>
                  )}
                  {versionId && versionState === "published" && (
                    <button onClick={() => transitionVersion("unpublish")}>Unpublish</button>
                  )}
                  {versionState && <span> State: {versionState}</span>}
                </div>
              </div>
              <textarea
                className={styles.textarea}
                value={JSON.stringify(blocks, null, 2)}
                onChange={(e) => {
                  try {
                    setBlocks(JSON.parse(e.target.value));
                  } catch {
                    // Ignore JSON parse errors while typing
                  }
                }}
              />
              <p className={styles.help}>Edit the raw JSON blocks here.</p>
            </>
          ) : (
            <p>Select a topic from the sidebar to edit.</p>
          )}
        </div>
      </div>
    </div>
  );
}
