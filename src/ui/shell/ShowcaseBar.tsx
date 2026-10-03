/**
 * NIRBHAR — Showcase Mode Guided Tour Dock (Phase 7)
 * 
 * Provides an interactive guided walkthrough across the 6 key demonstration chapters:
 *   1. Sovereign Foundation & Pitch (/)
 *   2. Industrial Refinery Demo (/refinery)
 *   3. Certified Branch-and-Cut Lab (/bnc-lab)
 *   4. Robustness Lab & Escalation (/robustness)
 *   5. Air-Gapped Independent Verifier (/verifier)
 *   6. PS Compliance & Acceptance Suite (/compliance & /selftest)
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../store';
import {
  Sparkles, ChevronRight, ChevronLeft, X, Play, ShieldCheck,
  CheckCircle2, Award, ArrowRight
} from 'lucide-react';

interface ShowcaseChapter {
  id: number;
  title: string;
  path: string;
  badge: string;
  narration: string;
  suggestedAction: string;
}

const CHAPTERS: ShowcaseChapter[] = [
  {
    id: 1,
    title: 'Sovereign Foundation & Core Pitch',
    path: '/',
    badge: 'Overview',
    narration: 'NIRBHAR is an indigenous certified optimization core built from mathematical first principles for MRPL (SIH26119) with 0 third-party solver dependencies.',
    suggestedAction: 'Review the Atmanirbhar core stats and click "Refinery Demo" to start.'
  },
  {
    id: 2,
    title: 'Industrial Refinery Planning Suite',
    path: '/refinery',
    badge: 'Core Demo',
    narration: 'Explore crude oil blending (LP), distillation campaign switchovers (MILP), and price-risk hedging (QP) with live duality certificate receipts.',
    suggestedAction: 'Click "Solve Baseline" to see binding CDU constraints and shadow prices.'
  },
  {
    id: 3,
    title: 'Certified Branch-and-Cut Lab',
    path: '/bnc-lab',
    badge: 'Discrete Engine',
    narration: 'Inspect tree exploration, safe lower bound pruning LB(y), and Gomory/c-MIR cut separation that guarantees no optimum is ever cut off.',
    suggestedAction: 'Select the Knapsack sample and toggle "Enable Cuts" to watch the root gap collapse.'
  },
  {
    id: 4,
    title: 'Robustness Lab & 8-Level Escalation',
    path: '/robustness',
    badge: 'Numerical Hardening',
    narration: 'Witness textbook Naive Mode enter an infinite cycle on Beale LP, while NIRBHAR Hardened Core detects the cycle and recovers with Bland\'s rule.',
    suggestedAction: 'Click "Run Side-by-Side Benchmark" to compare Naive vs Hardened.'
  },
  {
    id: 5,
    title: 'Air-Gapped Independent Verifier',
    path: '/verifier',
    badge: 'Proof Receipt',
    narration: 'An isolated engine with ZERO solver imports. Re-reads raw MPS files and re-evaluates safe bounds in exact BigInt rational arithmetic.',
    suggestedAction: 'Switch to "Exact Mode (BigInt Rational)" and run an Adversarial attack to see corruptions rejected.'
  },
  {
    id: 6,
    title: 'PS Compliance & Acceptance Self-Test',
    path: '/selftest',
    badge: 'Acceptance Audit',
    narration: '31/31 Problem Statement compliance traceability and automated in-memory acceptance testing confirming 100% green status.',
    suggestedAction: 'Click "Run All Acceptance Tests" to execute real-time browser diagnostics.'
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
      border: '1px solid var(--primary)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: '0 12px 36px rgba(0,0,0,0.25)',
      padding: '16px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      backdropFilter: 'blur(12px)',
      animation: 'slideUp 0.25s ease-out'
    }}>
      {/* Top row: Chapter header & controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            background: 'var(--primary)',
            color: '#fff',
            borderRadius: '50%',
            width: 24,
            height: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 12,
            fontWeight: 800
          }}>
            {currentChapter.id}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 800, fontSize: 14, color: 'var(--text)' }}>
                {currentChapter.title}
              </span>
              <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: 'var(--primary)', fontSize: 11 }}>
                {currentChapter.badge}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Chapter dots */}
          <div style={{ display: 'flex', gap: 4, marginRight: 8 }}>
            {CHAPTERS.map((chap, idx) => (
              <button
                key={chap.id}
                onClick={() => goToChapter(idx)}
                title={chap.title}
                style={{
                  width: idx === currentIdx ? 20 : 8,
                  height: 8,
                  borderRadius: 4,
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
            style={{ padding: '6px 12px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
          >
            <ChevronLeft size={14} /> Prev
          </button>

          <button
            className="btn btn-primary"
            onClick={handleNext}
            style={{ padding: '6px 14px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700 }}
          >
            {currentIdx === CHAPTERS.length - 1 ? 'Finish Tour' : 'Next Step'} <ChevronRight size={14} />
          </button>

          <button
            onClick={() => setShowcaseMode(false)}
            title="Exit Showcase Tour"
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
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Narration & action bar */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.4fr 1fr',
        gap: 16,
        padding: '10px 14px',
        background: 'var(--surface-muted)',
        borderRadius: 'var(--radius-sm)',
        fontSize: 12,
        alignItems: 'center'
      }}>
        <div style={{ color: 'var(--text)', lineHeight: 1.4 }}>
          <strong style={{ color: 'var(--primary)' }}>Judge Walkthrough: </strong>
          {currentChapter.narration}
        </div>
        <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={14} color="var(--primary)" />
          <span><strong style={{ color: 'var(--text)' }}>Action:</strong> {currentChapter.suggestedAction}</span>
        </div>
      </div>
    </div>
  );
}
