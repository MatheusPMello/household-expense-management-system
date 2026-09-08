import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { AlertCircle, Mail } from 'lucide-react';
import { Person, PersonHistory } from '../../types';
import { formatCentsToCurrency, formatDate } from '../../services/formatters';

const getBalanceTextColor = (cents: number): string => {
  if (cents > 0) return 'text-rose-600';
  if (cents < 0) return 'text-emerald-600';
  return 'text-slate-700';
};

interface InviteMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  formError: string;
  inviteEmail: string;
  setInviteEmail: (val: string) => void;
  inviteRole: 'ADMIN' | 'MEMBER';
  setInviteRole: (val: 'ADMIN' | 'MEMBER') => void;
  isPending: boolean;
}

export const InviteMemberModal: React.FC<InviteMemberModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  formError,
  inviteEmail,
  setInviteEmail,
  inviteRole,
  setInviteRole,
  isPending,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title="Add Household Member">
    <form onSubmit={onSubmit} className="space-y-4">
      {formError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div>
        <label htmlFor="invite-member-email" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Registered User Email
        </label>
        <input
          id="invite-member-email"
          type="email"
          required
          value={inviteEmail}
          onChange={(e) => setInviteEmail(e.target.value)}
          placeholder="resident@example.com"
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        />
      </div>

      <div>
        <label htmlFor="invite-member-role" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Assigned Role
        </label>
        <select
          id="invite-member-role"
          value={inviteRole}
          onChange={(e) => setInviteRole(e.target.value as 'ADMIN' | 'MEMBER')}
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        >
          <option value="MEMBER">MEMBER (Standard Access)</option>
          <option value="ADMIN">ADMIN (Full Household Privileges)</option>
        </select>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
        >
          {isPending ? 'Adding...' : 'Add Member'}
        </button>
      </div>
    </form>
  </Modal>
);

interface AddPersonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  formError: string;
  personName: string;
  setPersonName: (val: string) => void;
  personEmail: string;
  setPersonEmail: (val: string) => void;
  personRole: 'ADMIN' | 'MEMBER';
  setPersonRole: (val: 'ADMIN' | 'MEMBER') => void;
  isPending: boolean;
}

export const AddPersonModal: React.FC<AddPersonModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  formError,
  personName,
  setPersonName,
  personEmail,
  setPersonEmail,
  personRole,
  setPersonRole,
  isPending,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title="Register New Resident Participant">
    <form onSubmit={onSubmit} className="space-y-4">
      {formError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div>
        <label htmlFor="add-resident-name" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Resident Full Name *
        </label>
        <input
          id="add-resident-name"
          type="text"
          required
          value={personName}
          onChange={(e) => setPersonName(e.target.value)}
          placeholder="e.g. Jordan Lee"
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        />
      </div>

      <div>
        <label htmlFor="add-resident-email" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Registered User Email (Optional)
        </label>
        <input
          id="add-resident-email"
          type="email"
          value={personEmail}
          onChange={(e) => setPersonEmail(e.target.value)}
          placeholder="user@example.com (leave blank if no account yet)"
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        />
        <p className="text-xs text-slate-500 mt-1">
          Leave blank to add as a standalone resident. If they register an account later, an administrator can link it at any time.
        </p>
      </div>

      {personEmail.trim() && (
        <div>
          <label htmlFor="add-resident-role" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
            Assigned Household Role
          </label>
          <select
            id="add-resident-role"
            value={personRole}
            onChange={(e) => setPersonRole(e.target.value as 'ADMIN' | 'MEMBER')}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
          >
            <option value="MEMBER">MEMBER (Standard Access)</option>
            <option value="ADMIN">ADMIN (Full Household Privileges)</option>
          </select>
        </div>
      )}

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
        >
          {isPending ? 'Registering...' : 'Add Resident'}
        </button>
      </div>
    </form>
  </Modal>
);

interface EditPersonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  formError: string;
  editingPerson: Person | null;
  editPersonName: string;
  setEditPersonName: (val: string) => void;
  editPersonRole: 'ADMIN' | 'MEMBER';
  setEditPersonRole: (val: 'ADMIN' | 'MEMBER') => void;
  editPersonIsActive: boolean;
  setEditPersonIsActive: (val: boolean) => void;
  isPending: boolean;
}

export const EditPersonModal: React.FC<EditPersonModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  formError,
  editingPerson,
  editPersonName,
  setEditPersonName,
  editPersonRole,
  setEditPersonRole,
  editPersonIsActive,
  setEditPersonIsActive,
  isPending,
}) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title={`Edit Resident: ${editingPerson?.name || ''}`}
  >
    <form onSubmit={onSubmit} className="space-y-4">
      {formError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div>
        <label htmlFor="edit-resident-name" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Resident Full Name *
        </label>
        <input
          id="edit-resident-name"
          type="text"
          required
          value={editPersonName}
          onChange={(e) => setEditPersonName(e.target.value)}
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        />
      </div>

      {editingPerson?.user_email && (
        <div>
          <span className="block text-xs font-semibold text-slate-700 uppercase mb-1">
            Linked User Account
          </span>
          <div className="px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-600 flex items-center space-x-2">
            <Mail className="w-3.5 h-3.5 text-slate-400" />
            <span>{editingPerson.user_email}</span>
          </div>
        </div>
      )}

      {editingPerson?.user_id && (
        <div>
          <label htmlFor="edit-resident-role" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
            Assigned Household Role
          </label>
          <select
            id="edit-resident-role"
            value={editPersonRole}
            onChange={(e) => setEditPersonRole(e.target.value as 'ADMIN' | 'MEMBER')}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
          >
            <option value="MEMBER">MEMBER (Standard Access)</option>
            <option value="ADMIN">ADMIN (Full Household Privileges)</option>
          </select>
        </div>
      )}

      <div>
        <span className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Participation Status
        </span>
        <div className="flex items-center space-x-4 mt-1">
          <label className="flex items-center space-x-2 cursor-pointer text-sm text-slate-700">
            <input
              type="radio"
              name="editPersonActive"
              checked={editPersonIsActive}
              onChange={() => setEditPersonIsActive(true)}
              className="text-emerald-600 focus:ring-emerald-500"
            />
            <span>Active (Included in cycles)</span>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer text-sm text-slate-700">
            <input
              type="radio"
              name="editPersonActive"
              checked={!editPersonIsActive}
              onChange={() => setEditPersonIsActive(false)}
              className="text-slate-500 focus:ring-slate-500"
            />
            <span>Inactive (Temporarily away)</span>
          </label>
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
        >
          {isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  </Modal>
);

interface DeletePersonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  formError: string;
  deletingPerson: Person | null;
  isPending: boolean;
}

export const DeletePersonModal: React.FC<DeletePersonModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  formError,
  deletingPerson,
  isPending,
}) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title={`Delete Resident: ${deletingPerson?.name || ''}`}
  >
    <div className="space-y-4">
      {formError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs space-y-2">
        <p className="font-semibold text-sm text-amber-950">
          Safe Ledger Soft-Deletion
        </p>
        <p>
          Are you sure you want to delete resident <span className="font-bold">{deletingPerson?.name}</span>?
        </p>
        <p className="text-amber-800">
          To guarantee accounting and audit integrity, their complete transaction history (assigned expense splits, payments recorded, debt waivers, and past cycle balances) will be <strong>permanently stored and preserved in the ledger</strong>.
        </p>
        <p className="text-amber-800">
          They will be excluded from future billing cycles and new expense split calculations. You can view their historical ledger or restore them at any time from the "Show Deleted" filter.
        </p>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={isPending}
          onClick={onConfirm}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
        >
          {isPending ? 'Deleting...' : 'Confirm Soft Delete'}
        </button>
      </div>
    </div>
  </Modal>
);

interface PersonHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  historyPerson: Person | null;
  personHistory: PersonHistory | undefined;
  isHistoryLoading: boolean;
  historyTab: 'splits' | 'payments' | 'waivers';
  setHistoryTab: (val: 'splits' | 'payments' | 'waivers') => void;
}

export const PersonHistoryModal: React.FC<PersonHistoryModalProps> = ({
  isOpen,
  onClose,
  historyPerson,
  personHistory,
  isHistoryLoading,
  historyTab,
  setHistoryTab,
}) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title={`Financial & Split History: ${historyPerson?.name || ''}`}
  >
    <div className="space-y-5 max-h-[75vh] overflow-y-auto pr-1">
      {/* Header Card */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-bold text-slate-900">
              {historyPerson?.name}
            </span>
            {historyPerson?.is_deleted ? (
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 bg-rose-100 text-rose-700 rounded-full">
                Deleted (Archived)
              </span>
            ) : (
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full">
                {historyPerson?.is_active ? 'Active' : 'Inactive'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {historyPerson?.user_email || 'Standalone Resident'} • Joined {historyPerson ? formatDate(historyPerson.created_at) : ''}
          </p>
        </div>
        {historyPerson?.is_deleted && historyPerson?.deleted_at && (
          <span className="text-xs text-slate-400">
            Deleted on {formatDate(historyPerson.deleted_at)}
          </span>
        )}
      </div>

      {/* Stats Cards */}
      {personHistory && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-center">
          <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-2xs">
            <p className="text-[11px] font-semibold text-slate-500 uppercase">Assigned</p>
            <p className="text-sm font-bold text-slate-900 mt-1">
              {formatCentsToCurrency(personHistory.total_assigned_cents)}
            </p>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-2xs">
            <p className="text-[11px] font-semibold text-emerald-600 uppercase">Total Paid</p>
            <p className="text-sm font-bold text-emerald-700 mt-1">
              {formatCentsToCurrency(personHistory.total_paid_cents)}
            </p>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-2xs">
            <p className="text-[11px] font-semibold text-purple-600 uppercase">Total Waived</p>
            <p className="text-sm font-bold text-purple-700 mt-1">
              {formatCentsToCurrency(personHistory.total_waived_cents)}
            </p>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-2xs">
            <p className="text-[11px] font-semibold text-slate-500 uppercase">Net Balance</p>
            <p className={`text-sm font-bold mt-1 ${getBalanceTextColor(personHistory.outstanding_balance_cents)}`}>
              {formatCentsToCurrency(personHistory.outstanding_balance_cents)}
            </p>
          </div>
        </div>
      )}

      {/* Tab buttons */}
      <div className="flex border-b border-slate-200 space-x-4 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setHistoryTab('splits')}
          className={`pb-2 border-b-2 transition-colors ${
            historyTab === 'splits'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Expense Splits ({personHistory?.splits?.length || 0})
        </button>
        <button
          type="button"
          onClick={() => setHistoryTab('payments')}
          className={`pb-2 border-b-2 transition-colors ${
            historyTab === 'payments'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Payments ({personHistory?.payments?.length || 0})
        </button>
        <button
          type="button"
          onClick={() => setHistoryTab('waivers')}
          className={`pb-2 border-b-2 transition-colors ${
            historyTab === 'waivers'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Debt Waivers ({personHistory?.debt_waivers?.length || 0})
        </button>
      </div>

      {/* Tab content */}
      {isHistoryLoading ? (
        <div className="py-8 text-center text-xs text-slate-400">Loading history ledger...</div>
      ) : (
        <div>
          {historyTab === 'splits' && (
            <div className="space-y-2">
              {!personHistory?.splits || personHistory.splits.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-400">No expense splits recorded.</div>
              ) : (
                personHistory.splits.map((s) => (
                  <div
                    key={s.expense_id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-semibold text-slate-800">{s.expense_title}</p>
                      <p className="text-slate-500 text-[11px] mt-0.5">
                        {s.category} • Cycle {s.cycle_year}-{String(s.cycle_month).padStart(2, '0')} • Due {formatDate(s.due_date)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-slate-900">{formatCentsToCurrency(s.assigned_amount_cents)}</p>
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                          s.is_paid ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {s.is_paid ? 'Cycle Paid' : 'Pending Cycle Payment'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {historyTab === 'payments' && (
            <div className="space-y-2">
              {!personHistory?.payments || personHistory.payments.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-400">No payments recorded.</div>
              ) : (
                personHistory.payments.map((p) => (
                  <div
                    key={p.id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-semibold text-emerald-800">
                        Payment • {formatDate(p.paid_at)}
                      </p>
                      <p className="text-slate-500 text-[11px] mt-0.5">
                        Cycle {p.cycle_year}-{String(p.cycle_month).padStart(2, '0')}
                        {p.notes ? ` • "${p.notes}"` : ''}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-emerald-700">{formatCentsToCurrency(p.amount_cents)}</p>
                      {p.proof_url && (
                        <a
                          href={p.proof_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-indigo-600 hover:underline"
                        >
                          View Proof
                        </a>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {historyTab === 'waivers' && (
            <div className="space-y-2">
              {!personHistory?.debt_waivers || personHistory.debt_waivers.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-400">No debt waivers recorded.</div>
              ) : (
                personHistory.debt_waivers.map((w) => (
                  <div
                    key={w.id}
                    className="p-3 bg-purple-50/60 border border-purple-200 rounded-lg flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-semibold text-purple-900">
                        Debt Waiver • {formatDate(w.waived_at)}
                      </p>
                      <p className="text-slate-600 text-[11px] mt-0.5">
                        Cycle {w.cycle_year}-{String(w.cycle_month).padStart(2, '0')} • <span className="italic font-medium">"{w.reason}"</span>
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-purple-700">{formatCentsToCurrency(w.amount_cents)}</p>
                      <span className="text-[10px] font-semibold text-purple-600 uppercase tracking-wider">
                        Audited Forgiveness
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Close
        </button>
      </div>
    </div>
  </Modal>
);

interface LinkUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  formError: string;
  linkingPerson: Person | null;
  linkEmail: string;
  setLinkEmail: (val: string) => void;
  linkRole: 'ADMIN' | 'MEMBER';
  setLinkRole: (val: 'ADMIN' | 'MEMBER') => void;
  isPending: boolean;
}

export const LinkUserModal: React.FC<LinkUserModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  formError,
  linkingPerson,
  linkEmail,
  setLinkEmail,
  linkRole,
  setLinkRole,
  isPending,
}) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title={linkingPerson ? `Link User Account to "${linkingPerson.name}"` : 'Link User Account'}
  >
    <form onSubmit={onSubmit} className="space-y-4">
      {formError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
        Link this resident profile to an existing registered user. They will be granted access to this household and their historical balance and splits will remain intact.
      </div>

      <div>
        <label htmlFor="link-user-email" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Registered User Email *
        </label>
        <input
          id="link-user-email"
          type="email"
          required
          value={linkEmail}
          onChange={(e) => setLinkEmail(e.target.value)}
          placeholder="e.g. resident@example.com"
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        />
        <p className="text-xs text-slate-500 mt-1">
          The user must already have a registered account on the platform.
        </p>
      </div>

      <div>
        <label htmlFor="link-user-role" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Assigned Household Role
        </label>
        <select
          id="link-user-role"
          value={linkRole}
          onChange={(e) => setLinkRole(e.target.value as 'ADMIN' | 'MEMBER')}
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        >
          <option value="MEMBER">MEMBER (Standard Access)</option>
          <option value="ADMIN">ADMIN (Full Household Privileges)</option>
        </select>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
        >
          {isPending ? 'Linking...' : 'Link Account'}
        </button>
      </div>
    </form>
  </Modal>
);

interface CreateTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  formError: string;
  templateTitle: string;
  setTemplateTitle: (val: string) => void;
  templateRecurrenceType: 'FIXED' | 'VARIABLE';
  setTemplateRecurrenceType: (val: 'FIXED' | 'VARIABLE') => void;
  templateAmountStr: string;
  setTemplateAmountStr: (val: string) => void;
  templateDueDay: number;
  setTemplateDueDay: (val: number) => void;
  templateCategory: string;
  setTemplateCategory: (val: string) => void;
  isPending: boolean;
}

export const CreateTemplateModal: React.FC<CreateTemplateModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  formError,
  templateTitle,
  setTemplateTitle,
  templateRecurrenceType,
  setTemplateRecurrenceType,
  templateAmountStr,
  setTemplateAmountStr,
  templateDueDay,
  setTemplateDueDay,
  templateCategory,
  setTemplateCategory,
  isPending,
}) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title="Create Recurring Fixed Expense Template"
  >
    <form onSubmit={onSubmit} className="space-y-4">
      {formError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div>
        <label htmlFor="template-title" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Template Title
        </label>
        <input
          id="template-title"
          type="text"
          required
          value={templateTitle}
          onChange={(e) => setTemplateTitle(e.target.value)}
          placeholder="e.g. Monthly Rent, Fiber Internet"
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        />
      </div>

      <div>
        <span className="block text-xs font-semibold text-slate-700 uppercase mb-1.5">
          Recurrence Type
        </span>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setTemplateRecurrenceType('FIXED')}
            className={`py-2 px-3 text-xs font-semibold rounded-lg border text-left transition-all ${
              templateRecurrenceType === 'FIXED'
                ? 'border-emerald-600 bg-emerald-50 text-emerald-900 ring-2 ring-emerald-500/20'
                : 'border-slate-200 hover:bg-slate-50 text-slate-700'
            }`}
          >
            Fixed Recurring
          </button>
          <button
            type="button"
            onClick={() => setTemplateRecurrenceType('VARIABLE')}
            className={`py-2 px-3 text-xs font-semibold rounded-lg border text-left transition-all ${
              templateRecurrenceType === 'VARIABLE'
                ? 'border-emerald-600 bg-emerald-50 text-emerald-900 ring-2 ring-emerald-500/20'
                : 'border-slate-200 hover:bg-slate-50 text-slate-700'
            }`}
          >
            Variable Recurring (e.g. Electricity)
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="template-amount" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
            {templateRecurrenceType === 'VARIABLE'
              ? 'Estimated Amount ($) (Optional)'
              : 'Contract Amount ($)'}
          </label>
          <input
            id="template-amount"
            type="number"
            step="0.01"
            required={templateRecurrenceType === 'FIXED'}
            value={templateAmountStr}
            onChange={(e) => setTemplateAmountStr(e.target.value)}
            placeholder={templateRecurrenceType === 'VARIABLE' ? 'e.g. 150.00 (optional)' : '1200.00'}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
          />
        </div>

        <div>
          <label htmlFor="template-due-day" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
            Due Day (1-31)
          </label>
          <input
            id="template-due-day"
            type="number"
            min={1}
            max={31}
            required
            value={templateDueDay}
            onChange={(e) => setTemplateDueDay(Number(e.target.value))}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
          />
        </div>
      </div>

      <div>
        <label htmlFor="template-category" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
          Category
        </label>
        <select
          id="template-category"
          value={templateCategory}
          onChange={(e) => setTemplateCategory(e.target.value)}
          className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
        >
          <option value="Rent">Rent & Lease</option>
          <option value="Utilities">Utilities (Water, Power, Gas)</option>
          <option value="Internet">Internet & Cable</option>
          <option value="Streaming">Streaming Services</option>
          <option value="Maintenance">Recurring Maintenance</option>
          <option value="Other">Other</option>
        </select>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
        >
          {isPending ? 'Saving...' : 'Save Template'}
        </button>
      </div>
    </form>
  </Modal>
);
