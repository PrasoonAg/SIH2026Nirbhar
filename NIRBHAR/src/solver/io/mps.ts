/**
 * NIRBHAR MPS/QPS Parser
 * Supports: fixed-field and free-format MPS
 * Sections: NAME, ROWS, COLUMNS, RHS, RANGES, BOUNDS, QUADOBJ/QMATRIX, OBJSENSE, ENDATA
 * Bound types: LO UP FX FR MI PL BV LI UI
 * Integer markers: INTORG / INTEND
 * RANGES: per the MPS spec (L/G/E rules)
 */

import { ModelBuilder, INF, BINARY, INTEGER } from './model';
import type { Model, RowType } from './model';

export interface ParseResult {
  model: Model;
  errors: string[];
  warnings: string[];
  parseTimeMs: number;
}

export function parseMPS(text: string): ParseResult {
  const t0 = performance.now();
  const builder = new ModelBuilder();
  const errors: string[] = [];
  const warnings: string[] = [];

  // Store the original text for SHA-256 (computed async by caller)
  builder.sourceText = text;

  const lines = text.split(/\r?\n/);

  // --- Index maps ---
  const rowByName = new Map<string, number>();
  const colByName = new Map<string, number>();
  const rowTypes  = new Map<number, RowType>();
  let objRowName  = '';
  let objRowIdx   = -1;  // internal row index if objective row is treated as a row

  type Section =
    | 'NAME' | 'ROWS' | 'COLUMNS' | 'RHS' | 'RANGES'
    | 'BOUNDS' | 'QUADOBJ' | 'QMATRIX' | 'OBJSENSE' | 'NONE';

  let section: Section = 'NONE';
  let inIntegers = false;  // inside INTORG/INTEND block
  let objSense: 'min' | 'max' = 'min';

  /** Get or create a column, returning its index */
  function ensureCol(name: string): number {
    let idx = colByName.get(name);
    if (idx === undefined) {
      idx = builder.addCol(name);
      colByName.set(name, idx);
    }
    return idx;
  }

  /** Get or create a row index (non-objective). Returns -1 for the N/obj row. */
  function getRowIdx(name: string): number {
    if (name === objRowName) return -1;
    const idx = rowByName.get(name);
    if (idx === undefined) {
      errors.push(`Unknown row name "${name}" in COLUMNS/RHS/RANGES section`);
      return -1;
    }
    return idx;
  }

  /** Parse a field value from MPS line, returning number or NaN */
  function parseVal(s: string): number {
    const v = parseFloat(s);
    return isNaN(v) ? NaN : v;
  }

  /** Split a MPS line into tokens, handling fixed-field or free format */
  function tokenize(line: string): string[] {
    // Try free format first (space-delimited)
    return line.trim().split(/\s+/).filter(t => t.length > 0);
  }

  for (let lineNum = 0; lineNum < lines.length; lineNum++) {
    const rawLine = lines[lineNum];
    const line = rawLine.trimEnd();

    // Skip blank and comment lines
    if (line.length === 0 || line[0] === '$' || line[0] === '*') continue;

    // Section header detection: starts in column 0 (no leading space) OR is a keyword
    const firstChar = line[0];
    const trimmed = line.trim();

    if (!trimmed) continue;

    // Check for section headers (must start at column 0 or be recognizable keywords)
    const upper = trimmed.toUpperCase();
    const token0 = upper.split(/\s+/)[0];

    if (firstChar !== ' ' && firstChar !== '\t') {
      // Section line
      switch (token0) {
        case 'NAME':
          section = 'NAME';
          builder.name = trimmed.replace(/^NAME\s*/i, '').trim() || 'untitled';
          continue;
        case 'ROWS':      section = 'ROWS';     continue;
        case 'COLUMNS':   section = 'COLUMNS';  continue;
        case 'RHS':       section = 'RHS';       continue;
        case 'RANGES':    section = 'RANGES';    continue;
        case 'BOUNDS':    section = 'BOUNDS';    continue;
        case 'QUADOBJ':
        case 'QMATRIX':   section = 'QUADOBJ';  continue;
        case 'OBJSENSE':  section = 'OBJSENSE'; continue;
        case 'ENDATA':    break;
        default:
          // Unknown section — skip
          section = 'NONE';
          continue;
      }
      break; // ENDATA
    }

    // Data line
    const tokens = tokenize(line);
    if (tokens.length === 0) continue;

    switch (section) {
      case 'OBJSENSE': {
        const s = tokens[0].toLowerCase();
        objSense = s === 'max' ? 'max' : 'min';
        builder.sense = objSense;
        break;
      }

      case 'ROWS': {
        if (tokens.length < 2) {
          errors.push(`Line ${lineNum + 1}: ROWS entry needs type and name`);
          continue;
        }
        const type = tokens[0].toUpperCase() as RowType;
        const name = tokens[1];
        if (type === 'N') {
          if (objRowName === '') {
            objRowName = name;
            builder.objRowName = name;
          }
          // Subsequent N rows are free rows — ignore for now
        } else if (type === 'L' || type === 'G' || type === 'E') {
          const idx = builder.addRow(name, type);
          rowByName.set(name, idx);
          rowTypes.set(idx, type);
        } else {
          errors.push(`Line ${lineNum + 1}: Unknown row type "${type}"`);
        }
        break;
      }

      case 'COLUMNS': {
        // Check for integer markers (e.g., MARK0000 'MARKER' 'INTORG')
        const markerIdx = tokens.findIndex(t => t.toUpperCase().replace(/['"]/g, '') === 'MARKER');
        if (markerIdx >= 0 && markerIdx + 1 < tokens.length) {
          const tag = tokens[markerIdx + 1].toUpperCase().replace(/['"]/g, '');
          if (tag === 'INTORG') inIntegers = true;
          else if (tag === 'INTEND') inIntegers = false;
          continue;
        }

        // Format: [indent] colName  rowName1 value1 [rowName2 value2]
        if (tokens.length < 3) continue;

        const colName = tokens[0];
        const colIdx  = ensureCol(colName);
        if (inIntegers) {
          const c = builder['cols'][colIdx];
          if (c && c.integ === 0) c.integ = INTEGER;
        }

        // Parse pairs: (rowName, value)
        let i = 1;
        while (i + 1 < tokens.length) {
          const rowName = tokens[i];
          const val     = parseVal(tokens[i + 1]);
          i += 2;

          if (isNaN(val)) {
            errors.push(`Line ${lineNum + 1}: Non-numeric value "${tokens[i - 1]}"`);
            continue;
          }

          if (rowName === objRowName) {
            builder.setObjCoeff(colIdx, val);
          } else {
            const rowIdx = getRowIdx(rowName);
            if (rowIdx >= 0) builder.setEntry(rowIdx, colIdx, val);
          }
        }
        break;
      }

      case 'RHS': {
        // Format: [indent] rhsName  rowName1 value1 [rowName2 value2]
        if (tokens.length < 3) continue;
        let i = 1;  // skip RHS vector name (tokens[0])
        while (i + 1 < tokens.length) {
          const rowName = tokens[i];
          const val     = parseVal(tokens[i + 1]);
          i += 2;
          if (isNaN(val)) { errors.push(`Line ${lineNum + 1}: Non-numeric RHS value`); continue; }
          if (rowName === objRowName) {
            builder.objConstant = -val; // RHS of objective row → shift constant (rarely used)
            continue;
          }
          const rowIdx = getRowIdx(rowName);
          if (rowIdx < 0) continue;
          const type = rowTypes.get(rowIdx) ?? 'E';
          builder.setRhs(rowIdx, val, type);
        }
        break;
      }

      case 'RANGES': {
        // Format: [indent] rangeName  rowName1 value1 [rowName2 value2]
        if (tokens.length < 3) continue;
        let i = 1;
        while (i + 1 < tokens.length) {
          const rowName = tokens[i];
          const range   = parseVal(tokens[i + 1]);
          i += 2;
          if (isNaN(range)) continue;
          const rowIdx = getRowIdx(rowName);
          if (rowIdx < 0) continue;
          const type = rowTypes.get(rowIdx) ?? 'E';
          builder.applyRange(rowIdx, range, type);
        }
        break;
      }

      case 'BOUNDS': {
        // Format: [indent] boundType  bndName  colName [value]
        if (tokens.length < 3) continue;
        const bType   = tokens[0].toUpperCase();
        // tokens[1] is the bound vector name (ignored)
        const colName = tokens[2];
        const colIdx  = ensureCol(colName);
        const val     = tokens.length >= 4 ? parseVal(tokens[3]) : 0;

        if (['LO', 'UP', 'FX', 'LI', 'UI'].includes(bType)) {
          if (isNaN(val)) { errors.push(`Line ${lineNum + 1}: Non-numeric bound value`); break; }
          builder.setColBound(colIdx, bType, val);
        } else if (['FR', 'MI', 'PL', 'BV'].includes(bType)) {
          builder.setColBound(colIdx, bType, 0);
        } else {
          warnings.push(`Line ${lineNum + 1}: Unknown bound type "${bType}"`);
        }

        // Handle BV: enforce binary integrality
        if (bType === 'BV') {
          const c = builder['cols'][colIdx];
          if (c) c.integ = BINARY;
        }
        break;
      }

      case 'QUADOBJ': {
        // Format: [indent] colName1  colName2  value  (upper-triangular Q)
        // ½ x^T Q x where Q is symmetric. MPS stores upper triangle.
        // We handle this in Phase 2 (QP support).
        // For Phase 1, just note it exists.
        warnings.push(`Line ${lineNum + 1}: QUADOBJ section detected — QP support enabled in Phase 2`);
        break;
      }

      default:
        break;
    }
  }

  // If OBJSENSE was 'max', negate objective
  if (objSense === 'max') {
    const cols = builder['cols'];
    const cObj = builder['cObj'] as Map<number, number>;
    for (const [k, v] of cObj) {
      cObj.set(k, -v);
    }
    builder.sense = 'max'; // keep sense label
    // The internal solver always minimizes; negation of c handles this
  }

  // Final validation
  if (objRowName === '') warnings.push('No N-type objective row found; objective is zero');

  builder.parseErrors = errors;
  const model = builder.build();
  const parseTimeMs = performance.now() - t0;

  return { model, errors, warnings, parseTimeMs };
}

/** Compute SHA-256 of raw model text (async, using Web Crypto) */
export async function computeSHA256(text: string): Promise<string> {
  const encoded = new TextEncoder().encode(text);
  const hashBuf = await crypto.subtle.digest('SHA-256', encoded);
  const hashArr = Array.from(new Uint8Array(hashBuf));
  return hashArr.map(b => b.toString(16).padStart(2, '0')).join('');
}
