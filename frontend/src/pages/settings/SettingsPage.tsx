import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  HouseholdMember,
  Person,
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
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { activeHousehold, user } = useAuth();
  const queryClient = useQueryClient();

  const isAdmin = activeHousehold?.role === 'ADMIN';

  // Modals state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isPersonModalOpen, setIsPersonModalOpen] = useState(false);
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);

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

  // 2. Fetch Household Persons
  const { data: persons = [] } = useQuery<Person[]>({
    queryKey: ['household-persons', activeHousehold?.household_id],
    queryFn: async () => {
      if (!activeHousehold) return [];
      const res = await api.get(
        `/households/${activeHousehold.household_id}/persons`
      );
      return res.data;
    },
    enabled: !!activeHousehold,
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
      if (cents <= 0) throw new Error('Estimated amount must be greater than zero.');

      await api.post(`/fixed-templates?household_id=${activeHousehold.household_id}`, {
        title: templateTitle.trim(),
        estimated_amount_cents: cents,
        due_day: Number(templateDueDay),
        category: templateCategory.trim(),
        is_active: true,
      });
    },
    onSuccess: () => {
      setIsTemplateModalOpen(false);
      setTemplateTitle('');
      setTemplateAmountStr('');
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
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Shield className="w-4 h-4 text-emerald-600" />
              <span>Resident Split Participants</span>
            </h2>
            <p className="text-xs text-slate-500">
              Managed residents in the household who participate in expense splits and settlements
            </p>
          </div>
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
              {persons.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/50">
                  <td className="px-6 py-4 font-semibold text-slate-900">
                    {p.name}
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
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        p.is_active
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {p.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      {isAdmin && (
                        <>
                          {p.user_id ? (
                            <button
                              onClick={() => {
                                if (
                                  confirm(
                                    `Unlink user account from resident "${p.name}"? They will become a standalone resident and won't be tied to that login account.`
                                  )
                                ) {
                                  unlinkUser.mutate(p.id);
                                }
                              }}
                              disabled={unlinkUser.isPending}
                              title="Unlink User Account"
                              className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-amber-700 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded transition-colors"
                            >
                              <Unlink className="w-3 h-3" />
                              <span>Unlink</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => {
                                setFormError('');
                                setLinkingPerson(p);
                                setLinkEmail('');
                                setLinkRole('MEMBER');
                                setIsLinkModalOpen(true);
                              }}
                              title="Link Registered User Account"
                              className="flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded transition-colors"
                            >
                              <Link2 className="w-3 h-3" />
                              <span>Link User</span>
                            </button>
                          )}
                        </>
                      )}
                      {isAdmin && (
                        <button
                          onClick={() =>
                            togglePersonActive.mutate({
                              personId: p.id,
                              isActive: !p.is_active,
                            })
                          }
                          className={`text-xs px-2.5 py-1 rounded font-medium border transition-colors ${
                            p.is_active
                              ? 'bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 border-slate-200'
                              : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200'
                          }`}
                        >
                          {p.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
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
                  <th className="px-6 py-3">Category</th>
                  <th className="px-6 py-3">Estimated Amount</th>
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
                    <td className="px-6 py-4 text-slate-600">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-medium">
                        {t.category}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-bold text-slate-900">
                      {formatCentsToCurrency(t.estimated_amount_cents)}
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
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Resident Full Name *
            </label>
            <input
              type="text"
              required
              value={personName}
              onChange={(e) => setPersonName(e.target.value)}
              placeholder="e.g. Jordan Lee"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Registered User Email (Optional)
            </label>
            <input
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
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Assigned Household Role
              </label>
              <select
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
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Template Title
            </label>
            <input
              type="text"
              required
              value={templateTitle}
              onChange={(e) => setTemplateTitle(e.target.value)}
              placeholder="e.g. Monthly Rent, Fiber Internet"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Estimated Amount ($)
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={templateAmountStr}
                onChange={(e) => setTemplateAmountStr(e.target.value)}
                placeholder="1200.00"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Due Day (1-31)
              </label>
              <input
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
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Category
            </label>
            <select
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
