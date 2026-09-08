import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  BillingCycle,
  CurrentCycleReport,
  ResidentCycleBalance,
  Payment,
  DebtWaiver,
} from '../../types';
import {
  formatCentsToCurrency,
  parseCurrencyToCents,
  formatDate,
  getMonthName,
} from '../../services/formatters';
import { MoneyDisplay } from '../../components/shared/MoneyDisplay';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { Modal } from '../../components/ui/Modal';
import {
  DollarSign,
  CheckCircle2,
  Calendar,
  Lock,
  Unlock,
  CreditCard,
  HeartHandshake,
  Plus,
  ChevronDown,
  ChevronUp,
  Receipt,
  AlertCircle,
  History,
  Edit2,
  Trash2,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { activeHousehold } = useAuth();
  const queryClient = useQueryClient();

  const [selectedCycleId, setSelectedCycleId] = useState<string | null>(null);
  const [expandedExpenseId, setExpandedExpenseId] = useState<string | null>(null);

  // Modals state
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isWaiverModalOpen, setIsWaiverModalOpen] = useState(false);
  const [isCreateCycleModalOpen, setIsCreateCycleModalOpen] = useState(false);
  const [selectedResident, setSelectedResident] = useState<ResidentCycleBalance | null>(null);

  // Settlement History & Edit / Delete Modals state
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historyResident, setHistoryResident] = useState<ResidentCycleBalance | null>(null);
  const [historyTab, setHistoryTab] = useState<'payments' | 'waivers'>('payments');
  const [editingPayment, setEditingPayment] = useState<Payment | null>(null);
  const [editPaymentAmountStr, setEditPaymentAmountStr] = useState('');
  const [editPaymentNotes, setEditPaymentNotes] = useState('');
  const [isEditPaymentModalOpen, setIsEditPaymentModalOpen] = useState(false);
  const [editingWaiver, setEditingWaiver] = useState<DebtWaiver | null>(null);
  const [editWaiverAmountStr, setEditWaiverAmountStr] = useState('');
  const [editWaiverReason, setEditWaiverReason] = useState('');
  const [isEditWaiverModalOpen, setIsEditWaiverModalOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    type: 'payment' | 'waiver';
    id: string;
    name: string;
  } | null>(null);

  // Form states
  const [paymentAmountStr, setPaymentAmountStr] = useState('');
  const [paymentNotes, setPaymentNotes] = useState('');
  const [waiverAmountStr, setWaiverAmountStr] = useState('');
  const [waiverReason, setWaiverReason] = useState('');
  const [newCycleYear, setNewCycleYear] = useState(new Date().getFullYear());
  const [newCycleMonth, setNewCycleMonth] = useState(new Date().getMonth() + 1);
  const [formError, setFormError] = useState('');

  // 1. Fetch household cycles
  const { data: cycles = [] } = useQuery<BillingCycle[]>({
    queryKey: ['cycles', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) return [];
      const res = await api.get<BillingCycle[]>(
        `/cycles?household_id=${activeHousehold.household_id}`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
  });

  // Automatically select latest cycle if none is selected
  const activeCycle =
    cycles.find((c) => c.id === selectedCycleId) || cycles[0] || null;

  // 2. Fetch current cycle operational report
  const {
    data: report,
    isLoading: reportLoading,
    refetch: refetchReport,
  } = useQuery<CurrentCycleReport>({
    queryKey: ['cycle-report', activeCycle?.id],
    queryFn: async () => {
      if (!activeCycle) throw new Error('No cycle');
      const res = await api.get<CurrentCycleReport>(
        `/reports/current-cycle?cycle_id=${activeCycle.id}`
      );
      return res.data;
    },
    enabled: !!activeCycle,
  });

  // Mutations
  const togglePaymentStatus = useMutation({
    mutationFn: async ({
      expenseId,
      isPaid,
    }: {
      expenseId: string;
      isPaid: boolean;
    }) => {
      await api.patch(`/expenses/${expenseId}/payment-status`, {
        is_paid: isPaid,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cycle-report', activeCycle?.id] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
  });

  // 3. Fetch payments and waivers for history modal
  const { data: residentPayments = [], isLoading: paymentsLoading } = useQuery<Payment[]>({
    queryKey: ['cycle-payments', activeCycle?.id, historyResident?.person_id],
    queryFn: async () => {
      if (!activeCycle || !historyResident) return [];
      const res = await api.get<Payment[]>(
        `/settlements/payments?billing_cycle_id=${activeCycle.id}&person_id=${historyResident.person_id}`
      );
      return res.data;
    },
    enabled: isHistoryModalOpen && !!activeCycle && !!historyResident,
  });

  const { data: residentWaivers = [], isLoading: waiversLoading } = useQuery<DebtWaiver[]>({
    queryKey: ['cycle-waivers', activeCycle?.id, historyResident?.person_id],
    queryFn: async () => {
      if (!activeCycle || !historyResident) return [];
      const res = await api.get<DebtWaiver[]>(
        `/settlements/waivers?billing_cycle_id=${activeCycle.id}&person_id=${historyResident.person_id}`
      );
      return res.data;
    },
    enabled: isHistoryModalOpen && !!activeCycle && !!historyResident,
  });

  const recordPayment = useMutation({
    mutationFn: async () => {
      if (!activeCycle || !selectedResident) return;
      const cents = parseCurrencyToCents(paymentAmountStr);
      if (cents <= 0) throw new Error('Payment amount must be greater than zero.');

      await api.post('/settlements/payments', {
        billing_cycle_id: activeCycle.id,
        person_id: selectedResident.person_id,
        amount_cents: cents,
        notes: paymentNotes || null,
      });
    },
    onSuccess: () => {
      setIsPaymentModalOpen(false);
      setPaymentAmountStr('');
      setPaymentNotes('');
      setFormError('');
      refetchReport();
      queryClient.invalidateQueries({ queryKey: ['cycle-payments'] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const updatePayment = useMutation({
    mutationFn: async () => {
      if (!editingPayment) return;
      const cents = parseCurrencyToCents(editPaymentAmountStr);
      if (cents <= 0) throw new Error('Payment amount must be greater than zero.');

      await api.patch(`/settlements/payments/${editingPayment.id}`, {
        amount_cents: cents,
        notes: editPaymentNotes || null,
      });
    },
    onSuccess: () => {
      setIsEditPaymentModalOpen(false);
      setEditingPayment(null);
      setFormError('');
      refetchReport();
      queryClient.invalidateQueries({ queryKey: ['cycle-payments'] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const deletePayment = useMutation({
    mutationFn: async (paymentId: string) => {
      await api.delete(`/settlements/payments/${paymentId}`);
    },
    onSuccess: () => {
      setDeleteConfirm(null);
      refetchReport();
      queryClient.invalidateQueries({ queryKey: ['cycle-payments'] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const recordWaiver = useMutation({
    mutationFn: async () => {
      if (!activeCycle || !selectedResident) return;
      const cents = parseCurrencyToCents(waiverAmountStr);
      if (cents <= 0) throw new Error('Waiver amount must be greater than zero.');
      if (!waiverReason.trim()) throw new Error('A detailed reason is required for audited debt waivers.');

      await api.post('/settlements/waivers', {
        billing_cycle_id: activeCycle.id,
        person_id: selectedResident.person_id,
        amount_cents: cents,
        reason: waiverReason.trim(),
      });
    },
    onSuccess: () => {
      setIsWaiverModalOpen(false);
      setWaiverAmountStr('');
      setWaiverReason('');
      setFormError('');
      refetchReport();
      queryClient.invalidateQueries({ queryKey: ['cycle-waivers'] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const updateWaiver = useMutation({
    mutationFn: async () => {
      if (!editingWaiver) return;
      const cents = parseCurrencyToCents(editWaiverAmountStr);
      if (cents <= 0) throw new Error('Waiver amount must be greater than zero.');
      if (!editWaiverReason.trim()) throw new Error('A detailed reason is required for audited debt waivers.');

      await api.patch(`/settlements/waivers/${editingWaiver.id}`, {
        amount_cents: cents,
        reason: editWaiverReason.trim(),
      });
    },
    onSuccess: () => {
      setIsEditWaiverModalOpen(false);
      setEditingWaiver(null);
      setFormError('');
      refetchReport();
      queryClient.invalidateQueries({ queryKey: ['cycle-waivers'] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const deleteWaiver = useMutation({
    mutationFn: async (waiverId: string) => {
      await api.delete(`/settlements/waivers/${waiverId}`);
    },
    onSuccess: () => {
      setDeleteConfirm(null);
      refetchReport();
      queryClient.invalidateQueries({ queryKey: ['cycle-waivers'] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const toggleCycleStatus = useMutation({
    mutationFn: async (action: 'close' | 'reopen') => {
      if (!activeCycle) return;
      await api.post(`/cycles/${activeCycle.id}/${action}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
      queryClient.invalidateQueries({ queryKey: ['cycle-report', activeCycle?.id] });
    },
  });

  const createCycle = useMutation({
    mutationFn: async () => {
      if (!activeHousehold) return;
      const res = await api.post('/cycles', {
        household_id: activeHousehold.household_id,
        year: Number(newCycleYear),
        month: Number(newCycleMonth),
      });
      return res.data;
    },
    onSuccess: (newCycle) => {
      setIsCreateCycleModalOpen(false);
      setSelectedCycleId(newCycle.id);
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  if (!activeHousehold) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-medium text-slate-700">
          Please select or create a household to get started.
        </h2>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Header: Cycle Selector & Period Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-emerald-100 rounded-lg text-emerald-700">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900">
                {activeCycle
                  ? `${getMonthName(activeCycle.month)} ${activeCycle.year}`
                  : 'No Billing Cycle'}
              </h1>
              {activeCycle && (
                <StatusBadge type="cycle" value={activeCycle.status} />
              )}
            </div>
            <p className="text-xs text-slate-500">
              Operational Ledger for {activeHousehold.household_name}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Cycle Switcher */}
          {cycles.length > 0 && (
            <select
              value={activeCycle?.id || ''}
              onChange={(e) => setSelectedCycleId(e.target.value)}
              className="text-sm bg-slate-50 border border-slate-300 text-slate-700 rounded-lg px-3 py-2 focus:ring-emerald-500 focus:border-emerald-500"
            >
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>
                  {getMonthName(c.month)} {c.year} ({c.status})
                </option>
              ))}
            </select>
          )}

          {/* New Cycle Button */}
          {activeHousehold.role === 'ADMIN' && (
            <button
              onClick={() => {
                setFormError('');
                setIsCreateCycleModalOpen(true);
              }}
              className="flex items-center space-x-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>New Cycle</span>
            </button>
          )}

          {/* Close / Reopen Cycle */}
          {activeHousehold.role === 'ADMIN' && activeCycle && (
            activeCycle.status === 'OPEN' ? (
              <button
                onClick={() => toggleCycleStatus.mutate('close')}
                className="flex items-center space-x-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg border border-slate-200 transition-colors"
                title="Lock billing cycle from further mutations"
              >
                <Lock className="w-4 h-4 text-slate-500" />
                <span>Close Cycle</span>
              </button>
            ) : (
              <button
                onClick={() => toggleCycleStatus.mutate('reopen')}
                className="flex items-center space-x-1.5 px-3 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 text-sm font-medium rounded-lg border border-amber-200 transition-colors"
              >
                <Unlock className="w-4 h-4" />
                <span>Reopen Cycle</span>
              </button>
            )
          )}
        </div>
      </div>

      {cycles.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <Receipt className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-slate-800">
            No billing cycles found
          </h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mt-1 mb-6">
            Create your first monthly billing period. Any active recurring templates will be automatically applied and split among residents.
          </p>
          {activeHousehold.role === 'ADMIN' && (
            <button
              onClick={() => setIsCreateCycleModalOpen(true)}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow transition-colors"
            >
              Create Initial Cycle
            </button>
          )}
        </div>
      ) : reportLoading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
        </div>
      ) : report ? (
        <>
          {/* Section 1: Summary Banner */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
                <DollarSign className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  House Budget
                </p>
                <p className="text-2xl font-bold text-slate-900 mt-0.5">
                  {formatCentsToCurrency(report.total_budget_cents)}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Total cycle expenses
                </p>
              </div>
            </div>

            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="p-3 rounded-lg bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Paid Expenses
                </p>
                <p className="text-2xl font-bold text-emerald-600 mt-0.5">
                  {formatCentsToCurrency(report.total_paid_cents)}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Utilities & bills settled
                </p>
              </div>
            </div>

            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="p-3 rounded-lg bg-indigo-50 text-indigo-600">
                <CreditCard className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Collected from Residents
                </p>
                <p className="text-2xl font-bold text-indigo-600 mt-0.5">
                  {formatCentsToCurrency(report.total_collected_cents)}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Payments received
                </p>
              </div>
            </div>

            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
              <div className="p-3 rounded-lg bg-amber-50 text-amber-600">
                <HeartHandshake className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Waived Amounts
                </p>
                <p className="text-2xl font-bold text-amber-600 mt-0.5">
                  {formatCentsToCurrency(report.total_waived_cents)}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Audited debt forgiveness
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Resident Breakdown Cards */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  Resident Balances & Operations
                </h2>
                <p className="text-xs text-slate-500">
                  Calculated from: Assigned - (Paid + Waived) = Remaining Balance
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {report.residents.map((r) => (
                <div
                  key={r.person_id}
                  className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
                      <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 font-semibold flex items-center justify-center text-sm">
                          {r.person_name.charAt(0)}
                        </div>
                        <span className="font-semibold text-slate-900">
                          {r.person_name}
                        </span>
                      </div>
                      <MoneyDisplay
                        cents={r.remaining_balance_cents}
                        highlightBalance
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-2 py-2 text-center text-xs">
                      <div className="bg-slate-50 p-2 rounded-lg">
                        <span className="text-slate-400 block font-medium">
                          Assigned
                        </span>
                        <span className="font-bold text-slate-800">
                          {formatCentsToCurrency(r.assigned_cents)}
                        </span>
                      </div>
                      <div className="bg-emerald-50/50 p-2 rounded-lg">
                        <span className="text-emerald-600 block font-medium">
                          Paid
                        </span>
                        <span className="font-bold text-emerald-700">
                          {formatCentsToCurrency(r.paid_cents)}
                        </span>
                      </div>
                      <div className="bg-amber-50/50 p-2 rounded-lg">
                        <span className="text-amber-600 block font-medium">
                          Waived
                        </span>
                        <span className="font-bold text-amber-700">
                          {formatCentsToCurrency(r.waived_cents)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Quick Actions */}
                  <div className="flex items-center space-x-2 mt-4 pt-3 border-t border-slate-100">
                    {activeCycle.status === 'OPEN' && (
                      <>
                        <button
                          onClick={() => {
                            setSelectedResident(r);
                            setPaymentAmountStr(
                              r.remaining_balance_cents > 0
                                ? (r.remaining_balance_cents / 100).toFixed(2)
                                : ''
                            );
                            setFormError('');
                            setIsPaymentModalOpen(true);
                          }}
                          className="flex-1 py-1.5 px-3 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-medium text-xs rounded-lg transition-colors border border-emerald-200 text-center"
                        >
                          + Record Payment
                        </button>

                        {activeHousehold.role === 'ADMIN' && (
                          <button
                            onClick={() => {
                              setSelectedResident(r);
                              setWaiverAmountStr(
                                r.remaining_balance_cents > 0
                                  ? (r.remaining_balance_cents / 100).toFixed(2)
                                  : ''
                              );
                              setWaiverReason('');
                              setFormError('');
                              setIsWaiverModalOpen(true);
                            }}
                            className="py-1.5 px-3 bg-amber-50 hover:bg-amber-100 text-amber-700 font-medium text-xs rounded-lg transition-colors border border-amber-200 text-center"
                            title="Waive remaining debt without penalizing operational ledger"
                          >
                            Waive Amount
                          </button>
                        )}
                      </>
                    )}

                    <button
                      onClick={() => {
                        setHistoryResident(r);
                        setHistoryTab('payments');
                        setFormError('');
                        setIsHistoryModalOpen(true);
                      }}
                      className={`py-1.5 px-2.5 bg-slate-50 hover:bg-slate-100 text-slate-600 font-medium text-xs rounded-lg transition-colors border border-slate-200 flex items-center space-x-1 ${
                        activeCycle.status !== 'OPEN' ? 'w-full justify-center' : ''
                      }`}
                      title="View Settlement & Waiver History"
                    >
                      <History className="w-3.5 h-3.5" />
                      <span>History</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Cycle Expense Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900">
                  Cycle Expenses & Splits
                </h3>
                <p className="text-xs text-slate-500">
                  Detailed expense allocations and payment statuses
                </p>
              </div>
            </div>

            {report.expenses.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                No expenses registered for this cycle yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Expense</th>
                      <th className="px-6 py-3">Category</th>
                      <th className="px-6 py-3">Due Date</th>
                      <th className="px-6 py-3">Total Amount</th>
                      <th className="px-6 py-3">Payment Status</th>
                      <th className="px-6 py-3">Split Method</th>
                      <th className="px-6 py-3 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {report.expenses.map((e) => {
                      const isExpanded = expandedExpenseId === e.id;
                      return (
                        <React.Fragment key={e.id}>
                          <tr className="hover:bg-slate-50/50 transition-colors">
                            <td className="px-6 py-4 font-medium text-slate-900">
                              <div className="flex items-center space-x-2">
                                <span>{e.title}</span>
                                {e.is_fixed && (
                                  <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-semibold uppercase">
                                    Fixed
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4 text-slate-600">
                              <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs">
                                {e.category}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-slate-600">
                              {formatDate(e.due_date)}
                            </td>
                            <td className="px-6 py-4 font-bold text-slate-900">
                              {formatCentsToCurrency(e.total_amount_cents)}
                            </td>
                            <td className="px-6 py-4">
                              <button
                                onClick={() =>
                                  togglePaymentStatus.mutate({
                                    expenseId: e.id,
                                    isPaid: !e.is_paid,
                                  })
                                }
                                className="group flex items-center space-x-1.5 focus:outline-none"
                                title="Click to toggle payment settlement"
                              >
                                <StatusBadge
                                  type="payment"
                                  value={e.is_paid ? 'Paid' : 'Pending'}
                                />
                              </button>
                            </td>
                            <td className="px-6 py-4">
                              <StatusBadge type="split" value={e.split_type} />
                            </td>
                            <td className="px-6 py-4 text-right">
                              <button
                                onClick={() =>
                                  setExpandedExpenseId(isExpanded ? null : e.id)
                                }
                                className="text-slate-400 hover:text-slate-700 p-1 rounded-md transition-colors"
                              >
                                {isExpanded ? (
                                  <ChevronUp className="w-5 h-5" />
                                ) : (
                                  <ChevronDown className="w-5 h-5" />
                                )}
                              </button>
                            </td>
                          </tr>

                          {/* Expanded split view */}
                          {isExpanded && (
                            <tr className="bg-slate-50/75 border-y border-slate-100">
                              <td colSpan={7} className="px-6 py-3">
                                <div className="text-xs font-semibold text-slate-500 uppercase mb-2">
                                  Participant Split Allocations:
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                  {e.splits.map((s) => (
                                    <div
                                      key={s.id}
                                      className="bg-white p-2.5 rounded-lg border border-slate-200 flex justify-between items-center"
                                    >
                                      <span className="font-medium text-slate-700">
                                        {s.person_name}
                                      </span>
                                      <span className="font-bold text-emerald-700">
                                        {formatCentsToCurrency(
                                          s.assigned_amount_cents
                                        )}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}

      {/* Modal: Record Payment */}
      <Modal
        isOpen={isPaymentModalOpen}
        onClose={() => setIsPaymentModalOpen(false)}
        title={`Record Payment: ${selectedResident?.person_name}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            recordPayment.mutate();
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Payment Amount ($)
            </label>
            <div className="relative">
              <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="number"
                step="0.01"
                required
                value={paymentAmountStr}
                onChange={(e) => setPaymentAmountStr(e.target.value)}
                placeholder="100.00"
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Stored in backend ledger as exact integer cents.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Notes (Optional)
            </label>
            <input
              type="text"
              value={paymentNotes}
              onChange={(e) => setPaymentNotes(e.target.value)}
              placeholder="e.g. Venmo transfer #8172"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setIsPaymentModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={recordPayment.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {recordPayment.isPending ? 'Saving...' : 'Confirm Payment'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Record Debt Waiver */}
      <Modal
        isOpen={isWaiverModalOpen}
        onClose={() => setIsWaiverModalOpen(false)}
        title={`Waive Debt: ${selectedResident?.person_name}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            recordWaiver.mutate();
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Amount to Waive ($)
            </label>
            <div className="relative">
              <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="number"
                step="0.01"
                required
                value={waiverAmountStr}
                onChange={(e) => setWaiverAmountStr(e.target.value)}
                placeholder="50.00"
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-amber-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Mandatory Audit Reason
            </label>
            <textarea
              required
              rows={3}
              value={waiverReason}
              onChange={(e) => setWaiverReason(e.target.value)}
              placeholder="e.g. Mutual agreement for room painting labor offset; forgiven shortfall."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-amber-500"
            />
            <p className="text-xs text-slate-400 mt-1">
              Recorded into the immutable Debt Waiver Ledger for historical auditing.
            </p>
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setIsWaiverModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={recordWaiver.isPending}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {recordWaiver.isPending ? 'Recording...' : 'Waive Debt'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Create Billing Cycle */}
      <Modal
        isOpen={isCreateCycleModalOpen}
        onClose={() => setIsCreateCycleModalOpen(false)}
        title="Initialize New Billing Cycle"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createCycle.mutate();
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Year
              </label>
              <input
                type="number"
                required
                min={2020}
                max={2050}
                value={newCycleYear}
                onChange={(e) => setNewCycleYear(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Month
              </label>
              <select
                value={newCycleMonth}
                onChange={(e) => setNewCycleMonth(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>
                    {m} - {getMonthName(m)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg">
            Active recurring templates will automatically be copied into this cycle and divided equally among active household residents.
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateCycleModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createCycle.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {createCycle.isPending ? 'Creating...' : 'Create Cycle'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Settlement & Waiver History */}
      <Modal
        isOpen={isHistoryModalOpen}
        onClose={() => {
          setIsHistoryModalOpen(false);
          setHistoryResident(null);
        }}
        title={`Settlement History: ${historyResident?.person_name || ''}`}
      >
        <div className="space-y-4">
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setHistoryTab('payments')}
              className={`pb-2 px-4 text-sm font-medium border-b-2 transition-colors ${
                historyTab === 'payments'
                  ? 'border-emerald-500 text-emerald-600 font-semibold'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Payments ({residentPayments.length})
            </button>
            <button
              onClick={() => setHistoryTab('waivers')}
              className={`pb-2 px-4 text-sm font-medium border-b-2 transition-colors ${
                historyTab === 'waivers'
                  ? 'border-amber-500 text-amber-600 font-semibold'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Debt Waivers ({residentWaivers.length})
            </button>
          </div>

          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          {historyTab === 'payments' ? (
            paymentsLoading ? (
              <div className="text-center py-6 text-slate-400 text-xs">Loading payments...</div>
            ) : residentPayments.length === 0 ? (
              <div className="text-center py-6 text-slate-400 text-xs">
                No payments registered for this cycle.
              </div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {residentPayments.map((p) => (
                  <div
                    key={p.id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-emerald-600 text-sm">
                          {formatCentsToCurrency(p.amount_cents)}
                        </span>
                        <span className="text-xs text-slate-400">
                          {formatDate(p.paid_at)}
                        </span>
                      </div>
                      {p.notes && (
                        <p className="text-xs text-slate-600 mt-0.5">{p.notes}</p>
                      )}
                    </div>
                    {activeCycle?.status === 'OPEN' && (
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => {
                            setEditingPayment(p);
                            setEditPaymentAmountStr((p.amount_cents / 100).toFixed(2));
                            setEditPaymentNotes(p.notes || '');
                            setFormError('');
                            setIsEditPaymentModalOpen(true);
                          }}
                          className="p-1.5 text-slate-500 hover:text-emerald-600 hover:bg-white rounded-md transition-colors border border-transparent hover:border-slate-200"
                          title="Edit Payment"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {activeHousehold.role === 'ADMIN' && (
                          <button
                            onClick={() => {
                              setDeleteConfirm({
                                type: 'payment',
                                id: p.id,
                                name: `${formatCentsToCurrency(p.amount_cents)} on ${formatDate(p.paid_at)}`,
                              });
                            }}
                            className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-white rounded-md transition-colors border border-transparent hover:border-slate-200"
                            title="Delete Payment"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          ) : waiversLoading ? (
            <div className="text-center py-6 text-slate-400 text-xs">Loading waivers...</div>
          ) : residentWaivers.length === 0 ? (
            <div className="text-center py-6 text-slate-400 text-xs">
              No debt waivers registered for this cycle.
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {residentWaivers.map((w) => (
                <div
                  key={w.id}
                  className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between"
                >
                  <div className="max-w-[75%]">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-amber-600 text-sm">
                        {formatCentsToCurrency(w.amount_cents)}
                      </span>
                      <span className="text-xs text-slate-400">
                        {formatDate(w.waived_at)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 mt-0.5 italic">
                      "{w.reason}"
                    </p>
                  </div>
                  {activeCycle?.status === 'OPEN' && activeHousehold.role === 'ADMIN' && (
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => {
                          setEditingWaiver(w);
                          setEditWaiverAmountStr((w.amount_cents / 100).toFixed(2));
                          setEditWaiverReason(w.reason);
                          setFormError('');
                          setIsEditWaiverModalOpen(true);
                        }}
                        className="p-1.5 text-slate-500 hover:text-amber-600 hover:bg-white rounded-md transition-colors border border-transparent hover:border-slate-200"
                        title="Edit Waiver"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => {
                          setDeleteConfirm({
                            type: 'waiver',
                            id: w.id,
                            name: `${formatCentsToCurrency(w.amount_cents)} ("${w.reason}")`,
                          });
                        }}
                        className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-white rounded-md transition-colors border border-transparent hover:border-slate-200"
                        title="Delete Waiver"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <button
              onClick={() => {
                setIsHistoryModalOpen(false);
                setHistoryResident(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal: Edit Payment */}
      <Modal
        isOpen={isEditPaymentModalOpen}
        onClose={() => {
          setIsEditPaymentModalOpen(false);
          setEditingPayment(null);
        }}
        title={`Edit Payment (${historyResident?.person_name || ''})`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updatePayment.mutate();
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Payment Amount ($)
            </label>
            <div className="relative">
              <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="number"
                step="0.01"
                required
                value={editPaymentAmountStr}
                onChange={(e) => setEditPaymentAmountStr(e.target.value)}
                placeholder="100.00"
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Notes (Optional)
            </label>
            <input
              type="text"
              value={editPaymentNotes}
              onChange={(e) => setEditPaymentNotes(e.target.value)}
              placeholder="e.g. Bank transfer, Venmo..."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setIsEditPaymentModalOpen(false);
                setEditingPayment(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updatePayment.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {updatePayment.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Debt Waiver */}
      <Modal
        isOpen={isEditWaiverModalOpen}
        onClose={() => {
          setIsEditWaiverModalOpen(false);
          setEditingWaiver(null);
        }}
        title={`Edit Debt Waiver (${historyResident?.person_name || ''})`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateWaiver.mutate();
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Amount to Waive ($)
            </label>
            <div className="relative">
              <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="number"
                step="0.01"
                required
                value={editWaiverAmountStr}
                onChange={(e) => setEditWaiverAmountStr(e.target.value)}
                placeholder="50.00"
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-amber-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Mandatory Audit Reason
            </label>
            <textarea
              required
              rows={3}
              value={editWaiverReason}
              onChange={(e) => setEditWaiverReason(e.target.value)}
              placeholder="e.g. Mutual agreement for labor offset..."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-amber-500"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setIsEditWaiverModalOpen(false);
                setEditingWaiver(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateWaiver.isPending}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {updateWaiver.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Confirm Deletion */}
      <Modal
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        title="Confirm Deletion"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Are you sure you want to delete this {deleteConfirm?.type}:{' '}
            <span className="font-semibold text-slate-900">{deleteConfirm?.name}</span>?
          </p>
          <p className="text-xs text-slate-500">
            This action will permanently remove the record and recalculate the resident's remaining cycle balance.
          </p>
          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setDeleteConfirm(null)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deletePayment.isPending || deleteWaiver.isPending}
              onClick={() => {
                if (!deleteConfirm) return;
                if (deleteConfirm.type === 'payment') {
                  deletePayment.mutate(deleteConfirm.id);
                } else {
                  deleteWaiver.mutate(deleteConfirm.id);
                }
              }}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {deletePayment.isPending || deleteWaiver.isPending ? 'Deleting...' : 'Delete Record'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
