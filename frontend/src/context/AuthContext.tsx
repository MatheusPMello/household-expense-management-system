import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { User, HouseholdMembership } from '../types';

interface AuthContextType {
  user: User | null;
  activeHousehold: HouseholdMembership | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (tokens: { access_token: string; refresh_token: string }) => Promise<void>;
  register: (tokens: { access_token: string; refresh_token: string }) => Promise<void>;
  logout: () => Promise<void>;
  switchHousehold: (householdId: string) => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [activeHousehold, setActiveHousehold] = useState<HouseholdMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    try {
      const resp = await api.get<User>('/auth/me');
      const userData = resp.data;
      setUser(userData);

      const savedHhId = localStorage.getItem('homeledger_active_household_id');
      const found = userData.households.find((h) => h.household_id === savedHhId);

      if (found) {
        setActiveHousehold(found);
      } else if (userData.households.length > 0) {
        const defaultHh = userData.households[0];
        setActiveHousehold(defaultHh);
        localStorage.setItem('homeledger_active_household_id', defaultHh.household_id);
      } else {
        setActiveHousehold(null);
      }
    } catch {
      setUser(null);
      setActiveHousehold(null);
      localStorage.removeItem('homeledger_access_token');
      localStorage.removeItem('homeledger_refresh_token');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('homeledger_access_token');
    if (token) {
      refreshUser();
    } else {
      setIsLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback(async (tokens: { access_token: string; refresh_token: string }) => {
    localStorage.setItem('homeledger_access_token', tokens.access_token);
    localStorage.setItem('homeledger_refresh_token', tokens.refresh_token);
    await refreshUser();
  }, [refreshUser]);

  const register = useCallback(async (tokens: { access_token: string; refresh_token: string }) => {
    await login(tokens);
  }, [login]);

  const logout = useCallback(async () => {
    try {
      const refreshToken = localStorage.getItem('homeledger_refresh_token');
      if (refreshToken) {
        await api.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('homeledger_access_token');
      localStorage.removeItem('homeledger_refresh_token');
      localStorage.removeItem('homeledger_active_household_id');
      setUser(null);
      setActiveHousehold(null);
      queryClient.clear();
    }
  }, [queryClient]);

  const switchHousehold = useCallback((householdId: string) => {
    if (!user) return;
    const found = user.households.find((h) => h.household_id === householdId);
    if (found) {
      setActiveHousehold(found);
      localStorage.setItem('homeledger_active_household_id', found.household_id);
      queryClient.clear();
    }
  }, [user, queryClient]);

  const contextValue = useMemo(
    () => ({
      user,
      activeHousehold,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
      switchHousehold,
      refreshUser,
    }),
    [user, activeHousehold, isLoading, login, register, logout, switchHousehold, refreshUser]
  );

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
