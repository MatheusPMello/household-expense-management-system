import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { GeneralBalanceReport } from '../../types';
import {
  formatCentsToCurrency,
  formatDate,
  getMonthName,
} from '../../services/formatters';
import {
  ShieldAlert,
  BarChart3,
  CheckCircle,
} from 'lucide-react';

export const GeneralBalancePage: React.FC = () => {
  const { activeHousehold } = useAuth();

  const { data: report, isLoading, error } = useQuery<GeneralBalanceReport>({
    queryKey: ['general-balance-report', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) throw new Error('No active household');
      const res = await api.get<GeneralBalanceReport>(
        `/reports/general-balance?household_id=${activeHousehold.household_id}`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
  });

  if (!activeHousehold) {
    return (
      <div className="text-center py-12 text-slate-500">
        Please select a household to view the general balance.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-sm">
        Failed to load general balance metrics.
      </div>
    );
  }

  const maxTrajectoryCents = Math.max(
    ...report.trajectory.map((t) => t.total_cents),
    1
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-emerald-100 text-emerald-700 rounded-xl">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              General Balance & Historical Audit
            </h1>
            <p className="text-sm text-slate-500">
              Long-term liability consolidation, cumulative debt waivers, and compliance metrics for{' '}
              <span className="font-semibold text-slate-700">
                {activeHousehold.household_name}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Section 1: Resident Historical Performance */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Resident Cumulative Ledger & Compliance
            </h2>
            <p className="text-xs text-slate-500">
              Aggregated across all monthly cycles recorded in this household
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Resident</th>
                <th className="px-6 py-3">Total Assigned</th>
                <th className="px-6 py-3">Total Paid</th>
                <th className="px-6 py-3">Cumulative Waived</th>
                <th className="px-6 py-3">Outstanding Net</th>
                <th className="px-6 py-3">Compliance Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.residents.map((r) => {
                const compliance = r.compliance_rate_percent;
                return (
                  <tr key={r.person_id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      {r.person_name}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-700">
                      {formatCentsToCurrency(r.total_assigned_cents)}
                    </td>
                    <td className="px-6 py-4 font-bold text-emerald-600">
                      {formatCentsToCurrency(r.total_paid_cents)}
                    </td>
                    <td className="px-6 py-4 font-bold text-amber-600">
                      {formatCentsToCurrency(r.total_waived_cents)}
                    </td>
                    <td className="px-6 py-4 font-semibold">
                      {r.outstanding_historical_balance_cents === 0 ? (
                        <span className="text-emerald-600">$0.00 Settled</span>
                      ) : r.outstanding_historical_balance_cents > 0 ? (
                        <span className="text-rose-600">
                          {formatCentsToCurrency(r.outstanding_historical_balance_cents)} Owed
                        </span>
                      ) : (
                        <span className="text-sky-600">
                          {formatCentsToCurrency(Math.abs(r.outstanding_historical_balance_cents))} Credit
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-24 bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              compliance >= 95
                                ? 'bg-emerald-500'
                                : compliance >= 75
                                ? 'bg-amber-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(compliance, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-slate-700">
                          {compliance.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 2: Household Monthly Cost Trajectory (Fixed vs Variable) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Household Cost Trajectory
            </h2>
            <p className="text-xs text-slate-500">
              Monthly spending trend separated into Fixed recurring expenses and Variable ad-hoc expenses
            </p>
          </div>
          <div className="flex items-center space-x-4 text-xs">
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 bg-emerald-500 rounded" />
              <span className="text-slate-600 font-medium">Fixed Recurring</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 bg-indigo-500 rounded" />
              <span className="text-slate-600 font-medium">Variable Ad-hoc</span>
            </div>
          </div>
        </div>

        {report.trajectory.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No trajectory data yet. Once billing cycles are created, trajectory analysis will render here.
          </div>
        ) : (
          <div className="space-y-4">
            {report.trajectory.map((point) => {
              const fixedPct = (point.fixed_cents / maxTrajectoryCents) * 100;
              const varPct = (point.variable_cents / maxTrajectoryCents) * 100;

              return (
                <div key={point.cycle_id} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-700">
                      {getMonthName(point.month)} {point.year}
                    </span>
                    <span className="text-slate-900 font-bold">
                      {formatCentsToCurrency(point.total_cents)}
                      <span className="text-slate-400 font-normal ml-2">
                        (Fixed: {formatCentsToCurrency(point.fixed_cents)} &bull; Var: {formatCentsToCurrency(point.variable_cents)})
                      </span>
                    </span>
                  </div>

                  <div className="h-4 bg-slate-100 rounded-lg overflow-hidden flex">
                    <div
                      className="bg-emerald-500 h-full transition-all"
                      style={{ width: `${fixedPct}%` }}
                      title={`Fixed: ${formatCentsToCurrency(point.fixed_cents)}`}
                    />
                    <div
                      className="bg-indigo-500 h-full transition-all"
                      style={{ width: `${varPct}%` }}
                      title={`Variable: ${formatCentsToCurrency(point.variable_cents)}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 3: Dedicated Debt Waiver Audit Ledger */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Debt Waiver & Forgiveness Audit Ledger
              </h2>
              <p className="text-xs text-slate-500">
                Audited, immutable log of forgiven liabilities and offsets across all historical cycles
              </p>
            </div>
          </div>
        </div>

        {report.debt_waiver_ledger.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            No debt waivers have been registered. All residents have settled their assigned obligations in full.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Resident</th>
                  <th className="px-6 py-3">Billing Cycle</th>
                  <th className="px-6 py-3">Waived Amount</th>
                  <th className="px-6 py-3">Date Waived</th>
                  <th className="px-6 py-3">Mandatory Audited Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.debt_waiver_ledger.map((w) => (
                  <tr key={w.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      {w.person_name}
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-medium">
                      {getMonthName(w.cycle_month)} {w.cycle_year}
                    </td>
                    <td className="px-6 py-4 font-bold text-amber-600">
                      {formatCentsToCurrency(w.amount_cents)}
                    </td>
                    <td className="px-6 py-4 text-slate-500 text-xs">
                      {formatDate(w.waived_at)}
                    </td>
                    <td className="px-6 py-4 text-slate-700 italic max-w-md">
                      "{w.reason}"
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
