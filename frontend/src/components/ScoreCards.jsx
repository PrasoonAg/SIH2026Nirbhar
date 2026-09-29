// components/ScoreCards.jsx — Two-number score model §7.2
// NEVER shows a blended score. Always Verified + Provisional-Inclusive side by side.

function pct(num, den) {
  if (!den || den === 0) return null
  return ((num / den) * 100).toFixed(1)
}

function colorClass(val, isDepend) {
  if (val === null) return ''
  const n = parseFloat(val)
  if (isDepend) return n > 30 ? 'red' : n > 10 ? 'amber' : 'green'
  return n >= 75 ? 'green' : n >= 50 ? 'amber' : 'red'
}

export function ScoreCards({ score }) {
  if (!score) return null

  const verified = pct(score.verified_numerator, score.verified_denominator)
  const provisional = pct(score.provisional_inclusive_numerator, score.provisional_inclusive_denominator)
  const dependence = pct(score.provisional_dependence_numerator, score.provisional_inclusive_denominator)

  return (
    <div className="score-grid mb-3">
      {/* Card 1: Verified */}
      <div className="score-card verified">
        <div className="score-label">Verified</div>
        <div className={`score-num ${colorClass(verified, false)}`}>
          {verified !== null ? `${verified}%` : 'n/a'}
        </div>
        {score.verified_numerator != null && (
          <div className="score-fraction">
            {score.verified_numerator} / {score.verified_denominator} pts
          </div>
        )}
        <div className="score-fraction mt-1" style={{color:'var(--txt-3)'}}>
          DETERMINISTIC + CORROBORATED only
        </div>
      </div>

      {/* Card 2: Provisional-Inclusive */}
      <div className="score-card provisional">
        <div className="score-label">Provisional-Inclusive</div>
        <div className={`score-num ${colorClass(provisional, false)}`}>
          {provisional !== null ? `${provisional}%` : 'n/a'}
        </div>
        {score.provisional_inclusive_numerator != null && (
          <div className="score-fraction">
            {score.provisional_inclusive_numerator} / {score.provisional_inclusive_denominator} pts
          </div>
        )}
        <div className="score-fraction mt-1" style={{color:'var(--txt-3)'}}>
          All evaluated checks
        </div>
      </div>

      {/* Card 3: Provisional Dependence */}
      <div className="score-card dependence">
        <div className="score-label">Provisional Dependence</div>
        <div className={`score-num ${colorClass(dependence, true)}`}>
          {dependence !== null ? `${dependence}%` : 'n/a'}
        </div>
        <div className="score-fraction mt-1" style={{color:'var(--txt-3)'}}>
          % weight resting on Provisional
        </div>
      </div>
    </div>
  )
}
