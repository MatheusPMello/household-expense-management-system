import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { BillingCycle } from '../types';

export function useHouseholdCycles(
  householdId?: string,
  selectedCycleId?: string | null
) {
  const {
    data: cycles = [],
    isLoading,
    refetch,
  } = useQuery<BillingCycle[]>({
    queryKey: ['cycles', householdId],
    queryFn: async () => {
      if (!householdId) return [];
      const res = await api.get<BillingCycle[]>(
        `/cycles?household_id=${householdId}`
      );
      return res.data;
    },
    enabled: !!householdId,
  });

  const activeCycle =
    cycles.find((c) => c.id === selectedCycleId) || cycles[0] || null;

  return { cycles, activeCycle, isLoading, refetch };
}
