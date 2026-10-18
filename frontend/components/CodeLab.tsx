"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import styles from "./CodeLab.module.css";

interface BrowserRunData {
  stdout: string;
  stderr: string;
  exit_code: number;
  output_files: Record<string, string>;
}

interface WorkerMessage {
  type: "ready" | "result" | "error";
  data?: BrowserRunData;
  error?: string;
}

interface CodeLabProps {
  initialCode: string;
  language: string;
  isAuthenticated?: boolean;
}

interface CodeFolder { id: string; name: string; }
interface SaveState { title: string; folderId: string | null; }

function runInBrowser(
  language: string,
  code: string,
  inputFiles: Record<string, string>,
  onReady: () => void,
  onWorkerChange: (worker: Worker | null) => void,
): Promise<BrowserRunData> {
  return new Promise((resolve, reject) => {
    const worker = new Worker("/workers/codelab.worker.js");
    onWorkerChange(worker);
    let executionTimer: ReturnType<typeof setTimeout> | undefined;
    const startupTimer = setTimeout(() => {
      finish();
      reject(new Error("The browser runner took too long to initialize. Please retry."));
    }, 60_000);

    const finish = () => {
      clearTimeout(startupTimer);
      if (executionTimer) clearTimeout(executionTimer);
      worker.terminate();
      onWorkerChange(null);
    };

    worker.onmessage = (event: MessageEvent<WorkerMessage>) => {
      const message = event.data;
      if (message.type === "ready") {
        clearTimeout(startupTimer);
        onReady();
        executionTimer = setTimeout(() => {
          finish();
          resolve({
            stdout: "",
            stderr: "Execution timed out after 5 seconds.",
            exit_code: 124,
            output_files: {},
          });
        }, 5_000);
        return;
      }

      finish();
      if (message.type === "error") {
        reject(new Error(message.error || "The browser runner failed."));
      } else if (message.data) {
        resolve(message.data);
      } else {
        reject(new Error("The browser runner returned an invalid response."));
      }
    };

    worker.onerror = (event) => {
      finish();
      reject(new Error(event.message || "The browser runner could not be started."));
    };

    worker.postMessage({
      language,
      code,
      input_files: inputFiles,
    });
  });
}

async function saveOutputFiles(
  apiBase: string,
  folderId: string | null,
  outputFiles: Record<string, string>,
): Promise<string[]> {
  const warnings: string[] = [];
  const query = new URLSearchParams({ folder: folderId || "none" });
  const existingByName = new Map<string, string>();

  try {
    let url: string | null = `${apiBase}/api/codelab/files/?${query}`;
    while (url) {
      const response = await apiFetch(url, {});
      if (!response.ok) throw new Error(`Could not load saved files (${response.status}).`);
      const page = await response.json();
      for (const file of page.results || page) {
        existingByName.set(file.filename, file.id);
      }
      url = page.next || null;
    }
  } catch (error) {
    return Object.keys(outputFiles).map(
      (name) => `${name}: ${error instanceof Error ? error.message : "Could not load saved files."}`,
    );
  }

  for (const [filename, content_b64] of Object.entries(outputFiles)) {
    const existingId = existingByName.get(filename);
    try {
      const response = await apiFetch(
        existingId
          ? `${apiBase}/api/codelab/files/${existingId}/`
          : `${apiBase}/api/codelab/files/`,
        {
          method: existingId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename,
            content_b64,
            folder: folderId,
            mime_type: "application/octet-stream",
          }),
        },
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        warnings.push(`${filename}: ${data.detail || "Could not save to your code library."}`);
      }
    } catch {
      warnings.push(`${filename}: Could not save to your code library.`);
    }
  }

  return warnings;
}

export default function CodeLab({ initialCode, language, isAuthenticated = false }: CodeLabProps) {
  const [code,       setCode]       = useState(initialCode);
  const [output,     setOutput]     = useState("");
  const [isRunning,  setIsRunning]  = useState(false);
  const [hasError,   setHasError]   = useState(false);
  const activeWorker = useRef<Worker | null>(null);

  // Save panel state
  const [showSave,   setShowSave]   = useState(false);
  const [folders,    setFolders]    = useState<CodeFolder[]>([]);
  const [saveState,  setSaveState]  = useState<SaveState>({ title: "", folderId: null });
  const [isSaving,   setIsSaving]   = useState(false);
  const [saveMsg,    setSaveMsg]    = useState<string | null>(null);

  // New folder creation
  const [newFolder,  setNewFolder]  = useState("");
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [creatingFolder, setCreatingFolder] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // File management
  const [inputFiles, setInputFiles] = useState<Record<string, string>>({}); // filename -> string content (for now just text)
  const [outputFiles, setOutputFiles] = useState<Record<string, string>>({}); // filename -> base64 content
  const [newFileName, setNewFileName] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [showAddFile, setShowAddFile] = useState(false);

  // Load folders when save panel opens
  useEffect(() => {
    if (!showSave || !isAuthenticated) return;
    apiFetch(`${apiBase}/api/codelab/folders/`, {})
      .then((r) => r.json())
      .then((d) => setFolders(d.results || d))
      .catch(() => {});
  }, [showSave, isAuthenticated, apiBase]);

  useEffect(() => () => activeWorker.current?.terminate(), []);

  const handleAddInputFile = () => {
    if (!newFileName.trim()) return;
    // convert text to base64 for the API
    const b64 = btoa(unescape(encodeURIComponent(newFileContent)));
    setInputFiles(prev => ({ ...prev, [newFileName.trim()]: b64 }));
    setNewFileName("");
    setNewFileContent("");
    setShowAddFile(false);
  };

  const handleRemoveInputFile = (name: string) => {
    const updated = { ...inputFiles };
    delete updated[name];
    setInputFiles(updated);
  };

  // ── Run code ────────────────────────────────────────────────────────────────
  const handleRun = async () => {
    setIsRunning(true);
    setOutput(language === "python" ? "Loading Python runtime…" : "Starting JavaScript runner…");
    setHasError(false);
    setOutputFiles({});
    try {
      const data = await runInBrowser(
        language,
        code,
        inputFiles,
        () => setOutput("Running…"),
        (worker) => { activeWorker.current = worker; },
      );
      if (data.exit_code !== 0) {
        setHasError(true);
        setOutput(data.stderr || data.stdout || "Error occurred");
      } else {
        setOutputFiles(data.output_files);
        const warnings = isAuthenticated && Object.keys(data.output_files).length > 0
          ? await saveOutputFiles(apiBase, saveState.folderId, data.output_files)
          : [];
        setOutput(
          [
            data.stdout || "✓ Success (no output)",
            data.stderr,
            warnings.length ? `Some files could not be saved:\n${warnings.join("\n")}` : "",
          ].filter(Boolean).join("\n\n"),
        );
      }
    } catch (error) {
      setHasError(true);
      setOutput(error instanceof Error ? error.message : "The browser runner failed.");
    } finally {
      activeWorker.current = null;
      setIsRunning(false);
    }
  };

  // ── Create folder ────────────────────────────────────────────────────────────
  const handleCreateFolder = async () => {
    if (!newFolder.trim()) return;
    setCreatingFolder(true);
    try {
      const res = await apiFetch(`${apiBase}/api/codelab/folders/`, {
        method: "POST",
        headers: { "Content-Type": "application/json",  },
        body: JSON.stringify({ name: newFolder.trim() }),
      });
      if (res.ok) {
        const folder = await res.json();
        setFolders((prev) => [...prev, folder]);
        setSaveState((s) => ({ ...s, folderId: folder.id }));
        setNewFolder("");
        setShowNewFolder(false);
      }
    } finally {
      setCreatingFolder(false);
    }
  };

  // ── Save snippet ─────────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!saveState.title.trim()) {
      setSaveMsg("⚠️ Please enter a title.");
      return;
    }
    setIsSaving(true);
    setSaveMsg(null);
    try {
      const res = await apiFetch(`${apiBase}/api/codelab/snippets/`, {
        method: "POST",
        headers: { "Content-Type": "application/json",  },
        body: JSON.stringify({
          title: saveState.title.trim(),
          language,
          code,
          folder: saveState.folderId || null,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSaveMsg("✅ Saved! View it in My Code →");
        setShowSave(false);
      } else {
        setSaveMsg(`⚠️ ${data.detail || data.code?.[0] || "Save failed."}`);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={styles.container}>
      {/* ── Toolbar ── */}
      <div className={styles.header}>
        <span className={styles.languageBadge}>{language}</span>
        <div className={styles.headerActions}>
          {isAuthenticated && (
            <button
              className={styles.saveBtn}
              onClick={() => { setShowSave((s) => !s); setSaveMsg(null); }}
            >
              {showSave ? "✕ Close" : "💾 Save"}
            </button>
          )}
          <button className={styles.runButton} onClick={handleRun} disabled={isRunning}>
            {isRunning ? "Running…" : "▶ Run"}
          </button>
        </div>
      </div>

      {/* ── Save panel (slide-down) ── */}
      {showSave && isAuthenticated && (
        <div className={styles.savePanel}>
          <h4 className={styles.savePanelTitle}>💾 Save to My Code</h4>

          <label className={styles.saveLabel}>Title</label>
          <input
            className={styles.saveInput}
            placeholder="e.g. Fibonacci solution"
            value={saveState.title}
            onChange={(e) => setSaveState((s) => ({ ...s, title: e.target.value }))}
          />

          <label className={styles.saveLabel}>Folder (optional)</label>
          <div className={styles.folderRow}>
            <select
              className={styles.saveSelect}
              value={saveState.folderId || ""}
              onChange={(e) => setSaveState((s) => ({ ...s, folderId: e.target.value || null }))}
            >
              <option value="">— Unfiled —</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            <button
              className={styles.newFolderToggle}
              onClick={() => setShowNewFolder((v) => !v)}
            >
              + New Folder
            </button>
          </div>

          {showNewFolder && (
            <div className={styles.newFolderRow}>
              <input
                className={styles.saveInput}
                placeholder="Folder name"
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
              />
              <button
                className={styles.createFolderBtn}
                onClick={handleCreateFolder}
                disabled={creatingFolder}
              >
                {creatingFolder ? "Creating…" : "Create"}
              </button>
            </div>
          )}

          {saveMsg && (
            <p className={`${styles.saveMsg} ${saveMsg.startsWith("✅") ? styles.saveMsgOk : styles.saveMsgErr}`}>
              {saveMsg}
            </p>
          )}

          <div className={styles.savePanelActions}>
            <button className={styles.saveConfirmBtn} onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving…" : "Save Snippet"}
            </button>
          </div>
        </div>
      )}
      
      {/* ── File Management ── */}
      <div className={styles.filesSection}>
        <div className={styles.filesHeader}>
          <h4 className={styles.filesTitle}>Files (Working Directory)</h4>
          <button className={styles.addFileBtn} onClick={() => setShowAddFile(!showAddFile)}>+ Add File</button>
        </div>
        
        {showAddFile && (
           <div className={styles.addFileForm}>
             <input className={styles.fileInput} placeholder="data.txt" value={newFileName} onChange={e => setNewFileName(e.target.value)} />
             <textarea className={styles.fileTextarea} placeholder="File content..." value={newFileContent} onChange={e => setNewFileContent(e.target.value)}></textarea>
             <button className={styles.saveFileBtn} onClick={handleAddInputFile}>Attach File</button>
           </div>
        )}

        {Object.keys(inputFiles).length > 0 && (
          <div className={styles.fileList}>
            {Object.keys(inputFiles).map(name => (
              <div key={name} className={styles.fileItem}>
                <span>📄 {name}</span>
                <button onClick={() => handleRemoveInputFile(name)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Editor ── */}
      <div className={styles.editorWrapper}>
        <textarea
          className={styles.editor}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
        />
      </div>

      {/* ── Output ── */}
      {output && (
        <div className={`${styles.outputWrapper} ${hasError ? styles.error : ""}`}>
          <div className={styles.outputHeader}>Output</div>
          <pre className={styles.output}>{output}</pre>
        </div>
      )}
      
      {/* ── Output Files ── */}
      {Object.keys(outputFiles).length > 0 && (
        <div className={styles.outputFilesSection}>
          <div className={styles.outputHeader}>Generated Files {isAuthenticated ? "(Auto-saved to My Code)" : ""}</div>
          <div className={styles.fileList}>
            {Object.entries(outputFiles).map(([name, b64]) => {
                let contentPreview = "";
                try {
                    contentPreview = decodeURIComponent(escape(atob(b64)));
                } catch { contentPreview = "<Binary Data>"; }
                
                const handleDownload = () => {
                    const link = document.createElement("a");
                    link.href = `data:application/octet-stream;base64,${b64}`;
                    link.download = name;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                };

                return (
                  <div key={name} className={styles.outputFileItem}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <strong style={{ margin: 0, color: '#e2e8f0' }}>📄 {name}</strong>
                        <button onClick={handleDownload} className={styles.saveBtn} style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}>
                            📥 Download
                        </button>
                    </div>
                    <pre>{contentPreview.substring(0, 100)}{contentPreview.length > 100 ? "..." : ""}</pre>
                  </div>
                )
            })}
          </div>
        </div>
      )}

      {/* Inline save notification (after panel is closed) */}
      {!showSave && saveMsg?.startsWith("✅") && (
        <p className={styles.inlineSaveOk}>{saveMsg}</p>
      )}
    </div>
  );
}
