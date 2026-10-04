/**
 * NIRBHAR — Sovereign Hybrid Bridge Client
 * Enables seamless communication between the React Frontend and the
 * Python/JAX Sovereign Industrial Core (localhost:8000).
 *
 * Fallback Discipline:
 * If the Python server is offline, returns null/unavailable status so the
 * UI gracefully executes via the in-browser Web Worker engine.
 */

export interface BackendHealth {
  online: boolean;
  version?: string;
  hasJax?: boolean;
  jaxVersion?: string;
  devices?: string[];
  supportedEngines?: string[];
  url: string;
}

export interface BackendSolveResult {
  status: string;
  objective: number;
  lower_bound?: number;
  gap?: number;
  iterations: number;
  parse_time_ms: number;
  solve_time_ms: number;
  solve_path: string[];
  engine_used: string;
  has_jax: boolean;
  dimensions?: {
    rows: number;
    cols: number;
    nnz: number;
    integers: number;
  };
  x?: number[];
  y?: number[];
  certificate?: any;
}

const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';

/** Check if the local Python/JAX sovereign engine is online */
export async function checkBackendHealth(baseUrl = DEFAULT_BACKEND_URL): Promise<BackendHealth> {
  try {
    const res = await fetch(`${baseUrl}/api/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(1500),
    });
    if (!res.ok) {
      return { online: false, url: baseUrl };
    }
    const data = await res.json();
    return {
      online: true,
      version: data.version,
      hasJax: data.has_jax,
      jaxVersion: data.jax_version,
      devices: data.jax_devices,
      supportedEngines: data.supported_engines,
      url: baseUrl,
    };
  } catch {
    return { online: false, url: baseUrl };
  }
}

/** Solve model using the live Python/JAX Core */
export async function solveViaBackend(
  mpsText: string,
  method = 'auto',
  baseUrl = DEFAULT_BACKEND_URL
): Promise<BackendSolveResult> {
  const res = await fetch(`${baseUrl}/api/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mps_text: mpsText, method }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Network request failed' }));
    throw new Error(err.error || `Server responded with status ${res.status}`);
  }

  return await res.json();
}

/** Solve MRPL refinery planning instance on Python backend */
export async function solveRefineryViaBackend(
  periods = 4,
  problemClass = 'LP',
  scenario = 'baseline',
  baseUrl = DEFAULT_BACKEND_URL
) {
  const res = await fetch(`${baseUrl}/api/refinery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ periods, problem_class: problemClass, scenario }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Refinery solve failed' }));
    throw new Error(err.error || `Server responded with status ${res.status}`);
  }

  return await res.json();
}
