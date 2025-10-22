// Lightweight Pyodide loader and helpers for running Python and installing packages client-side.
// This uses the public CDN and micropip inside the Pyodide environment.

export interface RunResult {
  stdout: string;
  stderr: string;
  result?: unknown;
}

export interface StreamHandlers {
  onStdout?: (msg: string) => void;
  onStderr?: (msg: string) => void;
}

let pyodideReady: Promise<any> | null = null;

declare global {
  interface Window {
    loadPyodide?: (opts: { indexURL: string }) => Promise<any>;
  }
}

async function ensureLoaded(): Promise<any> {
  if (pyodideReady) return pyodideReady;
  pyodideReady = (async () => {
    if (!window.loadPyodide) {
      // Load Pyodide script dynamically and wait for it to be available
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js';
      document.head.appendChild(script);
      await new Promise((resolve, reject) => {
        script.onload = () => {
          // Wait a bit more for loadPyodide to be available
          const checkPyodide = () => {
            if (window.loadPyodide) {
              resolve(undefined);
            } else {
              setTimeout(checkPyodide, 50);
            }
          };
          checkPyodide();
        };
        script.onerror = reject;
      });
    }
    const pyodide = await window.loadPyodide!({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/" });
    // Preload micropip for installs
    await pyodide.loadPackage("micropip");
    return pyodide;
  })();
  return pyodideReady;
}

export async function runCode(code: string): Promise<RunResult> {
  const pyodide = await ensureLoaded();

  // Set up output capture using Python's sys module
  const setupCode = `
import sys
from io import StringIO

# Create string buffers to capture output
_stdout_buffer = StringIO()
_stderr_buffer = StringIO()

# Save original stdout/stderr
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# Redirect output to our buffers
sys.stdout = _stdout_buffer
sys.stderr = _stderr_buffer
`;

  const cleanupCode = `
# Get the captured output
_captured_stdout = _stdout_buffer.getvalue()
_captured_stderr = _stderr_buffer.getvalue()

# Restore original stdout/stderr
sys.stdout = _original_stdout
sys.stderr = _original_stderr

# Return the captured output
(_captured_stdout, _captured_stderr)
`;

  try {
    // Set up output capture
    await pyodide.runPythonAsync(setupCode);

    // Run the user code
    const result = await pyodide.runPythonAsync(code);

    // Get captured output
    const [capturedStdout, capturedStderr] = await pyodide.runPythonAsync(cleanupCode);

    return {
      stdout: capturedStdout || "",
      stderr: capturedStderr || "",
      result
    };
  } catch (error) {
    // Make sure to restore stdout/stderr even if there's an error
    try {
      await pyodide.runPythonAsync(`
sys.stdout = _original_stdout
sys.stderr = _original_stderr
_captured_stderr = _stderr_buffer.getvalue()
_captured_stderr
`);
    } catch (cleanupError) {
      // If cleanup fails, just return the original error
    }

    throw error;
  }
}

export async function installPackages(packages: string[]): Promise<RunResult> {
  await ensureLoaded();
  const code = `import micropip\nfor p in ${JSON.stringify(packages)}:\n    micropip.install(p)\nprint('installed:', ${JSON.stringify(packages)})`;
  return runCode(code);
}

export async function runFunction(funcName: string, args: unknown[] = [], env: Record<string, string> = {}): Promise<RunResult> {
  await ensureLoaded();
  const argList = JSON.stringify(args);
  const envJson = JSON.stringify(env);
  const code = `import json, os\nos.environ.update(json.loads('''${envJson}'''))\nres = ${funcName}(*json.loads('''${argList}'''))\nprint(json.dumps(res if res is not None else None))`;
  return runCode(code);
}

export async function formatPythonWithBlack(source: string): Promise<string> {
  const py = `\nimport micropip\ntry:\n    import black\nexcept Exception:\n    await micropip.install('black')\n    import black\n_src = ${JSON.stringify(source)}\nprint(black.format_str(_src, mode=black.FileMode()))\n`;
  const out = await runCode(py);
  return out.stdout || (typeof out.result === 'string' ? String(out.result) : source);
}



export function extractPackagesFromCode(code: string): string[] {
  const re = /^(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.]+))/gm;
  const builtins = new Set([
    "math", "json", "datetime", "statistics", "random", "os", "sys", "re", "typing", "logging",
    "time", "pathlib", "itertools", "functools", "collections", "enum", "dataclasses",
    "typing_extensions", "numpy", "pandas", "requests", "matplotlib", "scipy", "sklearn"
  ]);
  const found = new Set<string>();
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) {
    const pkg = (m[1] || m[2]).split('.')[0];
    if (!builtins.has(pkg)) {
      found.add(pkg);
    }
  }
  return Array.from(found);
}

export async function runCodeStreaming(code: string, handlers: StreamHandlers = {}): Promise<RunResult> {
  const pyodide = await ensureLoaded();

  const lines: string[] = [];
  const errs: string[] = [];
  const onStdout = handlers.onStdout ?? (() => {});
  const onStderr = handlers.onStderr ?? (() => {});

  // Extract and log imported packages
  const importedPackages = extractPackagesFromCode(code);
  if (importedPackages.length > 0) {
    const packageMsg = `📦 Detected imports: ${importedPackages.join(', ')}\n`;
    lines.push(packageMsg);
    onStdout(packageMsg);
  }

  // Stream per line when flushed/newline using batched handlers.
  pyodide.setStdout?.({ batched: (msg: string) => { lines.push(msg); onStdout(msg); } });
  pyodide.setStderr?.({ batched: (msg: string) => { errs.push(msg); onStderr(msg); } });

  try {
    const result = await pyodide.runPythonAsync(code);
    return { stdout: lines.join(""), stderr: errs.join(""), result };
  } finally {
    // Always restore default handlers
    try {
      pyodide.setStdout?.({});
      pyodide.setStderr?.({});
    } catch {}
  }
}
