/**
 * NIRBHAR Certificate Explanation
 * Generates human-readable, plain-language explanations of certificates.
 * Used by the Solve Studio "Explain" tab and the Certificate Viewer.
 */

import type { Certificate, CertLP, CertLPInfeasible, CertLPUnbounded, CertMILP } from './schema.js';

export interface ExplainSection {
  title: string;
  body: string;
  kind: 'info' | 'success' | 'warning' | 'error';
}

export interface ExplainReport {
  headline: string;
  summary: string;
  sections: ExplainSection[];
}

/**
 * Generate a full plain-language explanation report from a certificate.
 */
export function explainCertificate(cert: Certificate): ExplainReport {
  switch (cert.kind) {
    case 'LP_OPTIMAL':    return explainLP(cert);
    case 'LP_INFEASIBLE': return explainInfeasible(cert);
    case 'LP_UNBOUNDED':  return explainUnbounded(cert);
    case 'MILP_OPTIMAL':  return explainMILP(cert);
    default:
      return {
        headline: 'Unknown certificate type',
        summary: 'The certificate kind is not recognised.',
        sections: [],
      };
  }
}

// ─── LP Optimal ──────────────────────────────────────────────────────────────

function explainLP(cert: CertLP): ExplainReport {
  const gapPct = (cert.gap * 100).toFixed(6);
  const isExact = cert.gap < 1e-8;

  const headline = isExact
    ? `✓ Optimal solution found — objective = ${fmt(cert.objectiveUB)}`
    : `≈ Near-optimal solution — objective ≈ ${fmt(cert.objectiveUB)} (gap ${gapPct}%)`;

  const summary =
    `The solver proved that no feasible solution can have a cost below ` +
    `${fmt(cert.lowerBound)} (the safe lower bound LB(y)). ` +
    `The primal solution achieves cost ${fmt(cert.objectiveUB)}, ` +
    `so the optimality gap is ${gapPct}%.`;

  const sections: ExplainSection[] = [];

  // ── Objective ──────────────────────────────────────────────────────────────
  sections.push({
    title: 'Objective',
    kind: 'success',
    body:
      `Primal objective (upper bound):  ${fmt(cert.objectiveUB)}\n` +
      `Safe lower bound LB(y):          ${fmt(cert.lowerBound)}\n` +
      `Optimality gap:                  ${gapPct}%\n\n` +
      (isExact
        ? 'The gap is within tolerance — this is a certified optimal solution.'
        : 'The gap is above machine precision — labelled CERTIFIED_APPROXIMATE.'),
  });

  // ── Dual proof ─────────────────────────────────────────────────────────────
  sections.push({
    title: 'Dual Proof (LB(y) derivation)',
    kind: 'info',
    body:
      `The dual vector y (shadow prices) satisfies:\n` +
      `  LB(y) = bᵀy  ≤  min c·x  (weak duality)\n\n` +
      `Strong duality confirms LB(y) = objective at optimality.\n` +
      `The top 3 shadow prices (binding constraints):\n` +
      topValues(cert.y, 3, 'row').join('\n'),
  });

  // ── Reduced costs ─────────────────────────────────────────────────────────
  const nonzeroRC = cert.rc.filter(v => Math.abs(v) > 1e-6);
  sections.push({
    title: 'Reduced Costs',
    kind: 'info',
    body:
      `${nonzeroRC.length} of ${cert.rc.length} variables have non-zero reduced cost.\n` +
      `A non-zero reduced cost means the variable is non-basic (at a bound).\n` +
      `Top magnitudes:\n` +
      topValues(cert.rc, 3, 'var').join('\n'),
  });

  // ── Residuals ────────────────────────────────────────────────────────────
  const { residuals } = cert;
  const feasible = residuals.maxRowViol < 1e-6 && residuals.maxBoundViol < 1e-6;
  sections.push({
    title: 'Constraint Satisfaction',
    kind: feasible ? 'success' : 'warning',
    body:
      `Max row violation:   ${residuals.maxRowViol.toExponential(3)}\n` +
      `Max bound violation: ${residuals.maxBoundViol.toExponential(3)}\n` +
      `Max dual violation:  ${residuals.maxDualViol.toExponential(3)}\n\n` +
      (feasible ? 'All constraints satisfied to within tolerance.' : 'Warning: constraint violation above 1e-6.'),
  });

  // ── Engine / timing ──────────────────────────────────────────────────────
  sections.push({
    title: 'Solve Details',
    kind: 'info',
    body:
      `Engine:        ${cert.engine}\n` +
      `Iterations:    ${cert.iterations}\n` +
      `Wall time:     ${cert.solveTimeMs.toFixed(1)} ms\n` +
      (cert.escalations.length > 0 ? `Escalations:   ${cert.escalations.join('; ')}` : ''),
  });

  if (cert.explanationHints.length > 0) {
    sections.push({
      title: 'Solver Notes',
      kind: 'info',
      body: cert.explanationHints.join('\n'),
    });
  }

  return { headline, summary, sections };
}

// ─── LP Infeasible ───────────────────────────────────────────────────────────

function explainInfeasible(cert: CertLPInfeasible): ExplainReport {
  const headline = '✗ Problem is infeasible — no feasible solution exists';

  const summary =
    'The solver proved that the constraints are contradictory: ' +
    'no assignment of variable values can simultaneously satisfy all constraints and bounds.';

  const sections: ExplainSection[] = [
    {
      title: 'What Infeasibility Means',
      kind: 'error',
      body:
        'Infeasibility means the constraints cannot all be satisfied at once.\n' +
        'Common causes:\n' +
        '  • Conflicting equality constraints\n' +
        '  • Right-hand sides that are mutually inconsistent\n' +
        '  • Variable bounds tighter than constraints allow',
    },
  ];

  if (cert.farkasRay && cert.farkasCheck) {
    sections.push({
      title: 'Farkas Certificate (Dual Ray)',
      kind: 'warning',
      body:
        `A Farkas ray y has been computed:\n` +
        `  Aᵀy ≤ 0  but  bᵀy > 0  — contradiction with feasibility\n\n` +
        `Verification values:\n` +
        `  max(Aᵀy)+:  ${cert.farkasCheck.AtY_maxPositive.toExponential(3)}  (should be ≤ 0)\n` +
        `  bᵀy:        ${cert.farkasCheck.bTy.toExponential(3)}  (should be > 0)\n\n` +
        'This certificate can be independently verified without re-solving.',
    });
  }

  if (cert.iisRows && cert.iisRows.length > 0) {
    sections.push({
      title: 'Irreducible Infeasible Subset (IIS)',
      kind: 'error',
      body:
        `The following ${cert.iisRows.length} constraints form a minimal infeasible set:\n` +
        cert.iisRows.map(r => `  • ${r}`).join('\n') +
        '\nRemoving any one constraint would make the subsystem feasible.',
    });
  }

  sections.push({
    title: 'Solve Details',
    kind: 'info',
    body: `Engine: ${cert.engine} | Iterations: ${cert.iterations} | Time: ${cert.solveTimeMs.toFixed(1)} ms`,
  });

  return { headline, summary, sections };
}

// ─── LP Unbounded ────────────────────────────────────────────────────────────

function explainUnbounded(cert: CertLPUnbounded): ExplainReport {
  const headline = '∞ Problem is unbounded — objective has no finite minimum';

  const summary =
    'The solver found a direction in which the objective can decrease without limit ' +
    'while remaining feasible. This typically means a missing lower bound on a variable.';

  const sections: ExplainSection[] = [
    {
      title: 'What Unboundedness Means',
      kind: 'error',
      body:
        'The problem has feasible solutions, but the objective can be made arbitrarily small.\n' +
        'Common causes:\n' +
        '  • Missing variable lower bound (variable should have lb ≥ 0)\n' +
        '  • Incorrect objective coefficient sign\n' +
        '  • Free variable that the constraints do not bound',
    },
  ];

  if (cert.recessionDir && cert.recessionCheck) {
    sections.push({
      title: 'Recession Direction (Certificate)',
      kind: 'warning',
      body:
        `A recession direction d has been computed:\n` +
        `  Ad = 0  (feasibility preserved)\n` +
        `  cᵀd < 0  (objective decreases)\n\n` +
        `Verification:\n` +
        `  cᵀd:   ${cert.recessionCheck.cTd.toExponential(3)}  (should be < 0)\n` +
        `  max|Ad|: ${cert.recessionCheck.AdMax.toExponential(3)}  (should be ≈ 0)`,
    });
  }

  sections.push({
    title: 'Solve Details',
    kind: 'info',
    body: `Engine: ${cert.engine} | Iterations: ${cert.iterations} | Time: ${cert.solveTimeMs.toFixed(1)} ms`,
  });

  return { headline, summary, sections };
}

// ─── MILP Optimal ────────────────────────────────────────────────────────────

function explainMILP(cert: CertMILP): ExplainReport {
  const gapPct = (cert.gap * 100).toFixed(4);
  const headline = `✓ MILP optimal — objective = ${fmt(cert.objectiveUB)} (gap ${gapPct}%)`;

  const summary =
    `Branch-and-cut proved optimality. Best integer solution: ${fmt(cert.objectiveUB)}. ` +
    `Dual bound (LP relaxation lower bound across B&C tree): ${fmt(cert.objectiveLB)}.`;

  const sections: ExplainSection[] = [
    {
      title: 'Branch-and-Cut Statistics',
      kind: 'info',
      body:
        `Nodes explored:  ${cert.bcStats.nodes}\n` +
        `Cut rounds:      ${cert.bcStats.cutRounds}\n` +
        `Cuts added:      ${cert.bcStats.cutsAdded}\n` +
        (cert.bcStats.branchingVar ? `Most branched on: ${cert.bcStats.branchingVar}` : ''),
    },
    {
      title: 'Bounds',
      kind: 'success',
      body:
        `Best integer objective (UB): ${fmt(cert.objectiveUB)}\n` +
        `LP relaxation dual bound (LB): ${fmt(cert.objectiveLB)}\n` +
        `Optimality gap: ${gapPct}%`,
    },
    {
      title: 'Solve Details',
      kind: 'info',
      body: `Engine: ${cert.engine} | Time: ${cert.solveTimeMs.toFixed(1)} ms`,
    },
  ];

  return { headline, summary, sections };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(v: number): string {
  if (!isFinite(v)) return v > 0 ? '+∞' : '-∞';
  return v.toPrecision(10).replace(/\.?0+$/, '');
}

function topValues(arr: number[], k: number, prefix: string): string[] {
  return arr
    .map((v, i) => ({ i, v }))
    .filter(e => Math.abs(e.v) > 1e-8)
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
    .slice(0, k)
    .map(e => `  ${prefix}[${e.i}] = ${fmt(e.v)}`);
}
