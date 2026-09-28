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
  Image as ImageIcon,
  X,
  Eye,
  Camera,
} from 'lucide-react';
import { api } from '../services/api';
import { AMCase, Incident, ImageEvidence } from '../types';
import { ImageUploadSection } from '../components/ImageUploadSection';
import { ImageEvidenceReview } from '../components/ImageEvidenceReview';
import { CaseDetailsModal } from '../components/CaseDetailsModal';

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

  // Active Case Image Modal
  const [activeCaseForImage, setActiveCaseForImage] = useState<AMCase | null>(null);
  const [caseImages, setCaseImages] = useState<ImageEvidence[]>([]);
  const [selectedReviewImage, setSelectedReviewImage] = useState<ImageEvidence | null>(null);
  const [intakeImage, setIntakeImage] = useState<ImageEvidence | null>(null);
  const [inspectedCaseId, setInspectedCaseId] = useState<string | null>(null);

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

  const handleImageEvidenceExtracted = (img: ImageEvidence) => {
    setIntakeImage(img);
    const obs = img.extraction_json?.observations || {};
    const current = extractedData || {
      name: '',
      age: null,
      sex: '',
      height_cm: null,
      blood_group: '',
      physical_description: '',
      scars: [],
      birthmarks: [],
      tattoos: [],
      clothing: [],
      jewellery: [],
      last_seen_location: '',
    };

    const newClothing = [...(current.clothing || [])];
    (obs.clothing || []).forEach((c: any) => {
      const desc = typeof c === 'string' ? c : (c.description || `${c.color || ''} ${c.item_type || ''}`.trim());
      if (desc && !newClothing.includes(desc)) newClothing.push(desc);
    });

    const newJewellery = [...(current.jewellery || [])];
    (obs.jewellery || []).forEach((j: any) => {
      let desc = typeof j === 'string' ? j : (j.description || `${j.material_or_color || ''} ${j.item_type || ''}`.trim());
      if (typeof j === 'object' && j.location && !desc.includes(j.location)) desc = `${desc} (${j.location})`;
      if (desc && !newJewellery.includes(desc)) newJewellery.push(desc);
    });

    const newTattoos = [...(current.tattoos || [])];
    (obs.tattoos || []).forEach((t: any) => {
      if (typeof t === 'string') {
        newTattoos.push({ location: 'unspecified', description: t });
      } else {
        newTattoos.push({
          location: t.location || 'shoulder',
          description: t.description || 'tattoo',
          design_motifs: t.design_motifs || [],
          colors: t.colors || [],
        });
      }
    });

    const newScars = [...(current.scars || [])];
    const newBirthmarks = [...(current.birthmarks || [])];
    (obs.scars_or_marks || []).forEach((s: any) => {
      if (typeof s === 'string') {
        newScars.push({ location: 'forearm', description: s });
      } else {
        const mtype = (s.mark_type || 'scar').toLowerCase();
        const entry = {
          location: s.location || 'forearm',
          description: s.description || mtype,
        };
        if (mtype === 'birthmark' || mtype === 'mole') {
          newBirthmarks.push(entry);
        } else {
          newScars.push(entry);
        }
      }
    });

    // Enrich physical description
    let updatedPhys = current.physical_description || '';
    const addedTraits: string[] = [];
    (obs.physical_characteristics || []).forEach((p: any) => {
      if (typeof p === 'object' && p.value && p.value !== 'UNKNOWN') {
        addedTraits.push(`${(p.attribute || '').replace('_', ' ')}: ${p.value}`);
      } else if (typeof p === 'string' && p.trim()) {
        addedTraits.push(p.trim());
      }
    });
    if (addedTraits.length > 0) {
      const traitStr = `[Photo]: ${addedTraits.join(', ')}`;
      if (!updatedPhys) updatedPhys = traitStr;
      else if (!updatedPhys.includes(traitStr)) updatedPhys = `${updatedPhys} | ${traitStr}`;
    }

    setExtractedData({
      ...current,
      clothing: newClothing,
      jewellery: newJewellery,
      tattoos: newTattoos,
      scars: newScars,
      birthmarks: newBirthmarks,
      physical_description: updatedPhys,
    });
    setShowModal(true);
  };

  const handleSaveApproved = async () => {
    if (!activeIncident || !extractedData) return;
    setSubmitting(true);
    try {
      const autoNum = 'AM-' + String(cases.length + 1).padStart(3, '0');
      const savedCase = await api.reviewAM({
        review_id: reviewId,
        entity_type: 'AM',
        incident_id: activeIncident.id,
        case_identifier: extractedData.case_number || autoNum,
        approved_data: extractedData,
        decision: 'APPROVED',
        notes: 'Verified and approved by field intake team.',
      });

      if (intakeImage) {
        try {
          await api.reviewImage(
            intakeImage.id,
            'APPROVED',
            intakeImage.extraction_json?.observations || {},
            'Auto-linked during intake commit',
            { amId: savedCase.id || savedCase.case_number, incidentId: activeIncident.id }
          );
        } catch (e) {
          console.error("Failed to link intake image", e);
        }
      }

      setShowModal(false);
      setIntakeText('');
      setExtractedData(null);
      setReviewId(null);
      setIntakeImage(null);
      loadCases();
    } catch (err: any) {
      alert(`Save Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenCaseImages = async (amCase: AMCase) => {
    setActiveCaseForImage(amCase);
    try {
      const imgs = await api.listImages({ incidentId: activeIncident?.id, amId: amCase.id });
      setCaseImages(imgs);
    } catch (e) {
      console.error(e);
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
            Family-reported missing person descriptions with IBM Bob text & Gemini 2.5 Flash image extraction
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
          <span>New AM Intake (Text & Photo Vision)</span>
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
                <th className="py-3 px-3">Photos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {cases.map((am) => (
                <tr key={am.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3">
                    <button
                      type="button"
                      onClick={() => setInspectedCaseId(am.case_number)}
                      className="font-bold font-mono text-sky-400 hover:text-sky-300 hover:underline inline-flex items-center gap-1 group text-left"
                      title={`Inspect full forensic record for ${am.case_number}`}
                    >
                      <span>{am.case_number}</span>
                      <Eye className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                    </button>
                  </td>
                  <td className="py-3 px-3 font-sans font-medium text-slate-200">{am.name}</td>
                  <td className="py-3 px-3 text-slate-300">
                    {(am.sex || 'Unknown') + ' · ' + (am.age ? `${am.age} yrs` : 'Unknown')}
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    {am.height_cm ? `${am.height_cm} cm` : 'Not recorded'}
                  </td>
                  <td className="py-3 px-3 text-slate-300">{am.blood_group || 'Not recorded'}</td>
                  <td className="py-3 px-3 font-sans text-slate-400 max-w-[220px] truncate">
                    {am.scars?.length > 0 && `Scar: ${am.scars[0]?.location || am.scars[0]?.description || am.scars[0]}; `}
                    {am.tattoos?.length > 0 && `Tattoo: ${am.tattoos[0]?.location || am.tattoos[0]?.description || am.tattoos[0]}`}
                    {!am.scars?.length && !am.tattoos?.length && 'None recorded'}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-400 truncate max-w-[180px]">
                    {am.last_seen_location || 'N/A'}
                  </td>
                  <td className="py-3 px-3 font-sans">
                    <button
                      onClick={() => handleOpenCaseImages(am)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 text-xs font-medium transition"
                      title="Upload or Inspect Photos for this Case"
                    >
                      <Camera className="h-3.5 w-3.5" />
                      <span>Photo Vision</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AM Intake Modal with Dual Text & Gemini Image Input */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">New Ante-Mortem Intake</h3>
                  <p className="text-xs text-slate-400">IBM Bob Narrative Parser + Gemini Cloud Multimodal Vision</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Section 1: Narrative & Voice Intake */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  1. Family Narrative / Voice Transcript
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
                rows={3}
                placeholder="Paste verbatim family interview narrative or speak: 'My brother was 34 years old, approx 173 cm, had a scar on his left forearm, bird tattoo on right shoulder, wearing a blue shirt...'"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />

              <div className="flex items-center justify-between">
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
                      <span>Parse Narrative</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Section Divider */}
            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-slate-800"></div>
              <span className="flex-shrink mx-4 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                2. Multimodal Image Evidence (Gemini 2.5 Flash)
              </span>
              <div className="flex-grow border-t border-slate-800"></div>
            </div>

            {/* Section 2: Gemini Image Upload Component */}
            <div>
              <ImageUploadSection
                activeIncident={activeIncident}
                recordType="AM"
                onEvidenceApproved={(img) => handleImageEvidenceExtracted(img)}
              />
            </div>

            {/* Structured Preview & Save Section */}
            {extractedData && (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                    Structured Profile Preview (Text + Vision Integrated)
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
                    <label className="text-[10px] text-slate-400">Sector / Location</label>
                    <input
                      type="text"
                      value={extractedData.last_seen_location || ''}
                      onChange={(e) => setExtractedData({ ...extractedData, last_seen_location: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono"
                    />
                  </div>
                </div>

                <div className="text-xs text-slate-300 space-y-2 pt-2 border-t border-slate-800">
                  {extractedData.clothing?.length > 0 && (
                    <div>
                      <span className="text-[11px] font-bold text-sky-400 uppercase tracking-wider block mb-1">
                        Visible Clothing ({extractedData.clothing.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {extractedData.clothing.map((c: any, i: number) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20 text-[11px] font-mono">
                            {typeof c === 'string' ? c : c.description || `${c.color || ''} ${c.item_type || ''}`}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {extractedData.jewellery?.length > 0 && (
                    <div>
                      <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider block mb-1">
                        Visible Jewellery & Accessories ({extractedData.jewellery.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {extractedData.jewellery.map((j: any, i: number) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[11px] font-mono">
                            {typeof j === 'string' ? j : `${j.description || j.item_type || ''} ${j.location ? `(${j.location})` : ''}`}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {extractedData.tattoos?.length > 0 && (
                    <div>
                      <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider block mb-1">
                        Visible Tattoos ({extractedData.tattoos.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {extractedData.tattoos.map((t: any, i: number) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[11px] font-mono">
                            {typeof t === 'string' ? t : `${t.description || 'tattoo'} [${t.location || 'shoulder'}]`}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {(extractedData.scars?.length > 0 || extractedData.birthmarks?.length > 0) && (
                    <div>
                      <span className="text-[11px] font-bold text-rose-400 uppercase tracking-wider block mb-1">
                        Scars & Marks ({(extractedData.scars?.length || 0) + (extractedData.birthmarks?.length || 0)})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {(extractedData.scars || []).map((s: any, i: number) => (
                          <span key={`s-${i}`} className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 text-[11px] font-mono">
                            {typeof s === 'string' ? s : `${s.description || 'scar'} [${s.location || 'forearm'}]`}
                          </span>
                        ))}
                        {(extractedData.birthmarks || []).map((b: any, i: number) => (
                          <span key={`b-${i}`} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-mono">
                            {typeof b === 'string' ? b : `${b.description || 'birthmark'} [${b.location || 'body'}]`}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
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
                    {submitting ? 'Saving to Database...' : 'Verify & Commit AM Record'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Case-Specific Image Gallery & Upload Dialog */}
      {activeCaseForImage && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Camera className="h-5 w-5 text-sky-400" />
                  <span>Image Evidence for Case {activeCaseForImage.case_number}</span>
                </h3>
                <p className="text-xs text-slate-400">{activeCaseForImage.name}</p>
              </div>
              <button
                onClick={() => {
                  setActiveCaseForImage(null);
                  setSelectedReviewImage(null);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Existing Case Images */}
            {caseImages.length > 0 ? (
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Associated Case Photos ({caseImages.length})
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {caseImages.map((img) => (
                    <div
                      key={img.id}
                      onClick={() => setSelectedReviewImage(img)}
                      className="cursor-pointer bg-slate-950 rounded-xl p-2.5 border border-slate-800 hover:border-sky-500 transition space-y-1.5"
                    >
                      <div className="h-28 rounded-lg overflow-hidden bg-slate-900 flex items-center justify-center">
                        <img
                          src={api.getImageFileUrl(img.id)}
                          alt={img.original_filename}
                          className="h-full w-full object-contain"
                        />
                      </div>
                      <div className="text-[11px] font-bold text-white truncate">{img.image_type}</div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>{img.human_review_status}</span>
                        <span className="text-sky-400 font-mono">Inspect</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No photographic evidence attached to this case yet.</p>
            )}

            {/* Upload New Image to this AM Case */}
            <div className="pt-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-2">
                Attach New Photo to {activeCaseForImage.case_number}
              </span>
              <ImageUploadSection
                activeIncident={activeIncident}
                recordType="AM"
                amId={activeCaseForImage.id}
                onEvidenceApproved={async () => {
                  if (activeCaseForImage) {
                    const imgs = await api.listImages({ incidentId: activeIncident?.id, amId: activeCaseForImage.id });
                    setCaseImages(imgs);
                    loadCases();
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Review Modal for Selected Gallery Image */}
      {selectedReviewImage && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm flex items-center justify-center p-4 z-[60] overflow-y-auto">
          <div className="max-w-4xl w-full">
            <ImageEvidenceReview
              image={selectedReviewImage}
              onClose={() => setSelectedReviewImage(null)}
              onReviewCompleted={async () => {
                setSelectedReviewImage(null);
                if (activeCaseForImage) {
                  const imgs = await api.listImages({ incidentId: activeIncident?.id, amId: activeCaseForImage.id });
                  setCaseImages(imgs);
                  loadCases();
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Case Details Inspector Modal */}
      {inspectedCaseId && (
        <CaseDetailsModal
          caseId={inspectedCaseId}
          onClose={() => setInspectedCaseId(null)}
        />
      )}
    </div>
  );
};
