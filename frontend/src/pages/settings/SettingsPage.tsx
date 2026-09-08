import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  HouseholdMember,
  Person,
  PersonHistory,
  FixedExpenseTemplate,
} from '../../types';
import {
  formatCentsToCurrency,
  parseCurrencyToCents,
  formatDate,
} from '../../services/formatters';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { Modal } from '../../components/ui/Modal';
import {
  Users,
  UserPlus,
  Repeat,
  Plus,
  Trash2,
  Building,
  Shield,
  AlertCircle,
  Link2,
  Unlink,
  Mail,
  Edit2,
  RotateCcw,
  History,
} from 'lucide-react';

const getBalanceTextColor = (cents: number): string => {
  if (cents > 0) return 'text-rose-600';
  if (cents < 0) return 'text-emerald-600';
  return 'text-slate-700';
};

interface ResidentTableRowProps {
  person: Person;
  isAdmin: boolean;
  onViewHistory: (p: Person) => void;
  onRestore: (p: Person) => void;
  isRestoring: boolean;
  onEdit: (p: Person) => void;
  onUnlink: (p: Person) => void;
  isUnlinking: boolean;
  onLink: (p: Person) => void;
  onToggleActive: (personId: string, isActive: boolean) => void;
  onDelete: (p: Person) => void;
}

const ResidentTableRow: React.FC<ResidentTableRowProps> = ({
  person: p,
  isAdmin,
  onViewHistory,
  onRestore,
  isRestoring,
  onEdit,
  onUnlink,
  isUnlinking,
  onLink,
  onToggleActive,
  onDelete,
}) => {
  return (
    <tr
      key={p.id}
      className={`hover:bg-slate-50/50 transition-colors ${
        p.is_deleted ? 'bg-slate-50/70 opacity-75' : ''
      }`}
    >
      <td className="px-6 py-4">
        <div className="flex items-center space-x-2">
          <span
            className={`font-semibold ${
              p.is_deleted ? 'text-slate-500 line-through' : 'text-slate-900'
            }`}
          >
            {p.name}
          </span>
          {p.is_deleted && (
            <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 bg-rose-100 text-rose-700 rounded">
              Deleted
            </span>
          )}
        </div>
        {p.is_deleted && p.deleted_at && (
          <p className="text-[11px] text-slate-400 mt-0.5">
            Deleted on {formatDate(p.deleted_at)}
          </p>
        )}
      </td>
      <td className="px-6 py-4">
        {p.user_email ? (
          <div className="flex items-center space-x-1.5 text-slate-700 text-xs font-medium">
            <Mail className="w-3.5 h-3.5 text-slate-400" />
            <span>{p.user_email}</span>
          </div>
        ) : (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
            Standalone (No Login)
          </span>
        )}
      </td>
      <td className="px-6 py-4">
        {p.role ? (
          <StatusBadge type="role" value={p.role} />
        ) : (
          <span className="text-xs text-slate-400">—</span>
        )}
      </td>
      <td className="px-6 py-4">
        {p.is_deleted ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
            Deleted (Archived)
          </span>
        ) : (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
              p.is_active
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-500'
            }`}
          >
            {p.is_active ? 'Active' : 'Inactive'}
          </span>
        )}
      </td>
      <td className="px-6 py-4 text-right">
        <div className="flex items-center justify-end space-x-1.5">
          <button
            onClick={() => onViewHistory(p)}
            title="View Ledger & Settlement History"
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-slate-700 hover:text-indigo-700 bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded transition-colors"
          >
            <History className="w-3 h-3 text-slate-500" />
            <span>History</span>
          </button>

          {p.is_deleted && isAdmin && (
            <button
              onClick={() => onRestore(p)}
              disabled={isRestoring}
              title="Restore Deleted Resident"
              className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Restore</span>
            </button>
          )}

          {!p.is_deleted && isAdmin && (
            <>
              <button
                onClick={() => onEdit(p)}
                title="Edit Resident"
                className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-slate-700 hover:text-emerald-700 bg-slate-50 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-200 rounded transition-colors"
              >
                <Edit2 className="w-3 h-3" />
                <span>Edit</span>
              </button>

              {p.user_id ? (
                <button
                  onClick={() => onUnlink(p)}
                  disabled={isUnlinking}
                  title="Unlink User Account"
                  className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-amber-700 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded transition-colors"
                >
                  <Unlink className="w-3 h-3" />
                  <span>Unlink</span>
                </button>
              ) : (
                <button
                  onClick={() => onLink(p)}
                  title="Link Registered User Account"
                  className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded transition-colors"
                >
                  <Link2 className="w-3 h-3" />
                  <span>Link User</span>
                </button>
              )}

              <button
                onClick={() => onToggleActive(p.id, !p.is_active)}
                className={`text-xs px-2.5 py-1 rounded font-medium border transition-colors ${
                  p.is_active
                    ? 'bg-slate-50 hover:bg-amber-50 text-slate-600 hover:text-amber-700 border-slate-200'
                    : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200'
                }`}
              >
                {p.is_active ? 'Deactivate' : 'Activate'}
              </button>

              <button
                onClick={() => onDelete(p)}
                title="Delete Resident"
                className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded border border-transparent hover:border-rose-200 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
};

export const SettingsPage: React.FC = () => {
  const { activeHousehold, user } = useAuth();
  const queryClient = useQueryClient();

  const isAdmin = activeHousehold?.role === 'ADMIN';

  // Modals state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isPersonModalOpen, setIsPersonModalOpen] = useState(false);
  const [isEditPersonModalOpen, setIsEditPersonModalOpen] = useState(false);
  const [isDeletePersonModalOpen, setIsDeletePersonModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);

  const [showDeletedResidents, setShowDeletedResidents] = useState(false);

  // Edit Person states
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);
  const [editPersonName, setEditPersonName] = useState('');
  const [editPersonRole, setEditPersonRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');
  const [editPersonIsActive, setEditPersonIsActive] = useState(true);

  // Delete Person state
  const [deletingPerson, setDeletingPerson] = useState<Person | null>(null);

  // History Person state & tab
  const [historyPerson, setHistoryPerson] = useState<Person | null>(null);
  const [historyTab, setHistoryTab] = useState<'splits' | 'payments' | 'waivers'>('splits');

  // Form states
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');

  const [personName, setPersonName] = useState('');
  const [personEmail, setPersonEmail] = useState('');
  const [personRole, setPersonRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');

  const [linkingPerson, setLinkingPerson] = useState<Person | null>(null);
  const [linkEmail, setLinkEmail] = useState('');
  const [linkRole, setLinkRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');

  const [templateTitle, setTemplateTitle] = useState('');
  const [templateRecurrenceType, setTemplateRecurrenceType] = useState<'FIXED' | 'VARIABLE'>('FIXED');
  const [templateAmountStr, setTemplateAmountStr] = useState('');
  const [templateDueDay, setTemplateDueDay] = useState(1);
  const [templateCategory, setTemplateCategory] = useState('Rent');

  const [formError, setFormError] = useState('');

  // 1. Fetch Household Members
  const { data: members = [] } = useQuery<HouseholdMember[]>({
    queryKey: ['household-members', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) return [];
      const res = await api.get(
        `/households/${activeHousehold.household_id}/members`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
  });

  // 2. Fetch Household Persons (include deleted so admins can inspect audit history)
  const { data: persons = [] } = useQuery<Person[]>({
    queryKey: ['household-persons', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) return [];
      const res = await api.get(
        `/households/${activeHousehold.household_id}/persons?include_deleted=true`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
  });

  const deletedCount = persons.filter((p) => p.is_deleted).length;
  const displayedPersons = showDeletedResidents
    ? persons
    : persons.filter((p) => !p.is_deleted);

  // Person History query
  const { data: personHistory, isLoading: isHistoryLoading } = useQuery<PersonHistory>({
    queryKey: ['person-history', historyPerson?.id],
    queryFn: async () => {
      if (!historyPerson) return null;
      const res = await api.get(`/persons/${historyPerson.id}/history`);
      return res.data;
    },
    enabled: !!historyPerson && isHistoryModalOpen,
  });

  // 3. Fetch Fixed Expense Templates
  const { data: templates = [] } = useQuery<FixedExpenseTemplate[]>({
    queryKey: ['fixed-templates', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) return [];
      const res = await api.get(
        `/fixed-templates?household_id=${activeHousehold.household_id}`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
  });

  // Mutations
  const inviteMember = useMutation({
    mutationFn: async () => {
      if (!activeHousehold) return;
      await api.post(`/households/${activeHousehold.household_id}/members`, {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
    },
    onSuccess: () => {
      setIsInviteModalOpen(false);
      setInviteEmail('');
      setFormError('');
      queryClient.invalidateQueries({
        queryKey: ['household-members', activeHousehold?.household_id],
      });
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const addPerson = useMutation({
    mutationFn: async () => {
      if (!activeHousehold) return;
      if (!personName.trim()) throw new Error('Name cannot be empty.');
      await api.post(`/households/${activeHousehold.household_id}/persons`, {
        name: personName.trim(),
        email: personEmail.trim() || undefined,
        role: personEmail.trim() ? personRole : undefined,
      });
    },
    onSuccess: () => {
      setIsPersonModalOpen(false);
      setPersonName('');
      setPersonEmail('');
      setPersonRole('MEMBER');
      setFormError('');
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
      queryClient.invalidateQueries({
        queryKey: ['household-members', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const editPersonMutation = useMutation({
    mutationFn: async () => {
      if (!editingPerson) return;
      if (!editPersonName.trim()) throw new Error('Resident name cannot be empty.');
      await api.put(`/persons/${editingPerson.id}`, {
        name: editPersonName.trim(),
        role: editingPerson.user_id ? editPersonRole : undefined,
        is_active: editPersonIsActive,
      });
    },
    onSuccess: () => {
      setIsEditPersonModalOpen(false);
      setEditingPerson(null);
      setFormError('');
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
      queryClient.invalidateQueries({
        queryKey: ['household-members', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const deletePersonMutation = useMutation({
    mutationFn: async () => {
      if (!deletingPerson) return;
      await api.delete(`/persons/${deletingPerson.id}`);
    },
    onSuccess: () => {
      setIsDeletePersonModalOpen(false);
      setDeletingPerson(null);
      setFormError('');
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const restorePersonMutation = useMutation({
    mutationFn: async (personId: string) => {
      await api.post(`/persons/${personId}/restore`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || err.message);
    },
  });

  const linkUser = useMutation({
    mutationFn: async () => {
      if (!linkingPerson) return;
      if (!linkEmail.trim()) throw new Error('Email cannot be empty.');
      await api.post(`/persons/${linkingPerson.id}/link-user`, {
        email: linkEmail.trim(),
        role: linkRole,
      });
    },
    onSuccess: () => {
      setIsLinkModalOpen(false);
      setLinkingPerson(null);
      setLinkEmail('');
      setLinkRole('MEMBER');
      setFormError('');
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
      queryClient.invalidateQueries({
        queryKey: ['household-members', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const unlinkUser = useMutation({
    mutationFn: async (personId: string) => {
      await api.post(`/persons/${personId}/unlink-user`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
      queryClient.invalidateQueries({
        queryKey: ['household-members', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || err.message);
    },
  });

  const togglePersonActive = useMutation({
    mutationFn: async ({
      personId,
      isActive,
    }: {
      personId: string;
      isActive: boolean;
    }) => {
      await api.put(`/persons/${personId}`, { is_active: isActive });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['household-persons', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || err.message);
    },
  });

  const addTemplate = useMutation({
    mutationFn: async () => {
      if (!activeHousehold) return;
      const cents = parseCurrencyToCents(templateAmountStr);
      if (templateRecurrenceType === 'FIXED' && cents <= 0) {
        throw new Error('Fixed templates require an amount greater than zero.');
      }

      await api.post(`/fixed-templates?household_id=${activeHousehold.household_id}`, {
        title: templateTitle.trim(),
        recurrence_type: templateRecurrenceType,
        estimated_amount_cents: cents > 0 ? cents : null,
        due_day: Number(templateDueDay),
        category: templateCategory.trim(),
        is_active: true,
      });
    },
    onSuccess: () => {
      setIsTemplateModalOpen(false);
      setTemplateTitle('');
      setTemplateAmountStr('');
      setTemplateRecurrenceType('FIXED');
      setFormError('');
      queryClient.invalidateQueries({
        queryKey: ['fixed-templates', activeHousehold?.household_id],
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || err.message);
    },
  });

  const deleteTemplate = useMutation({
    mutationFn: async (templateId: string) => {
      await api.delete(`/fixed-templates/${templateId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['fixed-templates', activeHousehold?.household_id],
      });
    },
  });

  if (!activeHousehold) {
    return (
      <div className="text-center py-12 text-slate-500">
        Please select a household to manage settings.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-emerald-100 text-emerald-700 rounded-xl">
            <Building className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Household Settings & Directory
            </h1>
            <p className="text-sm text-slate-500">
              Manage residents, recurring fixed templates, and household permissions for{' '}
              <span className="font-semibold text-slate-700">
                {activeHousehold.household_name}
              </span>
            </p>
          </div>
        </div>
        <StatusBadge type="role" value={activeHousehold.role} />
      </div>

      {/* Section 1: Household Members */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Users className="w-4 h-4 text-emerald-600" />
              <span>Registered Household Members</span>
            </h2>
            <p className="text-xs text-slate-500">
              Users with authenticated login access to this household
            </p>
          </div>
          {isAdmin && (
            <button
              onClick={() => {
                setFormError('');
                setIsInviteModalOpen(true);
              }}
              className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              <span>Add Member</span>
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Member Name</th>
                <th className="px-6 py-3">Email</th>
                <th className="px-6 py-3">Role</th>
                <th className="px-6 py-3">Joined Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {members.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50/50">
                  <td className="px-6 py-4 font-semibold text-slate-900">
                    {m.full_name}
                    {m.user_id === user?.id && (
                      <span className="text-xs text-emerald-600 font-normal ml-2">
                        (You)
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-slate-600">{m.email}</td>
                  <td className="px-6 py-4">
                    <StatusBadge type="role" value={m.role} />
                  </td>
                  <td className="px-6 py-4 text-slate-500 text-xs">
                    {formatDate(m.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 2: Residents Directory (Persons) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Shield className="w-4 h-4 text-emerald-600" />
              <span>Resident Split Participants</span>
            </h2>
            <p className="text-xs text-slate-500">
              Managed residents in the household who participate in expense splits and settlements
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {deletedCount > 0 && (
              <button
                type="button"
                onClick={() => setShowDeletedResidents(!showDeletedResidents)}
                className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition-colors ${
                  showDeletedResidents
                    ? 'bg-amber-50 text-amber-800 border-amber-300 ring-2 ring-amber-400/20'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200'
                }`}
              >
                {showDeletedResidents ? 'Hide Deleted' : `Show Deleted (${deletedCount})`}
              </button>
            )}
            {isAdmin && (
              <button
                onClick={() => {
                  setFormError('');
                  setIsPersonModalOpen(true);
                }}
                className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Resident</span>
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Resident Name</th>
                <th className="px-6 py-3">User Account</th>
                <th className="px-6 py-3">Household Role</th>
                <th className="px-6 py-3">Resident Status</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {displayedPersons.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400 text-xs">
                    {persons.length === 0
                      ? 'No residents registered yet. Add a resident to get started.'
                      : 'No residents matching the current filter.'}
                  </td>
                </tr>
              ) : (
                displayedPersons.map((p) => (
                  <ResidentTableRow
                    key={p.id}
                    person={p}
                    isAdmin={isAdmin}
                    onViewHistory={(person) => {
                      setHistoryPerson(person);
                      setHistoryTab('splits');
                      setIsHistoryModalOpen(true);
                    }}
                    onRestore={(person) => {
                      if (
                        confirm(
                          `Restore resident "${person.name}"? They will become active again and participate in upcoming cycles.`
                        )
                      ) {
                        restorePersonMutation.mutate(person.id);
                      }
                    }}
                    isRestoring={restorePersonMutation.isPending}
                    onEdit={(person) => {
                      setFormError('');
                      setEditingPerson(person);
                      setEditPersonName(person.name);
                      setEditPersonRole((person.role as 'ADMIN' | 'MEMBER') || 'MEMBER');
                      setEditPersonIsActive(person.is_active);
                      setIsEditPersonModalOpen(true);
                    }}
                    onUnlink={(person) => {
                      if (
                        confirm(
                          `Unlink user account from resident "${person.name}"? They will become a standalone resident and won't be tied to that login account.`
                        )
                      ) {
                        unlinkUser.mutate(person.id);
                      }
                    }}
                    isUnlinking={unlinkUser.isPending}
                    onLink={(person) => {
                      setFormError('');
                      setLinkingPerson(person);
                      setLinkEmail('');
                      setLinkRole('MEMBER');
                      setIsLinkModalOpen(true);
                    }}
                    onToggleActive={(personId, isActive) =>
                      togglePersonActive.mutate({ personId, isActive })
                    }
                    onDelete={(person) => {
                      setFormError('');
                      setDeletingPerson(person);
                      setIsDeletePersonModalOpen(true);
                    }}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 3: Fixed Expense Templates (Recurring) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Repeat className="w-4 h-4 text-emerald-600" />
              <span>Recurring Fixed Expense Templates</span>
            </h2>
            <p className="text-xs text-slate-500">
              Templates that automatically instantiate upon new billing cycle creation
            </p>
          </div>
          {isAdmin && (
            <button
              onClick={() => {
                setFormError('');
                setIsTemplateModalOpen(true);
              }}
              className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Template</span>
            </button>
          )}
        </div>

        {templates.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No recurring templates configured. Add templates like Rent, Internet, or Water.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Template Title</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Category</th>
                  <th className="px-6 py-3">Contract / Est. Amount</th>
                  <th className="px-6 py-3">Due Day of Month</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {templates.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      {t.title}
                    </td>
                    <td className="px-6 py-4">
                      {t.recurrence_type === 'VARIABLE' ? (
                        <span className="px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded text-xs font-semibold">
                          Variable
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-semibold">
                          Fixed
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-medium">
                        {t.category}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-bold text-slate-900">
                      {t.estimated_amount_cents ? (
                        formatCentsToCurrency(t.estimated_amount_cents)
                      ) : (
                        <span className="text-slate-400 font-normal italic text-xs">
                          Varies each cycle
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-medium">
                      Day {t.due_day}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          t.is_active
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {t.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {isAdmin && (
                        <button
                          onClick={() => {
                            if (confirm(`Delete template "${t.title}"?`)) {
                              deleteTemplate.mutate(t.id);
                            }
                          }}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded"
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

      {/* Modal: Invite / Add Member */}
      <Modal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        title="Add Household Member"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            inviteMember.mutate();
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
              Registered User Email
            </label>
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="resident@example.com"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Assigned Role
            </label>
            <select
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
              onClick={() => setIsInviteModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inviteMember.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {inviteMember.isPending ? 'Adding...' : 'Add Member'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Add Resident Person */}
      <Modal
        isOpen={isPersonModalOpen}
        onClose={() => setIsPersonModalOpen(false)}
        title="Register New Resident Participant"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addPerson.mutate();
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
              onClick={() => setIsPersonModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={addPerson.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {addPerson.isPending ? 'Registering...' : 'Add Resident'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Resident Person */}
      <Modal
        isOpen={isEditPersonModalOpen}
        onClose={() => {
          setIsEditPersonModalOpen(false);
          setEditingPerson(null);
        }}
        title={`Edit Resident: ${editingPerson?.name || ''}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editPersonMutation.mutate();
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
                  className="text-emerald-600 focus:ring-emerald-500"
                />
                <span>Inactive (Excluded from cycles)</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setIsEditPersonModalOpen(false);
                setEditingPerson(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={editPersonMutation.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {editPersonMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Delete Resident Confirmation */}
      <Modal
        isOpen={isDeletePersonModalOpen}
        onClose={() => {
          setIsDeletePersonModalOpen(false);
          setDeletingPerson(null);
        }}
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
              onClick={() => {
                setIsDeletePersonModalOpen(false);
                setDeletingPerson(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deletePersonMutation.isPending}
              onClick={() => deletePersonMutation.mutate()}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {deletePersonMutation.isPending ? 'Deleting...' : 'Confirm Soft Delete'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal: Resident Financial & Split History */}
      <Modal
        isOpen={isHistoryModalOpen}
        onClose={() => {
          setIsHistoryModalOpen(false);
          setHistoryPerson(null);
        }}
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
              onClick={() => {
                setIsHistoryModalOpen(false);
                setHistoryPerson(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal: Link User Account to Resident */}
      <Modal
        isOpen={isLinkModalOpen}
        onClose={() => {
          setIsLinkModalOpen(false);
          setLinkingPerson(null);
        }}
        title={linkingPerson ? `Link User Account to "${linkingPerson.name}"` : 'Link User Account'}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            linkUser.mutate();
          }}
          className="space-y-4"
        >
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
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Registered User Email *
            </label>
            <input
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
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Assigned Household Role
            </label>
            <select
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
              onClick={() => {
                setIsLinkModalOpen(false);
                setLinkingPerson(null);
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={linkUser.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {linkUser.isPending ? 'Linking...' : 'Link Account'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Add Fixed Template */}
      <Modal
        isOpen={isTemplateModalOpen}
        onClose={() => setIsTemplateModalOpen(false)}
        title="Create Recurring Fixed Expense Template"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addTemplate.mutate();
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
              onClick={() => setIsTemplateModalOpen(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={addTemplate.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
            >
              {addTemplate.isPending ? 'Saving...' : 'Save Template'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
