import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  FileText,
  Network,
  RotateCw,
  ShieldCheck,
  ChevronRight,
  Info,
  History,
  Layers,
  FileDown,
  Bot,
} from 'lucide-react';
import { api } from '../services/api';
import { EvidenceBadge } from '../components/EvidenceBadge';
import {
  Incident,
  PMCase,
  CandidateMatch,
  TopCandidatesResponse,
  ReconciliationResponse,
} from '../types';

interface ReconciliationProps {
  activeIncident: Incident | null;
  initialPmBodyNumber?: string;
  onNavigateToGraph: (matchId: string) => void;
}

export const Reconciliation: React.FC<ReconciliationProps> = ({
  activeIncident,
  initialPmBodyNumber = 'PM-017',
  onNavigateToGraph,
}) => {
  const [pmCases, setPmCases] = useState<PMCase[]>([]);
  const [selectedPmNumber, setSelectedPmNumber] = useState<string>(initialPmBodyNumber);
  const [candidatesData, setCandidatesData] = useState<TopCandidatesResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateMatch | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);

  // Decision Modal State
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [pendingDecision, setPendingDecision] = useState<string>('CONFIRMED_BY_FORENSIC_TEAM');
  const [decisionReason, setDecisionReason] = useState<string>('');
  const [coordinatorComment, setCoordinatorComment] = useState<string>('');
  const [submittingDecision, setSubmittingDecision] = useState(false);

  // Report Generation State
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadPmCases();
  }, [activeIncident]);

  useEffect(() => {
    if (selectedPmNumber) {
      loadCandidates(selectedPmNumber);
    }
  }, [selectedPmNumber]);

  const loadPmCases = async () => {
    if (!activeIncident) return;
    try {
      const pms = await api.listPMCases(activeIncident.id);
      setPmCases(pms);
      if (!selectedPmNumber && pms.length > 0) {
        setSelectedPmNumber(pms[0].body_number);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadCandidates = async (bodyNumber: string) => {
    setLoading(true);
    try {
      const res = await api.getCandidates(bodyNumber, 3);
      setCandidatesData(res);
      if (res.candidates.length > 0) {
        setSelectedCandidate(res.candidates[0]);
      } else {
        setSelectedCandidate(null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculate = async () => {
    if (!selectedPmNumber) return;
    setRecalculating(true);
    try {
      const res = await api.recalculateCandidates(selectedPmNumber, 3);
      setCandidatesData(res);
      if (res.candidates.length > 0) {
        setSelectedCandidate(res.candidates[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRecalculating(false);
    }
  };

  const handleOpenDecisionModal = (decision: string) => {
    setPendingDecision(decision);
    setDecisionReason(
      decision === 'CONFIRMED_BY_FORENSIC_TEAM'
        ? 'High concordance on primary biological attributes, stature, surgical scars, and personal belongings. No forensic contradictions.'
        : decision === 'NEEDS_REVIEW'
        ? 'Pending comparative odontological charting and reference family DNA swab analysis.'
        : 'Biological sex or extreme stature contradiction detected against family record.'
    );
    setShowDecisionModal(true);
  };

  const handleSubmitDecision = async () => {
    if (!candidatesData || !selectedCandidate || !decisionReason.trim()) return;
    setSubmittingDecision(true);
    try {
      await api.submitReconciliation({
        pm_id: candidatesData.pm_id,
        am_id: selectedCandidate.am_id,
        decision: pendingDecision,
        reason: decisionReason,
        coordinator_comment: coordinatorComment,
      });
      setShowDecisionModal(false);
      // Reload candidates
      loadCandidates(selectedPmNumber);
    } catch (err: any) {
      alert(`Reconciliation Submission Error: ${err.message}`);
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleGeneratePdfReport = async () => {
    if (!activeIncident || !candidatesData || !selectedCandidate) return;
    setGeneratingReport(true);
    setReportSuccess(null);
    try {
      const rep = await api.generateReport({
        incident_id: activeIncident.id,
        pm_id: candidatesData.pm_id,
        am_id: selectedCandidate.am_id,
        title: `Forensic Reconciliation Report — ${candidatesData.pm_body_number} ↔ ${selectedCandidate.am_case_number}`,
      });
      setReportSuccess(`Report ${rep.report_number} generated! Opening PDF download...`);
      // Open PDF in new tab
      window.open(`/api/reports/${rep.id}/pdf`, '_blank');
    } catch (err: any) {
      alert(`Report Generation Error: ${err.message}`);
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Target PM Selector */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
                FLAGSHIP RECONCILIATION
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Evaluated {candidatesData?.total_candidates_evaluated || 100} AM Profiles
              </span>
            </div>
            <h1 className="text-xl font-bold text-white mt-1">
              Target Post-Mortem Record: <span className="text-sky-400 font-mono">{selectedPmNumber}</span>
            </h1>
            <p className="text-xs text-slate-400">
              Deterministic Candidate Scoring (0-100) with IBM Bob Forensic Explainability
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedPmNumber}
              onChange={(e) => setSelectedPmNumber(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono font-medium text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {pmCases.map((pm) => (
                <option key={pm.id} value={pm.body_number}>
                  {pm.body_number} ({pm.sex || 'Sex?'}, {pm.height_cm ? `${pm.height_cm}cm` : 'Height?'})
                </option>
              ))}
            </select>

            <button
              onClick={handleRecalculate}
              disabled={recalculating}
              title="Force recalculate candidates & generate new match version snapshot"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            >
              <RotateCw className={`h-3.5 w-3.5 ${recalculating ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Recalculate</span>
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 font-mono text-sm">
          <div className="animate-spin h-6 w-6 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-2" />
          Running deterministic forensic comparison against all AM records...
        </div>
      ) : (
        <div className="space-y-6">
          {/* Top 3 Candidate Rank Cards */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Top Deterministic Candidates for {selectedPmNumber}
              </span>
              <span className="text-xs text-slate-500">
                Calculated: {new Date(candidatesData?.calculation_timestamp || '').toLocaleTimeString()}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {candidatesData?.candidates.map((cand) => {
                const isSelected = selectedCandidate?.am_id === cand.am_id;
                return (
                  <div
                    key={cand.am_id}
                    onClick={() => setSelectedCandidate(cand)}
                    className={`cursor-pointer rounded-2xl p-4 border transition relative overflow-hidden shadow-lg ${
                      isSelected
                        ? 'bg-slate-850 border-sky-500 ring-1 ring-sky-500/50 shadow-sky-500/10'
                        : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {/* Rank Badge */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="h-6 w-6 rounded-full bg-slate-800 flex items-center justify-center font-mono text-xs font-bold text-slate-200 border border-slate-700">
                          #{cand.candidate_rank}
                        </span>
                        <span className="font-bold text-white text-sm">{cand.am_case_number}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-sky-400 font-mono leading-none">
                          {cand.match_score}
                          <span className="text-[11px] font-normal text-slate-400">/100</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-xs font-medium text-slate-300 mb-2 truncate">
                      {cand.am_name}
                    </div>

                    <div className="flex items-center gap-2 flex-wrap text-[11px] mb-3">
                      <EvidenceBadge status={cand.status} size="sm" />
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        Quality: {cand.evidence_quality}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400 space-y-0.5 pt-2 border-t border-slate-800">
                      <div>Supporting Fields: <span className="text-emerald-400 font-mono font-semibold">{cand.supporting_evidence.length}</span></div>
                      <div>Contradictions: <span className={`font-mono font-semibold ${cand.contradictions.length ? 'text-rose-400' : 'text-slate-400'}`}>{cand.contradictions.length}</span></div>
                      <div>Decision: <span className="font-mono text-slate-300">{cand.reconciliation_status}</span></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected Candidate Detailed Evidence Matrix & Actions */}
          {selectedCandidate && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Field-by-Field Concordance Matrix */}
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-800">
                    <div>
                      <h2 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Evidence Concordance:</span>
                        <span className="text-sky-400 font-mono">{selectedCandidate.am_case_number}</span>
                        <span className="text-slate-400 font-normal">({selectedCandidate.am_name})</span>
                      </h2>
                      <p className="text-xs text-slate-400">
                        Field-by-field deterministic comparison against body {selectedPmNumber}
                      </p>
                    </div>

                    {selectedCandidate.match_id && (
                      <button
                        onClick={() => onNavigateToGraph(selectedCandidate.match_id!)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition"
                      >
                        <Network className="h-3.5 w-3.5" />
                        <span>Interactive Graph</span>
                      </button>
                    )}
                  </div>

                  {/* Concordance Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                        <tr>
                          <th className="py-2.5 px-3">Forensic Field</th>
                          <th className="py-2.5 px-3">AM Reported (Family)</th>
                          <th className="py-2.5 px-3">PM Observed (Mortuary)</th>
                          <th className="py-2.5 px-3">Result</th>
                          <th className="py-2.5 px-3 text-right">Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {selectedCandidate.supporting_evidence
                          .concat(selectedCandidate.contradictions)
                          .concat(selectedCandidate.unknown)
                          .map((item, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/40 transition">
                              <td className="py-2.5 px-3 font-sans font-medium text-slate-200">
                                {item.field_name.replace('_', ' ').toUpperCase()}
                              </td>
                              <td className="py-2.5 px-3 text-slate-300 max-w-[150px] truncate">
                                {item.am_value || 'Not recorded'}
                              </td>
                              <td className="py-2.5 px-3 text-slate-300 max-w-[150px] truncate">
                                {item.pm_value || 'Not recorded'}
                              </td>
                              <td className="py-2.5 px-3">
                                <EvidenceBadge status={item.comparison_result} size="sm" />
                              </td>
                              <td className="py-2.5 px-3 text-right text-slate-300 font-bold">
                                {item.score_awarded} / {item.weight}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Contradictions and Evidence Gaps Checklist */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Contradictions */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-rose-400 uppercase tracking-wider mb-2">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Contradiction Status: {selectedCandidate.contradiction_status}</span>
                    </div>
                    {selectedCandidate.contradictions.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-rose-300">
                        {selectedCandidate.contradictions.map((c, i) => (
                          <li key={i} className="p-2 rounded bg-rose-500/10 border border-rose-500/20">
                            <b>{c.field_name}:</b> {c.notes || 'Anatomical discrepancy observed'}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400">
                        No direct anatomical, serological, or stature contradictions detected.
                      </p>
                    )}
                  </div>

                  {/* Evidence Gaps */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider mb-2">
                      <HelpCircle className="h-4 w-4" />
                      <span>Evidence Gap Checklist</span>
                    </div>
                    {selectedCandidate.evidence_gaps?.recommended_workflow ? (
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {selectedCandidate.evidence_gaps.recommended_workflow.map((rec, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="text-amber-400 mt-0.5">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400">All standard secondary forensic markers available.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Col: IBM Bob Rationale & Human Decision Actions */}
              <div className="space-y-6">
                {/* IBM Bob Plain-Language Rationale Card */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
                  <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-800">
                    <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-indigo-500 to-sky-600 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        IBM Bob Forensic Rationale
                      </h3>
                      <p className="text-[10px] text-slate-400">AI explainability strictly bound to facts</p>
                    </div>
                  </div>

                  <div className="text-xs text-slate-300 leading-relaxed space-y-2 whitespace-pre-line bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                    {selectedCandidate.bob_rationale || 'Generating Bob plain-language rationale...'}
                  </div>
                </div>

                {/* Human-in-the-Loop Coordinator Action Panel */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                  <div>
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-sky-400" />
                      <span>Human Forensic Sign-Off</span>
                    </h3>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Interpol mandate: Final reconciliation is an authorized human forensic decision.
                    </p>
                  </div>

                  {reportSuccess && (
                    <div className="p-2.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs">
                      {reportSuccess}
                    </div>
                  )}

                  <div className="space-y-2">
                    <button
                      onClick={() => handleOpenDecisionModal('CONFIRMED_BY_FORENSIC_TEAM')}
                      className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 transition flex items-center justify-center gap-2"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Confirm Reconciliation</span>
                    </button>

                    <button
                      onClick={() => handleOpenDecisionModal('NEEDS_REVIEW')}
                      className="w-full py-2.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold shadow-lg shadow-amber-600/20 transition flex items-center justify-center gap-2"
                    >
                      <HelpCircle className="h-4 w-4" />
                      <span>Flag for Secondary Review</span>
                    </button>

                    <button
                      onClick={() => handleOpenDecisionModal('REJECTED')}
                      className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-rose-900/60 text-slate-300 hover:text-rose-200 border border-slate-700 text-xs font-bold transition flex items-center justify-center gap-2"
                    >
                      <XCircle className="h-4 w-4" />
                      <span>Reject Candidate Pair</span>
                    </button>
                  </div>

                  <div className="pt-3 border-t border-slate-800">
                    <button
                      onClick={handleGeneratePdfReport}
                      disabled={generatingReport}
                      className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-750 text-sky-400 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-2 transition"
                    >
                      <FileDown className="h-4 w-4" />
                      <span>{generatingReport ? 'Rendering ReportLab PDF...' : 'Export Reconciliation PDF Report'}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Coordinator Decision Modal */}
      {showDecisionModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">
              Log Reconciliation Decision: <span className="font-mono text-sky-400">{pendingDecision}</span>
            </h3>
            <p className="text-xs text-slate-400">
              This action creates an immutable, SHA-256 hashed audit log record for legal traceability.
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 uppercase tracking-wider">
                Forensic Decision Reason (Required)
              </label>
              <textarea
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                rows={3}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 uppercase tracking-wider">
                Coordinator Internal Notes (Optional)
              </label>
              <input
                type="text"
                value={coordinatorComment}
                onChange={(e) => setCoordinatorComment(e.target.value)}
                placeholder="e.g. Next-of-kin notified, biometric reference pending"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowDecisionModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingDecision || !decisionReason.trim()}
                onClick={handleSubmitDecision}
                className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-xs font-bold shadow-md shadow-sky-500/20 disabled:opacity-50"
              >
                {submittingDecision ? 'Signing Decision...' : 'Sign & Commit Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
