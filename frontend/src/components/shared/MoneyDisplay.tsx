import React from 'react';
import { formatCentsToCurrency } from '../../services/formatters';

interface MoneyDisplayProps {
  cents: number;
  highlightBalance?: boolean;
  className?: string;
}

export const MoneyDisplay: React.FC<MoneyDisplayProps> = ({
  cents,
  highlightBalance = false,
  className = '',
}) => {
  const formatted = formatCentsToCurrency(cents);

  if (!highlightBalance) {
    return <span className={`font-semibold text-slate-800 ${className}`}>{formatted}</span>;
  }

  if (cents === 0) {
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 ${className}`}>
        $0.00 Settled
      </span>
    );
  }

  if (cents > 0) {
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 ${className}`}>
        {formatted} Owed
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200 ${className}`}>
      {formatCentsToCurrency(Math.abs(cents))} Credit
    </span>
  );
};
