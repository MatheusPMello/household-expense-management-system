import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  BillingCycle,
  Expense,
  Person,
  SplitType,
} from '../../types';
import {
  formatCentsToCurrency,
  parseCurrencyToCents,
  formatDate,
  getMonthName,
} from '../../services/formatters';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { Modal } from '../../components/ui/Modal';
import {
  Plus,
  Receipt,
  Trash2,
  AlertCircle,
  Calculator,
  Users,
} from 'lucide-react';

export const ExpensesPage: React.FC = () => {
  const { activeHousehold } = useAuth();
  const queryClient = useQueryClient();

  const [selectedCycleId, setSelectedCycleId] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Form states
  const [title, setTitle] = useState('');
  const [totalAmountStr, setTotalAmountStr] = useState('');
  const [category, setCategory] = useState('Groceries');
  const [dueDate, setDueDate] = useState(new Date().toISOString().split('T')[0]);
  const [isFixed, setIsFixed] = useState(false);
  const [splitType, setSplitType] = useState<SplitType>('EQUAL');

  // Participants selection & distribution inputs
  const [selectedPersonIds, setSelectedPersonIds] = useState<string[]>([]);
  const [percentages, setPercentages] = useState<Record<string, number>>({});
  const [exactAmountsStr, setExactAmountsStr] = useState<Record<string, string>>({});
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [formError, setFormError] = useState('');

  // 1. Fetch cycles
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

  const activeCycle =
    cycles.find((c) => c.id === selectedCycleId) || cycles[0] || null;

  // 2. Fetch persons in household
  const { data: persons = [] } = useQuery<Person[]>({
    queryKey: ['persons', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) return [];
      const res = await api.get<Person[]>(
        `/households/${activeHousehold.household_id}/persons`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
  });

  // 3. Fetch expenses for the cycle
  const { data: cycleReport, isLoading: expensesLoading } = useQuery({
    queryKey: ['cycle-report', activeCycle?.id],
    queryFn: async () => {
      if (!activeCycle) return null;
      const res = await api.get(`/reports/current-cycle?cycle_id=${activeCycle.id}`);
      return res.data;
    },
    enabled: !!activeCycle,
  });

  const expenses: Expense[] = cycleReport?.expenses || [];

  // Initialize selected persons when persons load
  React.useEffect(() => {
    if (persons.length > 0 && selectedPersonIds.length === 0) {
      const activeIds = persons.filter((p) => p.is_active).map((p) => p.id);
      setSelectedPersonIds(activeIds);

      // Default equal percentages
      const equalPct = activeIds.length > 0 ? +(100 / activeIds.length).toFixed(2) : 0;
      const initialPcts: Record<string, number> = {};
      const initialWeights: Record<string, number> = {};
      activeIds.forEach((id) => {
        initialPcts[id] = equalPct;
        initialWeights[id] = 1;
      });
      setPercentages(initialPcts);
      setWeights(initialWeights);
    }
  }, [persons]);

  // Client-side Split Preview Calculation
  const splitPreview = useMemo(() => {
    const totalCents = parseCurrencyToCents(totalAmountStr);
    if (totalCents <= 0 || selectedPersonIds.length === 0) return [];

    if (splitType === 'EQUAL') {
      const n = selectedPersonIds.length;
      const q = Math.floor(totalCents / n);
      const r = totalCents % n;
      return selectedPersonIds.map((pid, idx) => {
        const assigned = q + (idx < r ? 1 : 0);
        const person = persons.find((p) => p.id === pid);
        return {
          personId: pid,
          name: person?.name || 'Resident',
          cents: assigned,
        };
      });
    }

    if (splitType === 'PERCENTAGE') {
      const selectedPersons = selectedPersonIds.map((pid) => ({
        pid,
        pct: percentages[pid] || 0,
      }));
      let baseSum = 0;
      const allocs = selectedPersons.map((sp) => {
        const exact = totalCents * (sp.pct / 100);
        const floor = Math.floor(exact);
        baseSum += floor;
        return {
          pid: sp.pid,
          pct: sp.pct,
          floor,
          fraction: exact - floor,
        };
      });
      allocs.sort((a, b) => b.pct - a.pct || b.fraction - a.fraction);
      const leftover = totalCents - baseSum;
      for (let i = 0; i < leftover; i++) {
        allocs[i % allocs.length].floor += 1;
      }
      return allocs.map((a) => ({
        personId: a.pid,
        name: persons.find((p) => p.id === a.pid)?.name || 'Resident',
        cents: a.floor,
      }));
    }

    if (splitType === 'EXACT') {
      return selectedPersonIds.map((pid) => {
        const amtStr = exactAmountsStr[pid] || '0';
        const cents = parseCurrencyToCents(amtStr);
        const person = persons.find((p) => p.id === pid);
        return {
          personId: pid,
          name: person?.name || 'Resident',
          cents,
        };
      });
    }

    if (splitType === 'WEIGHTED') {
      const totalWeight = selectedPersonIds.reduce(
        (sum, pid) => sum + (weights[pid] || 0),
        0
      );
      if (totalWeight <= 0) return [];
      let baseSum = 0;
      const allocs = selectedPersonIds.map((pid) => {
        const w = weights[pid] || 0;
        const exact = totalCents * (w / totalWeight);
        const floor = Math.floor(exact);
        baseSum += floor;
        return { pid, w, floor, fraction: exact - floor };
      });
      allocs.sort((a, b) => b.w - a.w || b.fraction - a.fraction);
      const leftover = totalCents - baseSum;
      for (let i = 0; i < leftover; i++) {
        allocs[i % allocs.length].floor += 1;
      }
      return allocs.map((a) => ({
        personId: a.pid,
        name: persons.find((p) => p.id === a.pid)?.name || 'Resident',
        cents: a.floor,
      }));
    }

    return [];
  }, [
    totalAmountStr,
    splitType,
    selectedPersonIds,
    percentages,
    exactAmountsStr,
    weights,
    persons,
  ]);

  const previewSumCents = splitPreview.reduce((sum, s) => sum + s.cents, 0);
  const targetTotalCents = parseCurrencyToCents(totalAmountStr);

  // Mutations
  const createExpense = useMutation({
    mutationFn: async () => {
      if (!activeCycle) throw new Error('No cycle selected.');
      const cents = parseCurrencyToCents(totalAmountStr);
      if (cents <= 0) throw new Error('Amount must be greater than zero.');
      if (selectedPersonIds.length === 0)
        throw new Error('At least one participant must be selected.');

      const payload: any = {
        billing_cycle_id: activeCycle.id,
        title: title.trim(),
        total_amount_cents: cents,
        is_fixed: isFixed,
        category: category.trim(),
        due_date: dueDate,
        split_type: splitType,
      };

      if (splitType === 'EQUAL') {
        payload.participant_ids = selectedPersonIds;
      } else if (splitType === 'PERCENTAGE') {
        const pcts: Record<string, number> = {};
        selectedPersonIds.forEach((pid) => {
          pcts[pid] = Number(percentages[pid] || 0);
        });
        payload.percentages = pcts;
      } else if (splitType === 'EXACT') {
        const exacts: Record<string, number> = {};
        selectedPersonIds.forEach((pid) => {
          exacts[pid] = parseCurrencyToCents(exactAmountsStr[pid] || '0');
        });
        payload.exact_amounts = exacts;
      } else if (splitType === 'WEIGHTED') {
        const wts: Record<string, number> = {};
        selectedPersonIds.forEach((pid) => {
          wts[pid] = Number(weights[pid] || 1);
        });
        payload.weights = wts;
      }

      await api.post('/expenses', payload);
    },
    onSuccess: () => {
      setIsCreateModalOpen(false);
      setTitle('');
      setTotalAmountStr('');
      setFormError('');
      queryClient.invalidateQueries({ queryKey: ['cycle-report', activeCycle?.id] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const deleteExpense = useMutation({
    mutationFn: async (expenseId: string) => {
      await api.delete(`/expenses/${expenseId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cycle-report', activeCycle?.id] });
      queryClient.invalidateQueries({ queryKey: ['cycles', activeHousehold?.household_id] });
    },
  });

  const togglePersonSelection = (personId: string) => {
    if (selectedPersonIds.includes(personId)) {
      setSelectedPersonIds(selectedPersonIds.filter((id) => id !== personId));
    } else {
      setSelectedPersonIds([...selectedPersonIds, personId]);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-emerald-100 rounded-lg text-emerald-700">
            <Receipt className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Cycle Expenses & Split Management
            </h1>
            <p className="text-xs text-slate-500">
              Register variable ad-hoc expenses with precision split algorithms
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {cycles.length > 0 && (
            <select
              value={activeCycle?.id || ''}
              onChange={(e) => setSelectedCycleId(e.target.value)}
              className="text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-2"
            >
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>
                  {getMonthName(c.month)} {c.year}
                </option>
              ))}
            </select>
          )}

          {activeCycle && activeCycle.status === 'OPEN' && (
            <button
              onClick={() => {
                setFormError('');
                setIsCreateModalOpen(true);
              }}
              className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Expense</span>
            </button>
          )}
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-bold text-slate-900">
            Expenses in {activeCycle ? `${getMonthName(activeCycle.month)} ${activeCycle.year}` : 'Cycle'}
          </h2>
          <span className="text-xs text-slate-400 font-medium">
            {expenses.length} Total Expense(s)
          </span>
        </div>

        {expensesLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
          </div>
        ) : expenses.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No expenses found for this billing cycle. Click "+ Add Expense" to register one.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Expense Title</th>
                  <th className="px-6 py-3">Category</th>
                  <th className="px-6 py-3">Due Date</th>
                  <th className="px-6 py-3">Total Amount</th>
                  <th className="px-6 py-3">Split Method</th>
                  <th className="px-6 py-3">Vendor Settlement</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {expenses.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-900">
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
                      <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md text-xs font-medium">
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
                      <StatusBadge type="split" value={e.split_type} />
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge
                        type="vendor"
                        value={e.paid_to_vendor ? 'Paid' : 'Pending'}
                      />
                    </td>
                    <td className="px-6 py-4 text-right">
                      {activeCycle?.status === 'OPEN' && (
                        <button
                          onClick={() => {
                            if (
                              confirm(
                                `Are you sure you want to delete expense "${e.title}"?`
                              )
                            ) {
                              deleteExpense.mutate(e.id);
                            }
                          }}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                          title="Delete expense"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Create Expense with Penny-Perfect Split Engine */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Register New Household Expense"
        maxWidth="lg"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createExpense.mutate();
          }}
          className="space-y-5"
        >
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Expense Title
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Front Gate Repair, WiFi"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Total Amount ($)
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={totalAmountStr}
                onChange={(e) => setTotalAmountStr(e.target.value)}
                placeholder="120.00"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
              >
                <option value="Groceries">Groceries</option>
                <option value="Utilities">Utilities</option>
                <option value="Maintenance">Maintenance</option>
                <option value="Internet">Internet & Tech</option>
                <option value="Cleaning">Cleaning & Supplies</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Due Date
              </label>
              <input
                type="date"
                required
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="isFixedCheckbox"
              checked={isFixed}
              onChange={(e) => setIsFixed(e.target.checked)}
              className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
            />
            <label htmlFor="isFixedCheckbox" className="text-xs font-medium text-slate-700 cursor-pointer">
              Mark as Fixed Recurring Expense (e.g. Monthly utility contract)
            </label>
          </div>

          {/* Split Type Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1.5">
              Split Engine Algorithm
            </label>
            <div className="grid grid-cols-4 gap-2">
              {(['EQUAL', 'PERCENTAGE', 'EXACT', 'WEIGHTED'] as SplitType[]).map(
                (type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setSplitType(type)}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                      splitType === type
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                        : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {type}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Participants Selection & Config */}
          <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 uppercase flex items-center space-x-1.5">
                <Users className="w-4 h-4 text-emerald-600" />
                <span>Select Participating Residents</span>
              </span>
              <span className="text-xs text-slate-500">
                {selectedPersonIds.length} Selected
              </span>
            </div>

            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {persons.map((p) => {
                const isSelected = selectedPersonIds.includes(p.id);
                return (
                  <div
                    key={p.id}
                    className={`flex items-center justify-between p-2.5 rounded-lg border transition-colors ${
                      isSelected
                        ? 'bg-white border-emerald-200 shadow-2xs'
                        : 'bg-slate-100/50 border-transparent opacity-60'
                    }`}
                  >
                    <label className="flex items-center space-x-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => togglePersonSelection(p.id)}
                        className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                      />
                      <span className="text-sm font-medium text-slate-800">
                        {p.name}
                      </span>
                    </label>

                    {/* Conditional inputs per split type */}
                    {isSelected && splitType === 'PERCENTAGE' && (
                      <div className="flex items-center space-x-1">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="100"
                          value={percentages[p.id] ?? ''}
                          onChange={(e) =>
                            setPercentages({
                              ...percentages,
                              [p.id]: parseFloat(e.target.value) || 0,
                            })
                          }
                          className="w-16 px-2 py-1 text-xs border border-slate-300 rounded text-right"
                          placeholder="%"
                        />
                        <span className="text-xs text-slate-400">%</span>
                      </div>
                    )}

                    {isSelected && splitType === 'EXACT' && (
                      <div className="flex items-center space-x-1">
                        <span className="text-xs text-slate-400">$</span>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={exactAmountsStr[p.id] ?? ''}
                          onChange={(e) =>
                            setExactAmountsStr({
                              ...exactAmountsStr,
                              [p.id]: e.target.value,
                            })
                          }
                          className="w-20 px-2 py-1 text-xs border border-slate-300 rounded text-right"
                          placeholder="0.00"
                        />
                      </div>
                    )}

                    {isSelected && splitType === 'WEIGHTED' && (
                      <div className="flex items-center space-x-1">
                        <span className="text-xs text-slate-400">Weight:</span>
                        <input
                          type="number"
                          step="1"
                          min="1"
                          value={weights[p.id] ?? 1}
                          onChange={(e) =>
                            setWeights({
                              ...weights,
                              [p.id]: parseFloat(e.target.value) || 1,
                            })
                          }
                          className="w-16 px-2 py-1 text-xs border border-slate-300 rounded text-right"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-time Penny-Perfect Split Preview */}
          {splitPreview.length > 0 && (
            <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-200 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-emerald-800 flex items-center space-x-1">
                  <Calculator className="w-4 h-4 text-emerald-600" />
                  <span>Calculated Penny-Perfect Split Allocations:</span>
                </span>
                <span
                  className={`font-semibold ${
                    previewSumCents === targetTotalCents
                      ? 'text-emerald-700'
                      : 'text-rose-600'
                  }`}
                >
                  Total: {formatCentsToCurrency(previewSumCents)} / {formatCentsToCurrency(targetTotalCents)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                {splitPreview.map((item) => (
                  <div
                    key={item.personId}
                    className="bg-white px-3 py-1.5 rounded-lg border border-emerald-100 flex justify-between text-xs"
                  >
                    <span className="font-medium text-slate-700 truncate">
                      {item.name}
                    </span>
                    <span className="font-bold text-emerald-700 ml-2">
                      {formatCentsToCurrency(item.cents)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createExpense.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {createExpense.isPending ? 'Splitting...' : 'Create & Split Expense'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
