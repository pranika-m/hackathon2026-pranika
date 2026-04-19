import React from 'react';

export interface SummaryCardProps {
  title: string;
  content: string;
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  className?: string;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  content,
  priority = 'medium',
  className = '',
}) => {
  const priorityColors: Record<string, string> = {
    low: 'var(--info)',
    medium: 'var(--escalated)',
    high: 'var(--terracotta)',
    urgent: 'var(--failed)',
  };

  return (
    <article
      className={`card ${className}`.trim()}
      style={{ padding: '20px', borderLeft: `5px solid ${priorityColors[priority]}` }}
    >
      <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>{title}</h3>
      <p style={{ margin: '10px 0 0', color: 'var(--text-muted)' }}>{content}</p>
      <div className="status-strip" style={{ marginTop: '16px', background: priorityColors[priority] }} />
    </article>
  );
};
