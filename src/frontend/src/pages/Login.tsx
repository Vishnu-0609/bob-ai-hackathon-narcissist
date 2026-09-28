import React, { useState } from 'react';
import { Shield, Lock, User as UserIcon, AlertCircle, ArrowRight, UserCheck, Sun, Moon } from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';

interface LoginProps {
  onLoginSuccess: (user: User) => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess, theme, onToggleTheme }) => {
  const [username, setUsername] = useState('coordinator');
  const [password, setPassword] = useState('coordpassword123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const demoRoles = [
    { name: 'Lead DVI Coordinator', user: 'coordinator', pass: 'coordpassword123', role: 'DVI_COORDINATOR', desc: 'Full reconciliation, candidate scoring & report sign-off' },
    { name: 'Chief Forensic Pathologist', user: 'reviewer', pass: 'reviewpassword123', role: 'FORENSIC_REVIEWER', desc: 'Forensic evidence verification and case approvals' },
    { name: 'System Administrator', user: 'admin', pass: 'adminpassword123', role: 'ADMIN', desc: 'Configuration, incidents, and audit management' },
    { name: 'NDRF Field Team', user: 'field_team', pass: 'fieldpassword123', role: 'FIELD_OPERATOR', desc: 'Ante-mortem & post-mortem intake and extraction review' },
    { name: 'Oversight Auditor', user: 'auditor', pass: 'auditpassword123', role: 'AUDITOR', desc: 'Tamper-evident audit chain and compliance verification' },
  ];

  const handleLogin = async (u = username, p = password) => {
    setLoading(true);
    setError(null);
    try {
      await api.login(u, p);
      const user = await api.getMe();
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden">
      <button
        onClick={onToggleTheme}
        title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        className="theme-toggle absolute top-5 right-5 p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
      <div className="w-full max-w-md z-10">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-md bg-sky-600 items-center justify-center mb-3">
            <Shield className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">DVI-BRIDGE</h1>
          <p className="text-xs text-sky-400 font-mono font-medium tracking-wider mt-0.5 uppercase">
            IBM Bob-Powered Disaster Victim Identification
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Secure Coordination, Deterministic Matching & Human-in-the-Loop Reconciliation
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center gap-2 text-rose-300 text-xs">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleLogin();
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Username
              </label>
              <div className="relative">
                <UserIcon className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
                  placeholder="Enter username"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <Lock className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
                  placeholder="Enter password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-sky-600 hover:bg-sky-500 text-white font-semibold py-2.5 px-4 rounded-md text-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Command Center</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Role Switcher */}
          <div className="mt-6 pt-5 border-t border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <UserCheck className="h-3.5 w-3.5 text-sky-400" />
              <span>Quick Demo Role Switcher</span>
            </div>
            <div className="space-y-1.5">
              {demoRoles.map((role) => (
                <button
                  key={role.user}
                  type="button"
                  onClick={() => {
                    setUsername(role.user);
                    setPassword(role.pass);
                    handleLogin(role.user, role.pass);
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg bg-slate-950/60 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-xs flex items-center justify-between transition group"
                >
                  <div>
                    <div className="font-medium text-slate-200 group-hover:text-sky-300 transition">
                      {role.name}
                    </div>
                    <div className="text-[10px] text-slate-400">{role.desc}</div>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {role.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-[11px] text-slate-400">
          <p>Interpol DVI Standards Compliant Prototype · Zero Real Victim PII</p>
        </div>
      </div>
    </div>
  );
};
