import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Search,
  Plus,
  Sparkles,
  CheckCircle,
  GitCompare,
  Clock,
  MapPin,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { PMCase, Incident } from '../types';

interface PMRecordsProps {
  activeIncident: Incident | null;
  onNavigateToReconciliation: (bodyNumber: string) => void;
}

export const PMRecords: React.FC<PMRecordsProps> = ({
  activeIncident,
  onNavigateToReconciliation,
}) => {
  const [cases, setCases] = useState<PMCase[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // Intake Modal State
  const [showModal, setShowModal] = useState(false);
  const [intakeText, setIntakeText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadCases();
  }, [activeIncident]);

  const loadCases = async () => {
    if (!activeIncident) return;
    setLoading(true);
    try {
      const data = await api.listPMCases(activeIncident.id, search);
      setCases(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadCases();
  };

  const handleExtractBob = async () => {
    if (!intakeText.trim() || !activeIncident) return;
    setExtracting(true);
    try {
      const res = await api.extractPM(intakeText, activeIncident.id);
      setExtractedData(res.extracted_data);
      setReviewId(res.review_id);
    } catch (err: any) {
      alert(`Bob Extraction Error: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  const handleSaveApproved = async () => {
    if (!activeIncident || !extractedData) return;
    setSubmitting(true);
    try {
      const autoNum = 'PM-' + String(cases.length + 1).padStart(3, '0');
      await api.reviewPM({
        review_id: reviewId,
        entity_type: 'PM',
        incident_id: activeIncident.id,
        case_identifier: extractedData.body_number || autoNum,
        approved_data: extractedData,
        decision: 'APPROVED',
        notes: 'Forensic examiner notes verified and approved.',
      });
      setShowModal(false);
      setIntakeText('');
      setExtractedData(null);
      setReviewId(null);
      loadCases();
    } catch (err: any) {
      alert(`Save Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const loadDemoSample = () => {
    setIntakeText(
      'Unidentified deceased male body approximately 32 to 36 years old. Measured height 172 cm, weight 67 kg. Healed surgical linear scar approximately 3 cm noted on left forearm. Small mole observed on left cheek. Bird tattoo noted on right shoulder. Blue shirt and dark denim jeans recovered. Recovered from Coromandel Express Coach B-3. Friction ridges preserved on digits.'
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white">Post-Mortem (PM) Records</h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {cases.length} Unidentified Bodies Logged
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Mortuary post-mortem observations, physical features, and biological specimen tracking
          </p>
        </div>

        <button
          onClick={() => {
            setShowModal(true);
            setExtractedData(null);
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-sky-500/20 transition"
        >
          <Sparkles className="h-4 w-4" />
          <span>New PM Examiner Intake (IBM Bob)</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by body number, physical marks, recovery sector, or examiner..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            Search
          </button>
        </form>
      </div>

      {/* PM Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-3">Body Number</th>
                <th className="py-3 px-3">Sex / Estimated Age</th>
                <th className="py-3 px-3">Measured Stature</th>
                <th className="py-3 px-3">Blood Group</th>
                <th className="py-3 px-3">Observed Scars / Tattoos</th>
                <th className="py-3 px-3">Recovery Sector</th>
                <th className="py-3 px-3">Fingerprint / DNA</th>
                <th className="py-3 px-3 text-right">Reconcile</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {cases.map((pm) => (
                <tr key={pm.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 font-bold text-sky-400">{pm.body_number}</td>
                  <td className="py-3 px-3 text-slate-300">
                    {(pm.sex || 'Unknown') + ' · ' + (pm.estimated_age_min ? `${pm.estimated_age_min}-${pm.estimated_age_max} yrs` : 'Unknown')}
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    {pm.height_cm ? `${pm.height_cm} cm` : 'Not measured'}
                  </td>
                  <td className="py-3 px-3 text-slate-300">{pm.blood_group || 'Pending'}</td>
                  <td className="py-3 px-3 font-sans text-slate-400 max-w-[200px] truncate">
                    {pm.scars?.length > 0 && `Scar: ${pm.scars[0]?.location || pm.scars[0]}; `}
                    {pm.tattoos?.length > 0 && `Tattoo: ${pm.tattoos[0]?.location || pm.tattoos[0]}`}
                    {!pm.scars?.length && !pm.tattoos?.length && 'None observed'}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-400 truncate max-w-[180px]">
                    {pm.recovery_location || 'N/A'}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-400 text-[11px]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      FP: {pm.fingerprint_status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right font-sans">
                    <button
                      onClick={() => onNavigateToReconciliation(pm.body_number)}
                      className="px-3 py-1 rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/20 text-xs font-semibold flex items-center gap-1.5 ml-auto transition"
                    >
                      <GitCompare className="h-3.5 w-3.5" />
                      <span>Reconcile</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* PM Intake Modal with IBM Bob Extraction */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <h3 className="text-base font-bold text-white">PM Mortuary Examiner Intake (IBM Bob)</h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Forensic Examiner Field Notes
                </label>
                <button
                  type="button"
                  onClick={loadDemoSample}
                  className="text-xs text-sky-400 hover:text-sky-300 font-medium"
                >
                  Load Demo Examiner Notes Sample
                </button>
              </div>

              <textarea
                value={intakeText}
                onChange={(e) => setIntakeText(e.target.value)}
                rows={4}
                placeholder="Paste verbatim examiner observations: 'Unidentified male body approx 32 to 36 yrs, measured 172 cm, healed surgical scar on left forearm, recovered from Coach B-3...'"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />

              <div className="flex items-center justify-end mt-2">
                <button
                  type="button"
                  disabled={extracting || !intakeText.trim()}
                  onClick={handleExtractBob}
                  className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold shadow-md shadow-sky-500/20 disabled:opacity-50 transition"
                >
                  {extracting ? (
                    <span>Bob Agent Parsing Notes...</span>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Parse PM Observations</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Structured PM Preview */}
            {extractedData && (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                    Parsed Post-Mortem Observations
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Forensic Verification Required
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-400">Estimated Age Min</label>
                    <input
                      type="number"
                      value={extractedData.estimated_age_min || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, estimated_age_min: parseInt(e.target.value) || null })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Estimated Age Max</label>
                    <input
                      type="number"
                      value={extractedData.estimated_age_max || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, estimated_age_max: parseInt(e.target.value) || null })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Sex</label>
                    <select
                      value={extractedData.sex || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, sex: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    >
                      <option value="">Unknown</option>
                      <option value="MALE">MALE</option>
                      <option value="FEMALE">FEMALE</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Measured Height (cm)</label>
                    <input
                      type="number"
                      value={extractedData.height_cm || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, height_cm: parseFloat(e.target.value) || null })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Blood Group</label>
                    <input
                      type="text"
                      value={extractedData.blood_group || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, blood_group: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Recovery Sector</label>
                    <input
                      type="text"
                      value={extractedData.recovery_location || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, recovery_location: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleSaveApproved}
                    className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20"
                  >
                    {submitting ? 'Saving to Database...' : 'Commit PM Record'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
