import React from 'react';

export interface BadgeProps {
  label: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  label,
  variant = 'default',
  className = '',
}) => {
  const variantClasses = {
    default: 'badge badge-default',
    success: 'badge badge-resolved',
    warning: 'badge badge-escalated',
    error: 'badge badge-failed',
    info: 'badge badge-processing',
  };

  return <span className={`${variantClasses[variant]} ${className}`.trim()}>{label}</span>;
};
