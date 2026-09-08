import React from 'react';

interface StatusBadgeProps {
  type: 'cycle' | 'payment' | 'role' | 'split' | 'expense_status';
  value: string;
}

const ExpenseStatusBadge: React.FC<{ value: string }> = ({ value }) => {
  if (value === 'PENDING_VALUE') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
        <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-amber-500 animate-pulse" />
        <span>Awaiting Bill</span>
      </span>
    );
  }
  if (value === 'READY') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-emerald-500" />
        <span>Ready</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
      {value}
    </span>
  );
};

const CycleBadge: React.FC<{ value: string }> = ({ value }) => {
  const isOpen = value === 'OPEN';
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        isOpen
          ? 'bg-emerald-100 text-emerald-800'
          : 'bg-slate-200 text-slate-700'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
          isOpen ? 'bg-emerald-500' : 'bg-slate-500'
        }`}
      />
      <span>{value}</span>
    </span>
  );
};

const PaymentBadge: React.FC<{ value: string }> = ({ value }) => {
  const isPaid = value === 'true' || value === 'Paid';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        isPaid
          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
          : 'bg-amber-50 text-amber-700 border border-amber-200'
      }`}
    >
      {isPaid ? 'Paid' : 'Pending'}
    </span>
  );
};

const RoleBadge: React.FC<{ value: string }> = ({ value }) => {
  const isAdmin = value === 'ADMIN';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
        isAdmin
          ? 'bg-purple-50 text-purple-700 border border-purple-200'
          : 'bg-blue-50 text-blue-700 border border-blue-200'
      }`}
    >
      {value}
    </span>
  );
};

const SplitBadge: React.FC<{ value: string }> = ({ value }) => (
  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
    {value}
  </span>
);

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  switch (type) {
    case 'expense_status':
      return <ExpenseStatusBadge value={value} />;
    case 'cycle':
      return <CycleBadge value={value} />;
    case 'payment':
      return <PaymentBadge value={value} />;
    case 'role':
      return <RoleBadge value={value} />;
    case 'split':
    default:
      return <SplitBadge value={value} />;
  }
};
