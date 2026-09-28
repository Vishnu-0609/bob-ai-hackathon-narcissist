import React, { useState, useEffect } from 'react';
import {
  Users,
  Search,
  Plus,
  Mic,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Clock,
  MapPin,
  FileText,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { AMCase, Incident } from '../types';

interface AMRecordsProps {
  activeIncident: Incident | null;
}

export const AMRecords: React.FC<AMRecordsProps> = ({ activeIncident }) => {
  const [cases, setCases] = useState<AMCase[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // Intake Modal State
  const [showModal, setShowModal] = useState(false);
  const [intakeText, setIntakeText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    loadCases();
  }, [activeIncident]);

  const loadCases = async () => {
    if (!activeIncident) return;
    setLoading(true);
    try {
      const data = await api.listAMCases(activeIncident.id, search);
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
      const res = await api.extractAM(intakeText, activeIncident.id);
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
      const autoNum = 'AM-' + String(cases.length + 1).padStart(3, '0');
      await api.reviewAM({
        review_id: reviewId,
        entity_type: 'AM',
        incident_id: activeIncident.id,
        case_identifier: extractedData.case_number || autoNum,
        approved_data: extractedData,
        decision: 'APPROVED',
        notes: 'Verified and approved by field intake team.',
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
      'My brother Arjun Mohanty is 34 years old, about 173 cm tall, has a 3 cm surgical scar on his left forearm and a tattoo of a bird in flight on his right shoulder. He was wearing a blue shirt and dark jeans, and had a silver ring on his right hand. Last seen in Coromandel Express Coach B-3.'
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white">Ante-Mortem (AM) Records</h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {cases.length} Profiles Logged
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Family-reported missing person descriptions and medical/dental records
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
          <span>New AM Intake (IBM Bob Assisted)</span>
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
              placeholder="Search by case number, name, physical description, or recovery sector..."
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

      {/* AM Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-3">Case ID</th>
                <th className="py-3 px-3">Name</th>
                <th className="py-3 px-3">Sex / Age</th>
                <th className="py-3 px-3">Stature</th>
                <th className="py-3 px-3">Blood Group</th>
                <th className="py-3 px-3">Identifying Scars / Tattoos</th>
                <th className="py-3 px-3">Last Seen Location</th>
                <th className="py-3 px-3">Provenance / Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {cases.map((am) => (
                <tr key={am.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 font-bold text-sky-400">{am.case_number}</td>
                  <td className="py-3 px-3 font-sans font-medium text-slate-200">{am.name}</td>
                  <td className="py-3 px-3 text-slate-300">
                    {(am.sex || 'Unknown') + ' · ' + (am.age ? `${am.age} yrs` : 'Unknown')}
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    {am.height_cm ? `${am.height_cm} cm` : 'Not recorded'}
                  </td>
                  <td className="py-3 px-3 text-slate-300">{am.blood_group || 'Not recorded'}</td>
                  <td className="py-3 px-3 font-sans text-slate-400 max-w-[220px] truncate">
                    {am.scars?.length > 0 && `Scar: ${am.scars[0]?.location || am.scars[0]}; `}
                    {am.tattoos?.length > 0 && `Tattoo: ${am.tattoos[0]?.location || am.tattoos[0]}`}
                    {!am.scars?.length && !am.tattoos?.length && 'None recorded'}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-400 truncate max-w-[180px]">
                    {am.last_seen_location || 'N/A'}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-400 text-[11px]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {am.source_type || 'FAMILY_INTERVIEW'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AM Intake Modal with IBM Bob Extraction */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <h3 className="text-base font-bold text-white">AM Free-Text & Voice Intake (IBM Bob)</h3>
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
                  Family Narrative / Voice Transcript
                </label>
                <button
                  type="button"
                  onClick={loadDemoSample}
                  className="text-xs text-sky-400 hover:text-sky-300 font-medium"
                >
                  Load Demo Narrative Sample
                </button>
              </div>

              <textarea
                value={intakeText}
                onChange={(e) => setIntakeText(e.target.value)}
                rows={4}
                placeholder="Paste verbatim family interview narrative or speak: 'My brother was 34 years old, approx 173 cm, had a scar on his left forearm, bird tattoo on right shoulder, wearing a blue shirt...'"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />

              <div className="flex items-center justify-between mt-2">
                <button
                  type="button"
                  onClick={() => setIsRecording(!isRecording)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                    isRecording
                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                      : 'bg-slate-800 hover:bg-slate-750 text-slate-300 border-slate-700'
                  }`}
                >
                  <Mic className="h-3.5 w-3.5" />
                  <span>{isRecording ? 'Listening (Voice Intake Active)...' : 'Simulate Voice Intake'}</span>
                </button>

                <button
                  type="button"
                  disabled={extracting || !intakeText.trim()}
                  onClick={handleExtractBob}
                  className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold shadow-md shadow-sky-500/20 disabled:opacity-50 transition"
                >
                  {extracting ? (
                    <span>Bob Agent Extracting...</span>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Extract Structured Profile</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Structured Preview */}
            {extractedData && (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                    IBM Bob Structured Extraction Preview
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Human Verification Required
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-400">Name</label>
                    <input
                      type="text"
                      value={extractedData.name || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, name: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Age</label>
                    <input
                      type="number"
                      value={extractedData.age || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, age: parseInt(e.target.value) || null })}
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
                    <label className="text-[10px] text-slate-400">Height (cm)</label>
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
                    <label className="text-[10px] text-slate-400">Sector</label>
                    <input
                      type="text"
                      value={extractedData.last_seen_location || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, last_seen_location: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                </div>

                <div className="text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">Extracted Features:</span>{' '}
                  {extractedData.scars?.length > 0 && `Scars: ${JSON.stringify(extractedData.scars)}; `}
                  {extractedData.tattoos?.length > 0 && `Tattoos: ${JSON.stringify(extractedData.tattoos)}; `}
                  {extractedData.clothing?.length > 0 && `Clothing: ${extractedData.clothing.join(', ')}`}
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
                    {submitting ? 'Committing to DB...' : 'Verify & Approve AM Record'}
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
