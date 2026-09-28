import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  FileSpreadsheet,
  FileDown,
  Calendar,
  ShieldCheck,
  Search,
  ExternalLink,
} from 'lucide-react';
import { api } from '../services/api';
import { Incident, ReportResponse } from '../types';

interface ReportsProps {
  activeIncident: Incident | null;
}

export const Reports: React.FC<ReportsProps> = ({ activeIncident }) => {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, [activeIncident]);

  const loadReports = async () => {
    if (!activeIncident) return;
    setLoading(true);
    try {
      const data = await api.listReports(activeIncident.id);
      setReports(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = (reportId: string, filename: string) => {
    window.open(`/api/reports/${reportId}/pdf`, '_blank');
  };

  const handleDownloadCsv = (reportId: string) => {
    window.open(`/api/reports/${reportId}/csv`, '_blank');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white">Forensic Reconciliation Reports</h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
              ReportLab Generated PDF & CSV
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative decision-support dossiers with evidence matrices, IBM Bob rationales, and tamper-evident audit seals
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 font-mono text-sm">
          <div className="animate-spin h-6 w-6 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-2" />
          Loading reconciliation dossiers...
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <FileText className="h-10 w-10 text-slate-500 mx-auto" />
          <h3 className="text-sm font-bold text-white">No Reconciliation Reports Generated Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Navigate to the Candidate Reconciliation screen and click "Export Reconciliation PDF Report" on any reviewed candidate match.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3">Report Number</th>
                  <th className="py-3 px-3">Dossier Title</th>
                  <th className="py-3 px-3">PM Body ↔ AM Candidate</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Generated At</th>
                  <th className="py-3 px-3 text-right">Downloads</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {reports.map((rep) => (
                  <tr key={rep.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-3 font-bold text-sky-400">{rep.report_number}</td>
                    <td className="py-3 px-3 font-sans font-medium text-slate-200">{rep.title}</td>
                    <td className="py-3 px-3 text-slate-300">
                      {rep.content_json?.pm_case?.body_number || 'PM'} ↔ {rep.content_json?.am_case?.case_number || 'AM'}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px]">
                        {rep.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400 text-[11px]">
                      {new Date(rep.generated_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-3 text-right font-sans">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleDownloadPdf(rep.id, rep.report_number)}
                          className="px-2.5 py-1 rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/20 text-xs font-semibold flex items-center gap-1 transition"
                        >
                          <FileDown className="h-3.5 w-3.5" />
                          <span>PDF</span>
                        </button>
                        <button
                          onClick={() => handleDownloadCsv(rep.id)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 text-xs font-semibold flex items-center gap-1 transition"
                        >
                          <FileSpreadsheet className="h-3.5 w-3.5" />
                          <span>CSV</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
