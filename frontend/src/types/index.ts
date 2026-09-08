export type SplitType = 'EQUAL' | 'PERCENTAGE' | 'EXACT' | 'WEIGHTED';
export type CycleStatus = 'OPEN' | 'CLOSED';
export type MemberRole = 'ADMIN' | 'MEMBER';

export interface HouseholdMembership {
  household_id: string;
  household_name: string;
  role: MemberRole;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  households: HouseholdMembership[];
}

export interface Household {
  id: string;
  name: string;
  created_at: string;
  role?: MemberRole;
}

export interface HouseholdMember {
  id: string;
  household_id: string;
  user_id: string;
  role: MemberRole;
  full_name: string;
  email: string;
  created_at: string;
}

export interface Person {
  id: string;
  household_id: string;
  user_id?: string | null;
  user_email?: string | null;
  role?: MemberRole | null;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface FixedExpenseTemplate {
  id: string;
  household_id: string;
  title: string;
  estimated_amount_cents: number;
  due_day: number;
  category: string;
  is_active: boolean;
}

export interface BillingCycle {
  id: string;
  household_id: string;
  year: number;
  month: number;
  status: CycleStatus;
  closed_at?: string | null;
  created_at: string;
  total_expenses_cents: number;
  total_paid_to_vendor_cents: number;
  total_collected_cents: number;
  total_waived_cents: number;
}

export interface ExpenseSplit {
  id: string;
  expense_id: string;
  person_id: string;
  person_name: string;
  assigned_amount_cents: number;
}

export interface Expense {
  id: string;
  billing_cycle_id: string;
  title: string;
  total_amount_cents: number;
  is_fixed: boolean;
  category: string;
  due_date: string;
  paid_to_vendor: boolean;
  split_type: SplitType;
  created_at: string;
  splits: ExpenseSplit[];
}

export interface Payment {
  id: string;
  billing_cycle_id: string;
  person_id: string;
  person_name: string;
  amount_cents: number;
  paid_at: string;
  notes?: string | null;
  proof_url?: string | null;
}

export interface DebtWaiver {
  id: string;
  billing_cycle_id: string;
  person_id: string;
  person_name: string;
  amount_cents: number;
  waived_at: string;
  reason: string;
}

export interface ResidentCycleBalance {
  person_id: string;
  person_name: string;
  assigned_cents: number;
  paid_cents: number;
  waived_cents: number;
  remaining_balance_cents: number;
  status: 'SETTLED' | 'OWES' | 'CREDIT';
}

export interface CurrentCycleReport {
  cycle_id: string;
  year: number;
  month: number;
  status: CycleStatus;
  total_budget_cents: number;
  total_paid_to_vendor_cents: number;
  total_collected_cents: number;
  total_waived_cents: number;
  residents: ResidentCycleBalance[];
  expenses: Expense[];
}

export interface ResidentHistoricalSummary {
  person_id: string;
  person_name: string;
  total_assigned_cents: number;
  total_paid_cents: number;
  total_waived_cents: number;
  compliance_rate_percent: number;
  outstanding_historical_balance_cents: number;
}

export interface DebtWaiverLedgerEntry {
  id: string;
  billing_cycle_id: string;
  cycle_year: number;
  cycle_month: number;
  person_id: string;
  person_name: string;
  amount_cents: number;
  waived_at: string;
  reason: string;
}

export interface MonthlyTrajectoryPoint {
  cycle_id: string;
  year: number;
  month: number;
  fixed_cents: number;
  variable_cents: number;
  total_cents: number;
}

export interface GeneralBalanceReport {
  household_id: string;
  residents: ResidentHistoricalSummary[];
  debt_waiver_ledger: DebtWaiverLedgerEntry[];
  trajectory: MonthlyTrajectoryPoint[];
}
