import React from 'react';
import { Construction } from 'lucide-react';

/**
 * Benchmarks
 * Netlib LP table (F19), MILP/QP/MIQP tables (F20), crossover chart, reliability table, known-optimum generators (F21–F22). Features F19–F22.
 * Implemented in: Phase 4
 */
export default function Benchmarks() {
  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
        <h1 className="text-page">Benchmarks</h1>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 'var(--space-6)', maxWidth: 600 }}>
        Netlib LP table (F19), MILP/QP/MIQP tables (F20), crossover chart, reliability table, known-optimum generators (F21–F22). Features F19–F22.
      </p>
      <div className="well" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', color: 'var(--text-muted)' }}>
        <Construction size={16} />
        <span style={{ fontSize: 13 }}>
          <strong style={{ color: 'var(--text)' }}>Phase 4</strong> — implementation pending.
          The solver engines, UI components and acceptance tests for this page will be built in the scheduled phase.
        </span>
      </div>
    </div>
  );
}
