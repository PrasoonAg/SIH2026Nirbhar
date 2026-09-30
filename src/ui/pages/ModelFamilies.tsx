import React from 'react';
import { Construction } from 'lucide-react';

/**
 * Model Families
 * Five synthetic model families: Refinery, Lot-Sizing, Transport, Unit Commitment, Supply Chain. Each with generator and Solve button. Feature F23.
 * Implemented in: Phase 6
 */
export default function ModelFamilies() {
  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
        <h1 className="text-page">Model Families</h1>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 'var(--space-6)', maxWidth: 600 }}>
        Five synthetic model families: Refinery, Lot-Sizing, Transport, Unit Commitment, Supply Chain. Each with generator and Solve button. Feature F23.
      </p>
      <div className="well" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', color: 'var(--text-muted)' }}>
        <Construction size={16} />
        <span style={{ fontSize: 13 }}>
          <strong style={{ color: 'var(--text)' }}>Phase 6</strong> — implementation pending.
          The solver engines, UI components and acceptance tests for this page will be built in the scheduled phase.
        </span>
      </div>
    </div>
  );
}
