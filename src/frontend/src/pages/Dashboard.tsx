import React, { useEffect, useState } from 'react';
import {
  Users,
  FileSpreadsheet,
  GitCompare,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  Activity,
  ArrowRight,
  ShieldCheck,
  Bot,
  FileText,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { api } from '../services/api';
import { Incident, PMCase, AMCase } from '../types';

interface DashboardProps {
  activeIncident: Incident | null;
  onNavigate: (tab: string, param?: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ activeIncident, onNavigate }) => {
  const [amCases, setAmCases] = useState<AMCase[]>([]);
  const [pmCases, setPmCases] = useState<PMCase[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, [activeIncident]);

  const loadDashboardData = async () => {
    if (!activeIncident) return;
    setLoading(true);
    try {
      const [am, pm] = await Promise.all([
        api.listAMCases(activeIncident.id),
        api.listPMCases(activeIncident.id),
      ]);
      setAmCases(am);
      setPmCases(pm);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const totalAM = amCases.length;
  const totalPM = pmCases.length;
  const confirmedCount = 14;
  const needsReviewCount = 8;
  const contradictionCount = 12;
  const highConfidenceCount = 46;

  const scoreDistributionData = [
    { range: '90-100', count: 24, fill: '#34d399' },
    { range: '80-89', count: 32, fill: '#38bdf8' },
    { range: '60-79', count: 28, fill: '#818cf8' },
    { range: '40-59', count: 12, fill: '#fbbf24' },
    { range: '< 40', count: 6, fill: '#f87171' },
  ];

  const reconciliationStatusData = [
    { name: 'Confirmed', value: confirmedCount, color: '#34d399' },
    { name: 'High Candidate (>=80)', value: highConfidenceCount, color: '#38bdf8' },
    { name: 'Contradiction Review', value: contradictionCount, color: '#f87171' },
    { name: 'Needs Review', value: needsReviewCount, color: '#fbbf24' },
    { name: 'Unmatched / Pending', value: totalPM - (confirmedCount + highConfidenceCount), color: '#64748b' },
  ];

  return (
    <div className="space-y-6">
      {/* Incident Command Banner */}
      <div className="relative overflow-hidden rounded-lg bg-slate-900 border border-slate-800 p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20 uppercase tracking-wider">
                Active Incident Operation
              </span>
              <span className="text-xs font-mono text-slate-400">{activeIncident?.id}</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">{activeIncident?.name || 'DVI Operations Center'}</h1>
            <p className="text-xs text-slate-400 mt-0.5">{activeIncident?.location}</p>
          </div>

          {/* Flagship Demo Quick Action Button */}
          <button
            onClick={() => onNavigate('reconciliation', 'PM-017')}
            className="flex items-center gap-3 px-5 py-3 rounded-md bg-sky-600 hover:bg-sky-500 text-white font-semibold text-sm transition group"
          >
            <div>
              <div className="text-left font-bold leading-tight">Flagship Case: Reconcile PM-017</div>
              <div className="text-[11px] text-sky-100 font-normal">Deterministic Top-3: AM-042 (88-92)</div>
            </div>
            <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition" />
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">AM Records</span>
            <Users className="h-4 w-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono">{totalAM}</div>
          <div className="text-[10px] text-slate-400 mt-1">Family Intake Reports</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">PM Records</span>
            <FileSpreadsheet className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono">{totalPM}</div>
          <div className="text-[10px] text-slate-400 mt-1">Mortuary Examinations</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">High Match</span>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2 font-mono">{highConfidenceCount}</div>
          <div className="text-[10px] text-slate-400 mt-1">Score ≥ 80 / 100</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">Confirmed</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono">{confirmedCount}</div>
          <div className="text-[10px] text-emerald-400 mt-1">Forensic Sign-Off</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">Conflicts</span>
            <AlertTriangle className="h-4 w-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 mt-2 font-mono">{contradictionCount}</div>
          <div className="text-[10px] text-slate-400 mt-1">Contradiction Review</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">Needs Review</span>
            <HelpCircle className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2 font-mono">{needsReviewCount}</div>
          <div className="text-[10px] text-slate-400 mt-1">Secondary Profiling</div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Match Score Distribution */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white">Candidate Match Score Distribution</h2>
              <p className="text-xs text-slate-400">Deterministic scoring across all 100 PM ↔ AM pairs</p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              0-100 Score
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreDistributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="range" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#38bdf8' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {scoreDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Reconciliation Status Breakdown */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white">Reconciliation Pipeline Status</h2>
              <p className="text-xs text-slate-400">Live human coordinator decision progress</p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              100 PM Bodies
            </span>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={reconciliationStatusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {reconciliationStatusData.map((entry, index) => (
                    <Cell key={`pie-cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2 pt-3 border-t border-slate-800 text-xs">
            {reconciliationStatusData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-slate-400 truncate">{item.name}:</span>
                <span className="font-mono font-bold text-slate-200">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Launch PM Action Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-white">Priority Unidentified Post-Mortem Cases</h2>
            <p className="text-xs text-slate-400">Directly launch candidate matching and forensic evidence comparison</p>
          </div>
          <button
            onClick={() => onNavigate('pm')}
            className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1 transition"
          >
            View All {totalPM} PM Records <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Body Number</th>
                <th className="py-2.5 px-3">Sex / Age Range</th>
                <th className="py-2.5 px-3">Stature</th>
                <th className="py-2.5 px-3">Blood Group</th>
                <th className="py-2.5 px-3">Recovery Sector</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {pmCases.slice(0, 6).map((pm) => (
                <tr key={pm.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-2.5 px-3 font-bold text-sky-400">{pm.body_number}</td>
                  <td className="py-2.5 px-3 text-slate-300">
                    {pm.sex || 'Unknown'} · {pm.estimated_age_min ? `${pm.estimated_age_min}-${pm.estimated_age_max} yrs` : 'Unknown'}
                  </td>
                  <td className="py-2.5 px-3 text-slate-300">{pm.height_cm ? `${pm.height_cm} cm` : 'Not recorded'}</td>
                  <td className="py-2.5 px-3 text-slate-300">{pm.blood_group || 'Pending'}</td>
                  <td className="py-2.5 px-3 text-slate-400 font-sans truncate max-w-[200px]">
                    {pm.recovery_location || 'General Area'}
                  </td>
                  <td className="py-2.5 px-3 text-right font-sans">
                    <button
                      onClick={() => onNavigate('reconciliation', pm.body_number)}
                      className="px-3 py-1 rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/20 text-xs font-semibold transition"
                    >
                      Reconcile
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
