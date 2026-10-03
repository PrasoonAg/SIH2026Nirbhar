/**
 * NIRBHAR — Independent Verifier Workbench (Phase 5)
 * 
 * Demonstrates:
 *   - Sovereign, isolated independent verification (§6.13)
 *   - Re-reads original model text using internal minimal parser (mpsMin.ts)
 *   - Float64 and BigInt rational exact verification paths
 *   - Adversarial corruption test bench (detects falsified objectives, invalid dual bounds, violated rows)
 */

import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, ShieldAlert, CheckCircle2, XCircle, AlertTriangle,
  Play, RefreshCw, FileText, Bug, Zap, Layers, Lock, Cpu, Eye
} from 'lucide-react';

import { parseMPSMin } from '../../verify/mpsMin';
import { verifyCertificate, type VerifyOptions } from '../../verify/verify';
import { ratFromFloat } from '../../verify/exact';
import type { Certificate, VerifyResult, VerifyCheck } from '../../verify/certTypes';
import { parseMPS } from '../../solver/io/mps';
import { dualSimplexSolve } from '../../solver/lp/dualSimplex';
import { buildCertLP } from '../../solver/certificate/builder';

const SAMPLE_AFIRO_MPS = `NAME          AFIRO
ROWS
 E  R09
 E  R10
 L  X05
 L  X21
 E  R12
 E  R13
 L  X17
 L  X18
 L  X19
 L  X20
 E  R19
 E  R20
 L  X27
 L  X44
 E  R22
 E  R23
 L  X40
 L  X41
 L  X42
 L  X43
 L  X45
 L  X46
 L  X47
 L  X48
 L  X49
 L  X50
 L  X51
 N  COST
COLUMNS
    X01       X48               .301   R09                -1.
    X01       R10              -1.06   X05                 1.
    X02       X21                -1.   R09                 1.
    X02       COST               -.4
    X03       X46                -1.   R09                 1.
    X04       X50                 1.   R10                 1.
    X06       X49               .301   R12                -1.
    X06       R13              -1.06   X17                 1.
    X07       X49               .313   R12                -1.
    X07       R13              -1.06   X18                 1.
    X08       X49               .313   R12                -1.
    X08       R13               -.96   X19                 1.
    X09       X49               .326   R12                -1.
    X09       R13               -.86   X20                 1.
    X10       X45              2.364   X17                -1.
    X11       X45              2.386   X18                -1.
    X12       X45              2.408   X19                -1.
    X13       X45              2.429   X20                -1.
    X14       X21                1.4   R12                 1.
    X14       COST              -.32
    X15       X47                -1.   R12                 1.
    X16       X51                 1.   R13                 1.
    X22       X46               .109   R19                -1.
    X22       R20               -.43   X27                 1.
    X23       X44                -1.   R19                 1.
    X23       COST               -.6
    X24       X48                -1.   R19                 1.
    X25       X45                -1.   R19                 1.
    X26       X50                 1.   R20                 1.
    X28       X47               .109   R22               -.43
    X28       R23                 1.   X40                 1.
    X29       X47               .108   R22               -.43
    X29       R23                 1.   X41                 1.
    X30       X47               .108   R22               -.39
    X30       R23                 1.   X42                 1.
    X31       X47               .107   R22               -.37
    X31       R23                 1.   X43                 1.
    X32       X45              2.191   X40                -1.
    X33       X45              2.219   X41                -1.
    X34       X45              2.249   X42                -1.
    X35       X45              2.279   X43                -1.
    X36       X44                1.4   R23                -1.
    X36       COST              -.48
    X37       X49                -1.   R23                 1.
    X38       X51                 1.   R22                 1.
    X39       R23                 1.   COST               10.
RHS
    B         X50               310.   X51               300.
    B         X05                80.   X17                80.
    B         X27               500.   R23                44.
    B         X40               500.
ENDATA`;

export default function Verifier() {
  const [mpsText, setMpsText] = useState<string>(SAMPLE_AFIRO_MPS);
  const [cert, setCert] = useState<Certificate | null>(null);
  const [verifyMode, setVerifyMode] = useState<'float64' | 'bigint-rational'>('float64');
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
  const [tamperType, setTamperType] = useState<'none' | 'objective' | 'variable' | 'lowerbound'>('none');
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  // Generate baseline certificate on mount
  useEffect(() => {
    generateCertificate('none');
  }, []);

  const generateCertificate = (tamper: 'none' | 'objective' | 'variable' | 'lowerbound') => {
    try {
      const { model } = parseMPS(mpsText);
      const res = dualSimplexSolve(model);
      const c = buildCertLP(model, res, 'dual-simplex') as any;

      if (tamper === 'objective') {
        c.objectiveUB -= 50.0; // artificially claim a better objective
      } else if (tamper === 'variable') {
        c.x[0] += 15.0; // corrupt primal variable to violate constraints
      } else if (tamper === 'lowerbound') {
        c.lowerBound = c.objectiveUB + 25.0; // claim invalid lower bound > UB
      }

      setCert(c);
      setTamperType(tamper);

      // Verify
      const vModel = parseMPSMin(mpsText);
      const vr = verifyCertificate(c, vModel, { mode: verifyMode });
      setVerifyResult(vr);
    } catch (err) {
      console.error('Verification run error:', err);
    }
  };

  const handleRunVerify = () => {
    if (!cert) return;
    setIsVerifying(true);
    setTimeout(() => {
      try {
        const vModel = parseMPSMin(mpsText);
        const vr = verifyCertificate(cert, vModel, { mode: verifyMode });
        setVerifyResult(vr);
      } finally {
        setIsVerifying(false);
      }
    }, 40);
  };

  return (
    <div className="page" style={{ paddingBottom: 'var(--space-10)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(99, 102, 241, 0.15))',
            padding: 10,
            borderRadius: 'var(--radius-lg)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ShieldCheck size={24} style={{ color: 'var(--success, #10b981)' }} />
          </div>
          <div>
            <h1 className="text-page" style={{ margin: 0, fontSize: 24 }}>Independent Verifier Workbench</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '2px 0 0 0' }}>
              Phase 5 • Sovereign Isolated Audit Core (§6.13) • Float64 & BigInt Exact Rational Mode
            </p>
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleRunVerify}
          disabled={isVerifying}
          style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
        >
          {isVerifying ? <RefreshCw size={16} className="spin" /> : <Play size={16} fill="currentColor" />}
          <span>Re-Verify Certificate</span>
        </button>
      </div>

      {/* Verification Outcome Banner */}
      <div style={{
        background: verifyResult?.pass
          ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(16, 185, 129, 0.04))'
          : 'linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(239, 68, 68, 0.04))',
        border: verifyResult?.pass ? '1px solid var(--success, #10b981)' : '1px solid var(--danger, #ef4444)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-4)',
        marginBottom: 'var(--space-5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {verifyResult?.pass ? (
            <CheckCircle2 size={26} style={{ color: 'var(--success, #10b981)' }} />
          ) : (
            <XCircle size={26} style={{ color: 'var(--danger, #ef4444)' }} />
          )}
          <div>
            <div style={{
              fontWeight: 800,
              fontSize: 16,
              color: verifyResult?.pass ? 'var(--success, #10b981)' : 'var(--danger, #ef4444)',
              letterSpacing: '0.02em'
            }}>
              {verifyResult?.pass ? 'VERIFICATION PASSED — ZERO-TRUST MATHEMATICALLY CERTIFIED' : 'VERIFICATION REJECTED — INTEGRITY VIOLATION DETECTED'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {verifyResult?.pass
                ? `All primal feasibility, dual feasibility, safe lower bounds, and objective values verified independently against original MPS.`
                : `Verifier detected deliberate corruption or falsification: ${verifyResult?.checks.filter(c => !c.pass).map(c => c.name).join(', ')} failed.`}
            </div>
          </div>
        </div>

        <span className="badge" style={{
          background: verifyResult?.pass ? 'var(--success, #10b981)' : 'var(--danger, #ef4444)',
          color: '#fff',
          padding: '6px 14px',
          fontWeight: 700,
          fontSize: 12
        }}>
          {verifyResult?.pass ? 'AUDIT VERIFIED' : 'TAMPER BLOCKED'}
        </span>
      </div>

      {/* Main Grid: Control & Adversarial Sandbox + Verification Checks */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 'var(--space-5)' }}>
        
        {/* Left Column: Settings & Adversarial Sandbox */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Mode Card */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ margin: '0 0 var(--space-3) 0', fontSize: 14, fontWeight: 600 }}>Verifier Mode</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                cursor: 'pointer',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                border: verifyMode === 'float64' ? '1px solid var(--primary)' : '1px solid var(--border)',
                background: verifyMode === 'float64' ? 'rgba(99, 102, 241, 0.08)' : 'transparent'
              }}>
                <input
                  type="radio"
                  name="vmode"
                  checked={verifyMode === 'float64'}
                  onChange={() => setVerifyMode('float64')}
                />
                <div>
                  <div style={{ fontWeight: 600 }}>Float64 (Standard)</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Tolerance ≤ 1e-6 relative</div>
                </div>
              </label>

              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                cursor: 'pointer',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                border: verifyMode === 'bigint-rational' ? '1px solid var(--primary)' : '1px solid var(--border)',
                background: verifyMode === 'bigint-rational' ? 'rgba(99, 102, 241, 0.08)' : 'transparent'
              }}>
                <input
                  type="radio"
                  name="vmode"
                  checked={verifyMode === 'bigint-rational'}
                  onChange={() => setVerifyMode('bigint-rational')}
                />
                <div>
                  <div style={{ fontWeight: 600 }}>BigInt Rational (Exact)</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Exact p/q lossless arithmetic</div>
                </div>
              </label>
            </div>
          </div>

          {/* Adversarial Corruption Sandbox */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 'var(--space-2)' }}>
              <Bug size={16} style={{ color: 'var(--danger, #ef4444)' }} />
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Adversarial Sandbox</h3>
            </div>
            <p style={{ margin: '0 0 var(--space-3) 0', fontSize: 12, color: 'var(--text-muted)' }}>
              Deliberately tamper with solver output to prove the independent verifier rejects falsified proofs:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <button
                className="btn btn-secondary"
                onClick={() => generateCertificate('none')}
                style={{
                  fontSize: 12,
                  justifyContent: 'flex-start',
                  fontWeight: tamperType === 'none' ? 700 : 400,
                  borderColor: tamperType === 'none' ? 'var(--success, #10b981)' : undefined
                }}
              >
                <CheckCircle2 size={14} style={{ color: 'var(--success, #10b981)' }} />
                <span>Reset to Legitimate Proof</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={() => generateCertificate('objective')}
                style={{
                  fontSize: 12,
                  justifyContent: 'flex-start',
                  fontWeight: tamperType === 'objective' ? 700 : 400,
                  borderColor: tamperType === 'objective' ? 'var(--danger, #ef4444)' : undefined
                }}
              >
                <AlertTriangle size={14} style={{ color: 'var(--warning, #f59e0b)' }} />
                <span>Forge Claimed Objective (-50.0)</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={() => generateCertificate('variable')}
                style={{
                  fontSize: 12,
                  justifyContent: 'flex-start',
                  fontWeight: tamperType === 'variable' ? 700 : 400,
                  borderColor: tamperType === 'variable' ? 'var(--danger, #ef4444)' : undefined
                }}
              >
                <AlertTriangle size={14} style={{ color: 'var(--danger, #ef4444)' }} />
                <span>Corrupt Primal Variable (+15.0)</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={() => generateCertificate('lowerbound')}
                style={{
                  fontSize: 12,
                  justifyContent: 'flex-start',
                  fontWeight: tamperType === 'lowerbound' ? 700 : 400,
                  borderColor: tamperType === 'lowerbound' ? 'var(--danger, #ef4444)' : undefined
                }}
              >
                <AlertTriangle size={14} style={{ color: 'var(--danger, #ef4444)' }} />
                <span>Forge Invalid Dual Bound</span>
              </button>
            </div>
          </div>

          {/* Sovereignty Isolation Note */}
          <div className="card" style={{ padding: 'var(--space-4)', fontSize: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontWeight: 600 }}>
              <Lock size={14} style={{ color: 'var(--primary)' }} />
              <span>Architectural Isolation Rule</span>
            </div>
            <p style={{ margin: 0, color: 'var(--text-muted)', lineHeight: 1.5 }}>
              The verifier package in <code>src/verify</code> imports zero code from <code>src/solver</code>.
              It uses its own isolated minimal MPS parser (<code>mpsMin.ts</code>) and re-evaluates all row activities from raw file data.
            </p>
          </div>
        </div>

        {/* Right Column: Verification Checks Table & Audit Report */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Checks Table */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ margin: '0 0 var(--space-3) 0', fontSize: 14, fontWeight: 600 }}>
              Independent Mathematical Audit Checks (§6.13)
            </h3>

            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: 'var(--surface-muted, rgba(255,255,255,0.03))', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '8px 12px' }}>Check Name</th>
                    <th style={{ padding: '8px 12px' }}>Verification Criterion</th>
                    <th style={{ padding: '8px 12px' }}>Measured Value</th>
                    <th style={{ padding: '8px 12px' }}>Tolerance Threshold</th>
                    <th style={{ padding: '8px 12px' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {verifyResult?.checks.map((check, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '8px 12px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                        {check.name}
                      </td>
                      <td style={{ padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11 }}>
                        {check.name === 'ROW_FEAS' && 'max |Ax - b| / (1 + |b|) ≤ tol'}
                        {check.name === 'BOUND_FEAS' && 'all l_j ≤ x_j ≤ u_j satisfied'}
                        {check.name === 'DUAL_FEAS' && 'reduced cost signs valid for nonbasics'}
                        {check.name === 'OBJ_MATCH' && '|cᵀx - claimed_UB| ≤ tol'}
                        {check.name === 'LB_VALID' && 'lowerBound ≤ objectiveUB + margin'}
                        {check.name === 'GAP_OK' && 'proven gap within tolerance'}
                        {check.name === 'FARKAS_CHECK' && 'Aᵀy ≤ 0 and bᵀy > 0 infeasibility proof'}
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                        {typeof check.value === 'number' ? check.value.toExponential(2) : String(check.value)}
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                        {check.threshold !== undefined ? check.threshold.toExponential(1) : 'Exact'}
                      </td>
                      <td style={{ padding: '8px 12px' }}>
                        {check.pass ? (
                          <span style={{ color: 'var(--success, #10b981)', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 700, fontSize: 11 }}>
                            <CheckCircle2 size={13} />
                            <span>PASS</span>
                          </span>
                        ) : (
                          <span style={{ color: 'var(--danger, #ef4444)', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 700, fontSize: 11 }}>
                            <XCircle size={13} />
                            <span>FAIL</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Certificate JSON Preview */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileText size={15} style={{ color: 'var(--primary)' }} />
                <h4 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Zero-Trust Certificate JSON Payload</h4>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Schema Version 1.0</span>
            </div>

            <pre style={{
              margin: 0,
              padding: 'var(--space-3)',
              background: 'var(--surface-muted, rgba(0,0,0,0.25))',
              borderRadius: 'var(--radius-sm)',
              fontSize: 11,
              fontFamily: 'var(--font-mono)',
              maxHeight: 200,
              overflowY: 'auto',
              border: '1px solid var(--border)'
            }}>
              {cert ? JSON.stringify(cert, null, 2) : 'No certificate loaded.'}
            </pre>
          </div>
        </div>

      </div>
    </div>
  );
}
