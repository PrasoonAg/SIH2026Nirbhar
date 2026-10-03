#!/usr/bin/env node
/**
 * check-imports.mjs
 * Sovereignty + isolation enforcement for NIRBHAR Showcase.
 *
 * Rules:
 *   1. src/solver/** must not import any third-party numeric/solver package.
 *      Forbidden: mathjs, glpk.js, highs-js, javascript-lp-solver, numeric,
 *                 ml-matrix, ndarray, linear-solve, lp-solve, glpk, simplex-js
 *   2. src/verify/** must not import anything from src/solver/**
 *   3. src/solver/** must not import anything from src/verify/**
 *   4. src/bench/** may import highs lazily (only highsBaseline.ts) — all others banned
 *
 * Exit code: 0 = clean, 1 = violations found.
 * Writes results to dist/check-imports.json for the Sovereignty panel to read.
 */

import { readFileSync, readdirSync, statSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, relative, extname } from 'path';

const ROOT = process.cwd();
const SRC  = join(ROOT, 'src');

// Third-party numeric/solver packages forbidden in solver + verify
const FORBIDDEN_PACKAGES = [
  'mathjs',
  'glpk.js',
  'glpk',
  'highs-js',
  'highs',
  'javascript-lp-solver',
  'numeric',
  'numeric.js',
  'numericjs',
  'ml-matrix',
  'ndarray',
  'linear-solve',
  'lp-solve',
  'simplex-js',
  'ml-optimization',
  'fmin',
  'optimization-js',
];

// Regex: import ... from '...' or require('...')
const IMPORT_RE = /(?:import\s+(?:[^'"]*from\s+)?|require\s*\(\s*)['"]([^'"]+)['"]/g;

/** Collect all .ts / .tsx files under a directory recursively */
function collectFiles(dir) {
  const results = [];
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      results.push(...collectFiles(full));
    } else if (['.ts', '.tsx'].includes(extname(full))) {
      results.push(full);
    }
  }
  return results;
}

/** Extract all import/require specifiers from file content */
function extractImports(content) {
  const specs = [];
  for (const m of content.matchAll(IMPORT_RE)) {
    specs.push(m[1]);
  }
  return specs;
}

/** Check if a specifier is a third-party package (not relative, not Node built-in) */
function isThirdParty(spec) {
  return !spec.startsWith('.') && !spec.startsWith('/') && !spec.startsWith('@/') && !spec.startsWith('node:');
}

const violations = [];
const scannedFiles = [];

const solverDir  = join(SRC, 'solver');
const verifyDir  = join(SRC, 'verify');
const benchDir   = join(SRC, 'bench');

const solverFiles = collectFiles(solverDir);
const verifyFiles = collectFiles(verifyDir);

// === Rule 1: solver/* — no forbidden packages, no verify imports ===
for (const file of solverFiles) {
  const content = readFileSync(file, 'utf8');
  const imports = extractImports(content);
  const rel     = relative(ROOT, file).replace(/\\/g, '/');
  scannedFiles.push(rel);

  for (const spec of imports) {
    // Forbidden third-party
    if (isThirdParty(spec)) {
      const pkg = spec.split('/')[0].replace(/^@[^/]+\/[^/]+/, (m) => m); // scoped pkg
      const banned = FORBIDDEN_PACKAGES.find((f) => spec === f || spec.startsWith(f + '/'));
      if (banned) {
        violations.push({
          file: rel,
          rule: 'solver-no-forbidden-package',
          import: spec,
          detail: `Forbidden numeric/solver package "${banned}" in src/solver`,
        });
      }
    }
    // No imports from verify
    if (spec.includes('verify') || spec.includes('../verify') || spec.includes('src/verify')) {
      violations.push({
        file: rel,
        rule: 'solver-no-verify-import',
        import: spec,
        detail: 'src/solver must not import from src/verify',
      });
    }
  }
}

// === Rule 2: verify/* — no imports from solver/*, no forbidden packages ===
for (const file of verifyFiles) {
  const content = readFileSync(file, 'utf8');
  const imports = extractImports(content);
  const rel     = relative(ROOT, file).replace(/\\/g, '/');
  scannedFiles.push(rel);

  for (const spec of imports) {
    // No imports from solver
    if (
      spec.includes('/solver') ||
      spec.includes('../solver') ||
      spec.startsWith('solver/') ||
      spec === 'solver'
    ) {
      violations.push({
        file: rel,
        rule: 'verify-no-solver-import',
        import: spec,
        detail: 'src/verify must not import from src/solver',
      });
    }
    // Also ban third-party solver packages in verify
    if (isThirdParty(spec)) {
      const banned = FORBIDDEN_PACKAGES.find((f) => spec === f || spec.startsWith(f + '/'));
      if (banned) {
        violations.push({
          file: rel,
          rule: 'verify-no-forbidden-package',
          import: spec,
          detail: `Forbidden package "${banned}" in src/verify`,
        });
      }
    }
  }
}

// === Rule 3: bench/* — only highsBaseline.ts may reference highs ===
const benchFiles = collectFiles(benchDir);
for (const file of benchFiles) {
  const content = readFileSync(file, 'utf8');
  const imports = extractImports(content);
  const rel     = relative(ROOT, file).replace(/\\/g, '/');
  scannedFiles.push(rel);

  const isHighsFile = rel.includes('highsBaseline');
  for (const spec of imports) {
    if (!isHighsFile && (spec === 'highs' || spec.startsWith('highs/'))) {
      violations.push({
        file: rel,
        rule: 'bench-highs-only-in-baseline',
        import: spec,
        detail: 'Only highsBaseline.ts may import highs in src/bench',
      });
    }
  }
}

// === Output ===
const result = {
  timestamp: new Date().toISOString(),
  scannedFiles: scannedFiles.length,
  files: scannedFiles,
  violations,
  passed: violations.length === 0,
  rules: [
    { id: 'solver-no-forbidden-package', desc: 'src/solver imports no forbidden numeric/solver package' },
    { id: 'solver-no-verify-import',     desc: 'src/solver does not import from src/verify' },
    { id: 'verify-no-solver-import',     desc: 'src/verify does not import from src/solver' },
    { id: 'verify-no-forbidden-package', desc: 'src/verify imports no forbidden numeric/solver package' },
    { id: 'bench-highs-only-in-baseline',desc: 'Only highsBaseline.ts in src/bench may load highs' },
  ],
};

// Write to dist for Sovereignty panel
try {
  if (!existsSync(join(ROOT, 'dist'))) mkdirSync(join(ROOT, 'dist'));
  writeFileSync(join(ROOT, 'dist', 'check-imports.json'), JSON.stringify(result, null, 2));
} catch {}

// Also write to public for dev server access
try {
  writeFileSync(join(ROOT, 'public', 'check-imports.json'), JSON.stringify(result, null, 2));
} catch {}

if (violations.length > 0) {
  console.error('\n❌ check-imports FAILED — sovereignty violations found:\n');
  for (const v of violations) {
    console.error(`  [${v.rule}] ${v.file}`);
    console.error(`    import: "${v.import}"`);
    console.error(`    ${v.detail}\n`);
  }
  console.error(`Total violations: ${violations.length}`);
  process.exit(1);
} else {
  const fileCount = scannedFiles.length;
  console.log(`\n✅ check-imports PASSED — ${fileCount} file${fileCount !== 1 ? 's' : ''} scanned, 0 violations.\n`);
  console.log('Sovereignty rules enforced:');
  for (const r of result.rules) {
    console.log(`  ✓ ${r.desc}`);
  }
  console.log();
  process.exit(0);
}
