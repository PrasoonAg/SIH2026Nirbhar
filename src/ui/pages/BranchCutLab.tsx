import React from 'react';
import { Construction } from 'lucide-react';

/**
 * Branch-and-Cut Lab
 * Certified branch-and-cut with live tree, cut inspector, branching and node selection controls, and brute-force cross-check. Features F11–F14.
 * Implemented in: Phase 3
 */
export default function BranchCutLab() {
  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
        <h1 className="text-page">Branch-and-Cut Lab</h1>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 'var(--space-6)', maxWidth: 600 }}>
        Certified branch-and-cut with live tree, cut inspector, branching and node selection controls, and brute-force cross-check. Features F11–F14.
      </p>
      <div className="well" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', color: 'var(--text-muted)' }}>
        <Construction size={16} />
        <span style={{ fontSize: 13 }}>
          <strong style={{ color: 'var(--text)' }}>Phase 3</strong> — implementation pending.
          The solver engines, UI components and acceptance tests for this page will be built in the scheduled phase.
        </span>
      </div>
    </div>
  );
}
