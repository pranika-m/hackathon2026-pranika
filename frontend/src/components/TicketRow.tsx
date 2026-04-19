import React from 'react';

export interface TicketRowProps {
  ticketId: string;
  subject: string;
  status: 'pending' | 'resolved' | 'escalated';
  customer: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  onClick?: () => void;
  className?: string;
}

export const TicketRow: React.FC<TicketRowProps> = ({
  ticketId,
  subject,
  status,
  customer,
  priority,
  onClick,
  className = '',
}) => {
  const statusClasses = {
    pending: 'badge badge-processing',
    resolved: 'badge badge-resolved',
    escalated: 'badge badge-escalated',
  };

  const priorityColors: Record<string, string> = {
    low: 'var(--info)',
    medium: 'var(--escalated)',
    high: 'var(--terracotta-deep)',
    urgent: 'var(--failed)',
  };

  return (
    <tr onClick={onClick} className={className}>
      <td style={{ fontWeight: 700 }}>{ticketId}</td>
      <td>{subject}</td>
      <td style={{ color: 'var(--text-muted)' }}>{customer}</td>
      <td>
        <span className={statusClasses[status]}>{status.charAt(0).toUpperCase() + status.slice(1)}</span>
      </td>
      <td style={{ color: priorityColors[priority], fontWeight: 700 }}>
        {priority.charAt(0).toUpperCase() + priority.slice(1)}
      </td>
    </tr>
  );
};
