import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Home,
  Receipt,
  BarChart3,
  Settings,
  LogOut,
  ChevronDown,
  Building2,
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, activeHousehold, switchHousehold, logout } = useAuth();
  const location = useLocation();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const navItems = [
    { label: 'Current Cycle', path: '/', icon: Home },
    { label: 'Expenses', path: '/expenses', icon: Receipt },
    { label: 'General Balance', path: '/general-balance', icon: BarChart3 },
    { label: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand and Nav Links */}
          <div className="flex items-center space-x-8">
            <Link to="/" className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
                HL
              </div>
              <span className="font-bold text-xl text-slate-900 tracking-tight">
                Home<span className="text-emerald-600">Ledger</span>
              </span>
            </Link>

            <nav className="hidden md:flex space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Household Selector & User Profile */}
          <div className="flex items-center space-x-4">
            {/* Household switcher dropdown */}
            {user && user.households.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center space-x-2 px-3 py-1.5 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors"
                >
                  <Building2 className="w-4 h-4 text-emerald-600" />
                  <span className="max-w-[140px] truncate">
                    {activeHousehold?.household_name || 'Select Household'}
                  </span>
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50 animate-fadeIn">
                    <div className="px-3 py-2 border-b border-slate-100 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      My Households
                    </div>
                    {user.households.map((hh) => (
                      <button
                        key={hh.household_id}
                        onClick={() => {
                          switchHousehold(hh.household_id);
                          setDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-50 transition-colors ${
                          hh.household_id === activeHousehold?.household_id
                            ? 'font-medium text-emerald-600 bg-emerald-50/50'
                            : 'text-slate-700'
                        }`}
                      >
                        <span className="truncate">{hh.household_name}</span>
                        <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                          {hh.role}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* User details & logout */}
            <div className="flex items-center space-x-3 border-l border-slate-200 pl-4">
              <div className="hidden sm:block text-right">
                <div className="text-sm font-medium text-slate-800">
                  {user?.full_name}
                </div>
                <div className="text-xs text-slate-400">{user?.email}</div>
              </div>
              <button
                onClick={logout}
                title="Log out"
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
