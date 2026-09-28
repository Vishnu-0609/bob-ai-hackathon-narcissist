import React, { useState, useEffect } from 'react';
import {
  Award,
  TrendingUp,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Bot,
  Zap,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { api } from '../services/api';
import { EvaluationMetrics } from '../types';

export const Evaluation: React.FC = () => {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const data = await api.getEvaluationMetrics();
      setMetrics(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const benchmarkChartData = metrics
    ? [
        { name: 'Top-1 Accuracy', value: metrics.top1_accuracy, fill: '#34d399' },
        { name: 'Top-3 Recall', value: metrics.top3_recall, fill: '#38bdf8' },
        { name: 'Contradiction Acc.', value: metrics.contradiction_detection_accuracy, fill: '#818cf8' },
        { name: 'Missing Data Robust.', value: metrics.missing_data_robustness, fill: '#fbbf24' },
        { name: 'Bob Extract Valid.', value: metrics.bob_extraction_validation_rate, fill: '#f472b6' },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                RIGOROUS BENCHMARK EVALUATION
              </span>
              <span className="text-xs text-slate-400 font-mono">
                100 Ground Truth Benchmark Pairs
              </span>
            </div>
            <h1 className="text-xl font-bold text-white mt-1">Forensic Matching & AI Accuracy Benchmark</h1>
            <p className="text-xs text-slate-400">
              Evaluated against synthetic ground truth covering exact matches, partial observations, contradictions, and missing data
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 font-mono text-sm">
          <div className="animate-spin h-6 w-6 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-2" />
          Running statistical evaluation across ground truth benchmark dataset...
        </div>
      ) : metrics ? (
        <div className="space-y-6">
          {/* Key Metric Scorecards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase">Top-1 Accuracy</span>
                <TrendingUp className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="text-3xl font-bold text-emerald-400 mt-2 font-mono">{metrics.top1_accuracy}%</div>
              <div className="text-[11px] text-slate-400 mt-1">True match is ranked #1</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase">Top-3 Recall</span>
                <Award className="h-4 w-4 text-sky-400" />
              </div>
              <div className="text-3xl font-bold text-sky-400 mt-2 font-mono">{metrics.top3_recall}%</div>
              <div className="text-[11px] text-slate-400 mt-1">True match within Top 3</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase">Contradiction Acc.</span>
                <ShieldCheck className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="text-3xl font-bold text-indigo-400 mt-2 font-mono">{metrics.contradiction_detection_accuracy}%</div>
              <div className="text-[11px] text-slate-400 mt-1">Biological conflicts flagged</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase">Engine Latency</span>
                <Zap className="h-4 w-4 text-amber-400" />
              </div>
              <div className="text-3xl font-bold text-amber-400 mt-2 font-mono">{metrics.average_matching_latency_ms} ms</div>
              <div className="text-[11px] text-slate-400 mt-1">Avg 100-case pair scoring</div>
            </div>
          </div>

          {/* Benchmark Accuracy Chart */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <h2 className="text-sm font-bold text-white mb-4">Accuracy Benchmark Across Forensic Scenarios</h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={benchmarkChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {benchmarkChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Ground Truth Breakdown Matrix */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <h2 className="text-sm font-bold text-white mb-3">Synthetic Dataset Forensic Breakdown</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-400">Exact Match Cases:</span>
                <div className="text-base font-bold text-white mt-1">{metrics.exact_match_cases} / 100</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-400">Partial Match Cases:</span>
                <div className="text-base font-bold text-white mt-1">{metrics.partial_match_cases} / 100</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-400">Contradiction Injected:</span>
                <div className="text-base font-bold text-rose-400 mt-1">{metrics.contradiction_cases} / 100</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-400">Missing Data Handled:</span>
                <div className="text-base font-bold text-amber-400 mt-1">{metrics.missing_data_cases} / 100</div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
