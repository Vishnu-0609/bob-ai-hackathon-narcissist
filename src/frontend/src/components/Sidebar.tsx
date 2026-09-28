import React from 'react';
import {
  LayoutDashboard,
  GitCompare,
  FileSpreadsheet,
  Users,
  Network,
  Bot,
  FileText,
  ShieldCheck,
  Award,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Command Dashboard', icon: LayoutDashboard, badge: null },
    { id: 'reconciliation', label: 'Candidate Reconciliation', icon: GitCompare, badge: 'Flagship' },
    { id: 'am', label: 'Ante-Mortem (AM)', icon: Users, badge: null },
    { id: 'pm', label: 'Post-Mortem (PM)', icon: FileSpreadsheet, badge: null },
    { id: 'evidence', label: 'Evidence Graph', icon: Network, badge: null },
    { id: 'copilot', label: 'Bob DVI Copilot', icon: Bot, badge: 'AI' },
    { id: 'reports', label: 'Reconciliation Reports', icon: FileText, badge: 'PDF' },
    { id: 'audit', label: 'Audit Hash Trail', icon: ShieldCheck, badge: 'SHA-256' },
    { id: 'evaluation', label: 'Evaluation Metrics', icon: Award, badge: 'Benchmark' },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col flex-shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-3 space-y-1">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Forensic Workflows
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                isActive
                  ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/70 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-3 truncate">
                <Icon className={`h-4 w-4 flex-shrink-0 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                <span className="truncate">{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${
                    item.badge === 'Flagship'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : item.badge === 'AI'
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      : 'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-auto p-4 border-t border-slate-800/80">
        <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/60">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Deterministic Matching Engine
          </div>
          <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
            Forensic candidate scoring is 100% deterministic (0-100 Match Score). Human reconciliation required.
          </p>
        </div>
      </div>
    </aside>
  );
};
