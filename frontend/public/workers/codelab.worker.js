const PYODIDE_VERSION = "314.0.7";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const WORKSPACE = "/home/pyodide";
const MAX_CODE_BYTES = 512 * 1024;
const MAX_FILE_BYTES = 1024 * 1024;
const MAX_TOTAL_FILE_BYTES = 2 * 1024 * 1024;
const MAX_OUTPUT_FILE_BYTES = 10 * 1024 * 1024;
const MAX_OUTPUT_FILES = 20;
const MAX_STDIO_BYTES = 256 * 1024;

let pyodidePromise;

function validateFileName(name) {
  return (
    typeof name === "string" &&
    name.length > 0 &&
    name !== "." &&
    name !== ".." &&
    !name.includes("/") &&
    !name.includes("\\")
  );
}

function decodeBase64(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function encodeBase64(bytes) {
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}

function appendBounded(current, text) {
  if (current.length >= MAX_STDIO_BYTES) return current;
  return current + text.slice(0, MAX_STDIO_BYTES - current.length);
}

function collectPythonFiles(pyodide) {
  const outputFiles = {};
  let totalBytes = 0;

  function visit(directory, relativeDirectory = "") {
    for (const name of pyodide.FS.readdir(directory)) {
      if (name === "." || name === ".." || name.startsWith(".")) continue;

      const path = `${directory}/${name}`;
      const relativePath = relativeDirectory ? `${relativeDirectory}/${name}` : name;
      const stat = pyodide.FS.lstat(path);
      if (pyodide.FS.isLink(stat.mode)) continue;

      if (pyodide.FS.isDir(stat.mode)) {
        visit(path, relativePath);
        continue;
      }
      if (!pyodide.FS.isFile(stat.mode) || stat.size > MAX_OUTPUT_FILE_BYTES) continue;
      if (Object.keys(outputFiles).length >= MAX_OUTPUT_FILES) return;
      if (totalBytes + stat.size > MAX_OUTPUT_FILE_BYTES) continue;

      const bytes = pyodide.FS.readFile(path);
      outputFiles[relativePath] = encodeBase64(bytes);
      totalBytes += bytes.length;
    }
  }

  visit(WORKSPACE);
  return outputFiles;
}

async function getPyodide() {
  if (!pyodidePromise) {
    importScripts(`${PYODIDE_INDEX_URL}pyodide.js`);
    pyodidePromise = loadPyodide({ indexURL: PYODIDE_INDEX_URL });
  }
  return pyodidePromise;
}

function normalizeVirtualPath(name) {
  if (typeof name !== "string" || !name) throw new Error("A file path is required.");
  const parts = name.replaceAll("\\", "/").split("/");
  const normalized = [];

  for (const part of parts) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (normalized.length === 0) throw new Error("Path is outside the working directory.");
      normalized.pop();
    } else {
      normalized.push(part);
    }
  }
  return normalized.join("/");
}

function createJavaScriptFileSystem(inputFiles) {
  const files = new Map();
  const directories = new Set();
  let totalInputBytes = 0;

  for (const [name, encoded] of Object.entries(inputFiles)) {
    if (!validateFileName(name)) throw new Error(`Invalid input filename: ${name}`);
    const content = decodeBase64(encoded);
    if (content.length > MAX_FILE_BYTES) throw new Error(`Input file is too large: ${name}`);
    totalInputBytes += content.length;
    if (totalInputBytes > MAX_TOTAL_FILE_BYTES) throw new Error("Input files exceed the size limit.");
    files.set(name, content);
  }

  const getPath = (name) => normalizeVirtualPath(name);
  const asBytes = (content) => {
    if (typeof content === "string") return new TextEncoder().encode(content);
    if (content instanceof Uint8Array) return content;
    if (ArrayBuffer.isView(content)) {
      return new Uint8Array(content.buffer, content.byteOffset, content.byteLength);
    }
    if (content instanceof ArrayBuffer) return new Uint8Array(content);
    throw new TypeError("File content must be a string or byte array.");
  };
  const fs = {
    readFileSync(name, options) {
      const path = getPath(name);
      const content = files.get(path);
      if (!content) throw new Error(`File not found: ${path}`);
      const encoding = typeof options === "string" ? options : options?.encoding;
      return encoding ? new TextDecoder(encoding).decode(content) : content.slice();
    },
    writeFileSync(name, content) {
      const path = getPath(name);
      if (!path) throw new Error("Cannot write to the working directory.");
      files.set(path, asBytes(content).slice());
    },
    existsSync(name) {
      const path = getPath(name);
      return !path || files.has(path) || directories.has(path);
    },
    readdirSync(name = ".") {
      const path = getPath(name);
      const prefix = path ? `${path}/` : "";
      const entries = new Set();
      for (const entryPath of [...files.keys(), ...directories]) {
        if (!entryPath.startsWith(prefix)) continue;
        const entry = entryPath.slice(prefix.length).split("/")[0];
        if (entry) entries.add(entry);
      }
      return [...entries];
    },
    mkdirSync(name) {
      const path = getPath(name);
      if (!path) return;
      let current = "";
      for (const part of path.split("/")) {
        current = current ? `${current}/${part}` : part;
        directories.add(current);
      }
    },
    unlinkSync(name) {
      const path = getPath(name);
      if (!files.delete(path)) throw new Error(`File not found: ${path}`);
    },
    statSync(name) {
      const path = getPath(name);
      const isFile = files.has(path);
      const isDirectory = !isFile && (!path || directories.has(path));
      if (!isFile && !isDirectory) throw new Error(`File not found: ${path}`);
      return {
        isFile: () => isFile,
        isDirectory: () => isDirectory,
        size: isFile ? files.get(path).length : 0,
      };
    },
  };

  const path = {
    join: (...parts) => normalizeVirtualPath(parts.join("/")),
    resolve: (...parts) => `/${normalizeVirtualPath(parts.join("/"))}`,
    basename: (value) => normalizeVirtualPath(value).split("/").pop() || "",
    dirname: (value) => normalizeVirtualPath(value).split("/").slice(0, -1).join("/") || ".",
    extname: (value) => {
      const basename = normalizeVirtualPath(value).split("/").pop() || "";
      const index = basename.lastIndexOf(".");
      return index > 0 ? basename.slice(index) : "";
    },
  };

  return {
    fs,
    path,
    getOutputFiles() {
      const outputFiles = {};
      let totalBytes = 0;
      for (const [name, content] of files) {
        if (content.length > MAX_OUTPUT_FILE_BYTES) continue;
        if (Object.keys(outputFiles).length >= MAX_OUTPUT_FILES) break;
        if (totalBytes + content.length > MAX_OUTPUT_FILE_BYTES) continue;
        outputFiles[name] = encodeBase64(content);
        totalBytes += content.length;
      }
      return outputFiles;
    },
  };
}

function formatValue(value) {
  if (typeof value === "string") return value;
  try {
    const json = JSON.stringify(value);
    return json === undefined ? String(value) : json;
  } catch {
    return String(value);
  }
}

function runJavaScript(code, inputFiles) {
  const virtualFiles = createJavaScriptFileSystem(inputFiles);
  let stdout = "";
  let stderr = "";

  function append(target, values) {
    const text = `${values.map(formatValue).join(" ")}\n`;
    if (target === "stderr") stderr = appendBounded(stderr, text);
    else stdout = appendBounded(stdout, text);
  }

  const consoleApi = {
    log: (...values) => append("stdout", values),
    info: (...values) => append("stdout", values),
    warn: (...values) => append("stderr", values),
    error: (...values) => append("stderr", values),
  };
  const processApi = {
    cwd: () => "/workspace",
    env: {},
    stdout: { write: (value) => { stdout = appendBounded(stdout, String(value)); return true; } },
    stderr: { write: (value) => { stderr = appendBounded(stderr, String(value)); return true; } },
  };
  const requireApi = (moduleName) => {
    if (moduleName === "fs") return virtualFiles.fs;
    if (moduleName === "path") return virtualFiles.path;
    throw new Error(`Node.js module '${moduleName}' is not available in the browser runner.`);
  };

  try {
    const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
    const execute = new AsyncFunction("console", "require", "process", code);
    return Promise.resolve(execute(consoleApi, requireApi, processApi)).then(
      () => ({
        stdout: stdout.slice(0, MAX_STDIO_BYTES),
        stderr: stderr.slice(0, MAX_STDIO_BYTES),
        exit_code: 0,
        output_files: virtualFiles.getOutputFiles(),
      }),
      (error) => ({
        stdout: stdout.slice(0, MAX_STDIO_BYTES),
        stderr: `${stderr}${String(error?.stack || error)}`.slice(0, MAX_STDIO_BYTES),
        exit_code: 1,
        output_files: virtualFiles.getOutputFiles(),
      }),
    );
  } catch (error) {
    return Promise.resolve({
      stdout: stdout.slice(0, MAX_STDIO_BYTES),
      stderr: `${stderr}${String(error?.stack || error)}`.slice(0, MAX_STDIO_BYTES),
      exit_code: 1,
      output_files: virtualFiles.getOutputFiles(),
    });
  }
}

self.onmessage = async (event) => {
  const { language, code, input_files: inputFiles = {} } = event.data || {};

  try {
    if (typeof code !== "string" || new TextEncoder().encode(code).length > MAX_CODE_BYTES) {
      throw new Error("Code is missing or exceeds the 512 KB size limit.");
    }
    if (!["python", "javascript"].includes(language)) {
      throw new Error(`Unsupported language: ${language}`);
    }

    if (language === "javascript") {
      createJavaScriptFileSystem(inputFiles);
      self.postMessage({ type: "ready" });
      const result = await runJavaScript(code, inputFiles);
      self.postMessage({ type: "result", data: result });
      return;
    }

    const pyodide = await getPyodide();
    pyodide.FS.mkdirTree(WORKSPACE);
    pyodide.runPython(`import os\nos.chdir(${JSON.stringify(WORKSPACE)})`);

    let totalInputBytes = 0;
    for (const [name, encoded] of Object.entries(inputFiles)) {
      if (!validateFileName(name)) throw new Error(`Invalid input filename: ${name}`);
      const content = decodeBase64(encoded);
      if (content.length > MAX_FILE_BYTES) throw new Error(`Input file is too large: ${name}`);
      totalInputBytes += content.length;
      if (totalInputBytes > MAX_TOTAL_FILE_BYTES) throw new Error("Input files exceed the size limit.");
      pyodide.FS.writeFile(`${WORKSPACE}/${name}`, content);
    }

    let stdout = "";
    let stderr = "";
    pyodide.setStdout({ batched: (text) => { stdout = appendBounded(stdout, text); } });
    pyodide.setStderr({ batched: (text) => { stderr = appendBounded(stderr, text); } });
    self.postMessage({ type: "ready" });

    let exitCode = 0;
    try {
      await pyodide.runPythonAsync(code);
    } catch (error) {
      stderr = appendBounded(stderr, `${String(error)}\n`);
      exitCode = 1;
    }

    self.postMessage({
      type: "result",
      data: {
        stdout: stdout.slice(0, MAX_STDIO_BYTES),
        stderr: stderr.slice(0, MAX_STDIO_BYTES),
        exit_code: exitCode,
        output_files: collectPythonFiles(pyodide),
      },
    });
  } catch (error) {
    self.postMessage({ type: "error", error: String(error?.stack || error) });
  }
};
