import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Bot,
  Activity,
  User as UserIcon,
  LogOut,
  AlertTriangle,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { Incident, User } from '../types';

interface NavbarProps {
  currentUser: User | null;
  onLogout: () => void;
  activeIncident: Incident | null;
  onSelectIncident: (inc: Incident) => void;
  incidents: Incident[];
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onLogout,
  activeIncident,
  onSelectIncident,
  incidents,
}) => {
  const [bobStatus, setBobStatus] = useState<any>(null);
  const [auditVerified, setAuditVerified] = useState<boolean | null>(null);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [showIncidentDropdown, setShowIncidentDropdown] = useState(false);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    setVerifying(true);
    try {
      const bStatus = await api.getBobStatus();
      setBobStatus(bStatus);
      const aStatus = await api.verifyAuditChain();
      setAuditVerified(aStatus.valid);
    } catch (e) {
      setAuditVerified(false);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-4 flex items-center justify-between sticky top-0 z-30">
      {/* Brand & System Title */}
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-base tracking-wide">DVI-BRIDGE</span>
            <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono font-medium">
              IBM BOB
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">Disaster Victim Identification Coordination Platform</p>
        </div>
      </div>

      {/* Center: Active Incident Selector */}
      <div className="relative">
        <button
          onClick={() => setShowIncidentDropdown(!showIncidentDropdown)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-sm font-medium text-slate-200 transition"
        >
          <Activity className="h-4 w-4 text-sky-400" />
          <span className="max-w-[200px] truncate">{activeIncident ? activeIncident.name : 'Select Incident'}</span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
        </button>

        {showIncidentDropdown && (
          <div className="absolute top-full mt-1.5 w-72 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 z-50">
            <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700">
              Active Mass-Casualty Incidents
            </div>
            {incidents.map((inc) => (
              <button
                key={inc.id}
                onClick={() => {
                  onSelectIncident(inc);
                  setShowIncidentDropdown(false);
                }}
                className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-700/60 ${
                  activeIncident?.id === inc.id ? 'text-sky-400 bg-sky-500/10' : 'text-slate-200'
                }`}
              >
                <div className="truncate">
                  <div className="font-medium truncate">{inc.name}</div>
                  <div className="text-xs text-slate-400">{inc.location}</div>
                </div>
                <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">
                  {inc.status}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right Controls: AI status, Audit Chain badge, Profile */}
      <div className="flex items-center gap-3">
        {/* IBM Bob status pill */}
        <div
          title={bobStatus?.message || 'IBM Bob Status'}
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-medium text-slate-300"
        >
          <Bot className="h-3.5 w-3.5 text-indigo-400" />
          <span className="text-slate-400">Bob:</span>
          {bobStatus?.configured ? (
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Connected
            </span>
          ) : (
            <span className="flex items-center gap-1 text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              Active (Fallback)
            </span>
          )}
        </div>

        {/* Audit Hash Chain Verification Pill */}
        <button
          onClick={checkHealth}
          title="Click to re-verify cryptographic audit hash chain"
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-750 border border-slate-700 text-xs font-medium text-slate-300 transition"
        >
          {auditVerified === true ? (
            <span className="flex items-center gap-1 text-emerald-400">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Audit Integrity:</span> Verified
            </span>
          ) : auditVerified === false ? (
            <span className="flex items-center gap-1 text-rose-400">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Audit:</span> Integrity Alert
            </span>
          ) : (
            <span className="flex items-center gap-1 text-slate-400">
              <RefreshCw className={`h-3 w-3 ${verifying ? 'animate-spin' : ''}`} />
              Verifying
            </span>
          )}
        </button>

        {/* User Role & Logout */}
        {currentUser && (
          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-200 leading-none">{currentUser.full_name}</div>
              <div className="text-[10px] font-mono text-sky-400 mt-0.5">{currentUser.role}</div>
            </div>
            <button
              onClick={onLogout}
              title="Logout"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
