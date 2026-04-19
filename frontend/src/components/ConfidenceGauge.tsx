import React from 'react';

export interface ConfidenceGaugeProps {
  score: number;
  label?: string;
  className?: string;
}

export const ConfidenceGauge: React.FC<ConfidenceGaugeProps> = ({
  score,
  label = 'Confidence',
  className = '',
}) => {
  const percentage = Math.min(Math.max(score * 100, 0), 100);
  const color =
    percentage >= 70 ? 'var(--resolved)' : percentage >= 50 ? 'var(--escalated)' : 'var(--failed)';

  return (
    <div className={className} style={{ display: 'grid', gap: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text)' }}>{label}</span>
        <span style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text)' }}>{percentage.toFixed(1)}%</span>
      </div>
      <div className="confidence-gauge" aria-label={label}>
        <div className="confidence-gauge-fill" style={{ width: `${percentage}%`, background: color }} />
      </div>
    </div>
  );
};
