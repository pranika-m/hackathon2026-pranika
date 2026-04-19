import React from 'react';

export interface TimelineItemProps {
  title: string;
  description?: string;
  timestamp?: string;
  status?: 'pending' | 'completed' | 'failed';
  className?: string;
}

export const TimelineItem: React.FC<TimelineItemProps> = ({
  title,
  description,
  timestamp,
  status = 'pending',
  className = '',
}) => {
  const statusColors = {
    pending: 'var(--info)',
    completed: 'var(--resolved)',
    failed: 'var(--failed)',
  };

  return (
    <div className={`timeline-item ${status === 'failed' ? 'failure' : status === 'completed' ? 'success' : ''} ${className}`.trim()}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'start' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>{title}</h4>
          {description && <p style={{ margin: '8px 0 0', color: 'var(--text-muted)' }}>{description}</p>}
        </div>
        <span
          aria-hidden="true"
          style={{ width: '14px', height: '14px', borderRadius: '999px', background: statusColors[status], flexShrink: 0, marginTop: '4px' }}
        />
      </div>
      {timestamp && <p style={{ margin: '10px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{timestamp}</p>}
    </div>
  );
};
