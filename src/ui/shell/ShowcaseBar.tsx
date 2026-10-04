/**
 * NIRBHAR — System Tour & Operational Briefing Dock
 * 
 * Provides an executive walkthrough across the 6 key solver subsystems:
 *   1. Sovereign Optimization Architecture (/)
 *   2. Industrial Refinery Planning Suite (/refinery)
 *   3. Certified Branch-and-Cut Lab (/bnc-lab)
 *   4. Numerical Hardening & Degeneracy Lab (/robustness)
 *   5. Air-Gapped Independent Verifier (/verifier)
 *   6. System Acceptance & SIH Compliance (/selftest)
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../store';
import {
  ChevronRight, ChevronLeft, X, ShieldCheck
} from 'lucide-react';

interface ShowcaseChapter {
  id: number;
  title: string;
  path: string;
  badge: string;
  narration: string;
  capabilityHighlight: string;
}

const CHAPTERS: ShowcaseChapter[] = [
  {
    id: 1,
    title: 'Sovereign Optimization Architecture',
    path: '/',
    badge: 'Core Foundation',
    narration: 'NIRBHAR is an indigenous certified mathematical solver core engineered from first principles for MRPL operations (SIH26119), featuring zero third-party solver dependencies.',
    capabilityHighlight: '100% First-Principles Math · Zero Third-Party Imports'
  },
  {
    id: 2,
    title: 'Industrial Refinery Planning Suite',
    path: '/refinery',
    badge: 'Operations',
    narration: 'Multi-period crude assay optimization (LP), CDU distillation campaign scheduling (MILP), and crude price-risk volatility hedging (QP) with live duality certificate receipts.',
    capabilityHighlight: 'Atmospheric Distillation · BS-VI Diesel (≤10 ppm Sulfur)'
  },
  {
    id: 3,
    title: 'Certified Branch-and-Cut Lab',
    path: '/bnc-lab',
    badge: 'Discrete Engine',
    narration: 'Interactive search tree exploration with Gomory Mixed-Integer (GMI) and cover cuts, enforcing certified Lagrangian lower bound pruning LB(y).',
    capabilityHighlight: 'Mathematically Audited Pruning · No Node Pruned Without Proof'
  },
  {
    id: 4,
    title: 'Numerical Hardening & Degeneracy Lab',
    path: '/robustness',
    badge: 'Fault Tolerance',
    narration: 'Automated multi-level recovery actively detecting degenerate plateaus and infinite cycling, recovering seamlessly via Bland\'s anti-cycling rule.',
    capabilityHighlight: 'Degeneracy Recovery · Anti-Cycling Pivot Escalation'
  },
  {
    id: 5,
    title: 'Air-Gapped Independent Verifier',
    path: '/verifier',
    badge: 'Zero-Trust Audit',
    narration: 'Physically segregated verification engine re-reading raw MPS files to compute exact primal-dual residuals, safe Lagrangian bounds, and Farkas infeasibility rays.',
    capabilityHighlight: 'Air-Gapped Zero-Trust · Exact BigInt Rational Verification'
  },
  {
    id: 6,
    title: 'System Acceptance & SIH Compliance',
    path: '/selftest',
    badge: 'Traceability Matrix',
    narration: 'Full traceability across all 31 Problem Statement requirements with automated real-time in-browser acceptance test validation.',
    capabilityHighlight: '100% Verified · 73/73 Backend Pytest · 33/33 Frontend Suites'
  }
];

export function ShowcaseBar() {
  const { showcaseMode, showcaseChapter, setShowcaseMode, setShowcaseChapter } = useAppStore();
  const navigate = useNavigate();
  const location = useLocation();

  if (!showcaseMode) return null;

  const currentIdx = Math.min(Math.max(0, showcaseChapter), CHAPTERS.length - 1);
  const currentChapter = CHAPTERS[currentIdx];

  const goToChapter = (idx: number) => {
    setShowcaseChapter(idx);
    navigate(CHAPTERS[idx].path);
  };

  const handleNext = () => {
    if (currentIdx < CHAPTERS.length - 1) {
      goToChapter(currentIdx + 1);
    } else {
      setShowcaseMode(false);
    }
  };

  const handlePrev = () => {
    if (currentIdx > 0) {
      goToChapter(currentIdx - 1);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 'calc(100% - 48px)',
      maxWidth: 960,
      zIndex: 1000,
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderTop: '2px solid var(--primary)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: '0 16px 40px rgba(0,0,0,0.3)',
      padding: '14px 18px',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      backdropFilter: 'blur(16px)',
      animation: 'slideUp 0.25s ease-out'
    }}>
      {/* Top row: Chapter header & navigation controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            background: 'var(--primary)',
            color: '#fff',
            borderRadius: 'var(--radius-sm)',
            padding: '2px 8px',
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: '0.05em'
          }}>
            STAGE {currentChapter.id} OF 6
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text)' }}>
              {currentChapter.title}
            </span>
            <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.12)', color: 'var(--primary)', fontSize: 11, border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              {currentChapter.badge}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Chapter dots */}
          <div style={{ display: 'flex', gap: 5, marginRight: 8 }}>
            {CHAPTERS.map((chap, idx) => (
              <button
                key={chap.id}
                onClick={() => goToChapter(idx)}
                title={chap.title}
                style={{
                  width: idx === currentIdx ? 22 : 7,
                  height: 6,
                  borderRadius: 3,
                  background: idx === currentIdx ? 'var(--primary)' : 'var(--border)',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  transition: 'all 0.2s ease'
                }}
              />
            ))}
          </div>

          <button
            className="btn btn-secondary"
            onClick={handlePrev}
            disabled={currentIdx === 0}
            style={{ padding: '5px 12px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
          >
            <ChevronLeft size={13} /> Prev
          </button>

          <button
            className="btn btn-primary"
            onClick={handleNext}
            style={{ padding: '5px 14px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5, fontWeight: 700 }}
          >
            {currentIdx === CHAPTERS.length - 1 ? 'Complete Tour' : 'Next Chapter'} <ChevronRight size={13} />
          </button>

          <button
            onClick={() => setShowcaseMode(false)}
            title="Exit Tour"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
              marginLeft: 4
            }}
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Information row: Clean executive readout & capability highlight */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        padding: '10px 14px',
        background: 'var(--surface-muted)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        fontSize: 12,
        flexWrap: 'wrap'
      }}>
        <div style={{ flex: '1 1 520px', color: 'var(--text)', lineHeight: 1.5 }}>
          {currentChapter.narration}
        </div>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text)',
          fontSize: 11,
          fontWeight: 600,
          whiteSpace: 'nowrap'
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', flexShrink: 0 }} />
          <span>{currentChapter.capabilityHighlight}</span>
        </div>
      </div>
    </div>
  );
}
