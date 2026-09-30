/**
 * NIRBHAR Verifier — Minimal MPS Reader
 * 
 * ⚠️  SOVEREIGNTY RULE: This file must NOT import from src/solver.
 *      It is a completely isolated reader for the verification engine.
 * 
 * Supports the subset of MPS needed for verification:
 *   ROWS, COLUMNS, RHS, RANGES, BOUNDS, OBJSENSE
 * Produces a compact VerifyModel (not a full Model) for the verifier.
 */

export interface VerifyModel {
  name: string;
  sense: 'min' | 'max';
  nRows: number;
  nCols: number;
  // CSR matrix (rows = constraints, no objective row)
  Ap: number[];
  Ai: number[];
  Av: number[];
  // Row bounds
  rowLo: number[];
  rowHi: number[];
  // Column bounds
  colLo: number[];
  colHi: number[];
  // Objective
  c: number[];
  // Names
  rowNames: string[];
  colNames: string[];
  objConstant: number;
}

const INF = 1e30;
const NEG_INF = -1e30;

export function parseMPSVerify(text: string): VerifyModel {
  const lines = text.split(/\r?\n/);

  const rowByName = new Map<string, number>();
  const colByName = new Map<string, number>();
  const rowTypes: string[] = [];
  const rowNames: string[] = [];
  const colNames: string[] = [];
  let objRowName = '';
  let sense: 'min' | 'max' = 'min';

  // Entries: [rowIdx, colIdx, val]
  const entries: [number, number, number][] = [];
  // Objective entries: [colIdx, val]
  const objEntries: [number, number][] = [];

  const rowLo: number[] = [];
  const rowHi: number[] = [];
  const rhs: number[] = [];
  const colLo: number[] = [];
  const colHi: number[] = [];
  const c_obj: Map<number, number> = new Map();

  let section = '';
  let inInt = false;

  function ensureCol(name: string): number {
    let idx = colByName.get(name);
    if (idx === undefined) {
      idx = colNames.length;
      colNames.push(name);
      colByName.set(name, idx);
      colLo.push(0);
      colHi.push(INF);
    }
    return idx;
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line || line[0] === '*' || line[0] === '$') continue;

    const trimmed = line.trim();
    const firstChar = line[0];

    if (firstChar !== ' ' && firstChar !== '\t') {
      const kw = trimmed.split(/\s+/)[0].toUpperCase();
      switch (kw) {
        case 'ROWS':     section = 'ROWS'; continue;
        case 'COLUMNS':  section = 'COLUMNS'; continue;
        case 'RHS':      section = 'RHS'; continue;
        case 'RANGES':   section = 'RANGES'; continue;
        case 'BOUNDS':   section = 'BOUNDS'; continue;
        case 'OBJSENSE': section = 'OBJSENSE'; continue;
        case 'ENDATA':   section = 'END'; break;
        default: section = 'NONE'; continue;
      }
      break;
    }

    const tokens = trimmed.split(/\s+/);
    if (!tokens.length) continue;

    switch (section) {
      case 'OBJSENSE':
        sense = tokens[0].toLowerCase() === 'max' ? 'max' : 'min';
        break;

      case 'ROWS': {
        if (tokens.length < 2) break;
        const type = tokens[0].toUpperCase();
        const name = tokens[1];
        if (type === 'N') { if (!objRowName) objRowName = name; break; }
        const idx = rowNames.length;
        rowNames.push(name);
        rowByName.set(name, idx);
        rowTypes.push(type);
        rhs.push(0);
        rowLo.push(NEG_INF);
        rowHi.push(INF);
        break;
      }

      case 'COLUMNS': {
        if (tokens.length >= 3) {
          const marker = tokens[2].toUpperCase();
          if (marker === "'MARKER'" || marker === 'MARKER') {
            const tag = tokens[3]?.toUpperCase() ?? '';
            inInt = tag.includes('INTORG');
            break;
          }
        }
        if (tokens.length < 3) break;
        const colName = tokens[0];
        const colIdx = ensureCol(colName);
        let i = 1;
        while (i + 1 < tokens.length) {
          const rowName = tokens[i];
          const val = parseFloat(tokens[i + 1]);
          i += 2;
          if (isNaN(val)) continue;
          if (rowName === objRowName) {
            c_obj.set(colIdx, (c_obj.get(colIdx) ?? 0) + val);
          } else {
            const rIdx = rowByName.get(rowName);
            if (rIdx !== undefined) entries.push([rIdx, colIdx, val]);
          }
        }
        break;
      }

      case 'RHS': {
        if (tokens.length < 3) break;
        let i = 1;
        while (i + 1 < tokens.length) {
          const rowName = tokens[i];
          const val = parseFloat(tokens[i + 1]);
          i += 2;
          if (isNaN(val)) continue;
          const rIdx = rowByName.get(rowName);
          if (rIdx === undefined) continue;
          rhs[rIdx] = val;
          const type = rowTypes[rIdx];
          if (type === 'L') { rowLo[rIdx] = NEG_INF; rowHi[rIdx] = val; }
          else if (type === 'G') { rowLo[rIdx] = val; rowHi[rIdx] = INF; }
          else { rowLo[rIdx] = val; rowHi[rIdx] = val; }
        }
        break;
      }

      case 'RANGES': {
        if (tokens.length < 3) break;
        let i = 1;
        while (i + 1 < tokens.length) {
          const rowName = tokens[i];
          const range = parseFloat(tokens[i + 1]);
          i += 2;
          if (isNaN(range)) continue;
          const rIdx = rowByName.get(rowName);
          if (rIdx === undefined) continue;
          const absR = Math.abs(range);
          const type = rowTypes[rIdx];
          if (type === 'L') { rowLo[rIdx] = rowHi[rIdx] - absR; }
          else if (type === 'G') { rowHi[rIdx] = rowLo[rIdx] + absR; }
          else if (type === 'E') {
            if (range >= 0) { rowHi[rIdx] = rowLo[rIdx] + range; }
            else { const old = rowLo[rIdx]; rowLo[rIdx] = old + range; rowHi[rIdx] = old; }
          }
        }
        break;
      }

      case 'BOUNDS': {
        if (tokens.length < 3) break;
        const bType = tokens[0].toUpperCase();
        const colName = tokens[2];
        const colIdx = ensureCol(colName);
        const val = tokens[3] ? parseFloat(tokens[3]) : 0;
        switch (bType) {
          case 'LO': case 'LI': colLo[colIdx] = val; break;
          case 'UP': case 'UI': colHi[colIdx] = val; break;
          case 'FX': colLo[colIdx] = val; colHi[colIdx] = val; break;
          case 'FR': colLo[colIdx] = NEG_INF; colHi[colIdx] = INF; break;
          case 'MI': colLo[colIdx] = NEG_INF; break;
          case 'PL': colHi[colIdx] = INF; break;
          case 'BV': colLo[colIdx] = 0; colHi[colIdx] = 1; break;
        }
        break;
      }
    }
  }

  const nRows = rowNames.length;
  const nCols = colNames.length;

  // Build CSR from entries (merge duplicates)
  const rowEntries: Map<number, number>[] = Array.from({ length: nRows }, () => new Map());
  for (const [r, c, v] of entries) {
    rowEntries[r].set(c, (rowEntries[r].get(c) ?? 0) + v);
  }
  const Ap: number[] = [0];
  const Ai: number[] = [];
  const Av: number[] = [];
  for (let i = 0; i < nRows; i++) {
    for (const [c, v] of rowEntries[i]) {
      if (v !== 0) { Ai.push(c); Av.push(v); }
    }
    Ap.push(Ai.length);
  }

  const c_arr = new Array(nCols).fill(0);
  for (const [j, v] of c_obj) c_arr[j] = v;

  return {
    name: 'unknown',
    sense,
    nRows,
    nCols,
    Ap, Ai, Av,
    rowLo, rowHi,
    colLo, colHi,
    c: c_arr,
    rowNames,
    colNames,
    objConstant: 0,
  };
}
