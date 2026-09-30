/**
 * Phase 0 smoke test — verifies the manifest loads and has the expected structure.
 * Real solver tests are added in Phase 1.
 */
import { describe, it, expect } from 'vitest';
import manifest from '../public/samples/manifest.json';

describe('Sample manifest (Phase 0)', () => {
  it('has a models array', () => {
    expect(Array.isArray(manifest.models)).toBe(true);
  });

  it('has all required Netlib tune-set entries', () => {
    const names = manifest.models.map((m: { name: string }) => m.name);
    expect(names).toContain('afiro');
    expect(names).toContain('sc50a');
    expect(names).toContain('sc50b');
    expect(names).toContain('sc105');
    expect(names).toContain('kb2');
  });

  it('all models have required fields', () => {
    for (const m of manifest.models) {
      expect(typeof m.name).toBe('string');
      expect(typeof m.class).toBe('string');
      expect(typeof m.referenceObjective).toBe('number');
      expect(['tune', 'report', 'stress']).toContain(m.split);
    }
  });

  it('has a generated array', () => {
    expect(Array.isArray(manifest.generated)).toBe(true);
  });

  it('afiro reference objective is correct', () => {
    const afiro = manifest.models.find((m: { name: string }) => m.name === 'afiro');
    expect(afiro).toBeDefined();
    expect(afiro!.referenceObjective).toBeCloseTo(-464.7531428571, 4);
  });
});
