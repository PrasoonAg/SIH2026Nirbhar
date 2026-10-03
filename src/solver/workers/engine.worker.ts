/**
 * NIRBHAR Engine Worker
 * Runs the solver in a Web Worker to keep the UI responsive.
 * 
 * Message protocol:
 *   → { type: 'SOLVE', id: string, mpsText: string, engine?: string, options?: SolveOptions }
 *   ← { type: 'PROGRESS', id: string, phase: 1|2, iteration: number, objective: number }
 *   ← { type: 'RESULT', id: string, result: DispatchResult }
 *   ← { type: 'ERROR', id: string, message: string }
 */

import { parseMPS } from '../io/mps';
import { dispatch } from '../dispatch';
import type { EngineId } from '../dispatch';
import type { SolveOptions } from '../lp/dualSimplex';
import type { ProgressInfo } from '../lp/dualSimplex';

export type WorkerInMessage =
  | { type: 'SOLVE'; id: string; mpsText: string; engine?: EngineId; options?: SolveOptions }
  | { type: 'PING' };

export type WorkerOutMessage =
  | { type: 'PROGRESS'; id: string; phase: 1 | 2; iteration: number; objective: number; infeasibility?: number }
  | { type: 'RESULT'; id: string; result: unknown }
  | { type: 'ERROR'; id: string; message: string }
  | { type: 'PONG' };

self.onmessage = async (ev: MessageEvent<WorkerInMessage>) => {
  const msg = ev.data;

  if (msg.type === 'PING') {
    const out: WorkerOutMessage = { type: 'PONG' };
    self.postMessage(out);
    return;
  }

  if (msg.type === 'SOLVE') {
    const { id, mpsText, engine, options } = msg;

    try {
      // Parse MPS
      const { model, errors, warnings } = parseMPS(mpsText);

      if (errors.length > 0 && model.nCols === 0) {
        const out: WorkerOutMessage = {
          type: 'ERROR',
          id,
          message: `MPS parse errors: ${errors.join('; ')}`,
        };
        self.postMessage(out);
        return;
      }

      // Set up progress callback
      const opts: SolveOptions = {
        ...(options ?? {}),
        onProgress: (info: ProgressInfo) => {
          const out: WorkerOutMessage = {
            type: 'PROGRESS',
            id,
            phase: info.phase,
            iteration: info.iteration,
            objective: info.objective,
          };
          self.postMessage(out);
        },
      };

      // Dispatch to engine
      const result = await dispatch({ model, engine: engine as EngineId | undefined, options: opts });

      const out: WorkerOutMessage = {
        type: 'RESULT',
        id,
        result: {
          ...result,
          // Attach model info for UI display
          modelInfo: {
            name: model.name,
            nRows: model.nRows,
            nCols: model.nCols,
            nnz: model.nnz,
            sense: model.sense,
            parseErrors: errors,
            parseWarnings: warnings,
          },
        },
      };
      self.postMessage(out);
    } catch (err) {
      const out: WorkerOutMessage = {
        type: 'ERROR',
        id,
        message: err instanceof Error ? err.message : String(err),
      };
      self.postMessage(out);
    }
  }
};
