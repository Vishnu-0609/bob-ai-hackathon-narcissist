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
  Camera,
  X,
  Eye,
} from 'lucide-react';
import { api } from '../services/api';
import { PMCase, Incident, ImageEvidence } from '../types';
import { ImageUploadSection } from '../components/ImageUploadSection';
import { ImageEvidenceReview } from '../components/ImageEvidenceReview';
import { CaseDetailsModal } from '../components/CaseDetailsModal';

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

  // Case Image Management
  const [activeCaseForImage, setActiveCaseForImage] = useState<PMCase | null>(null);
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

  const handleImageEvidenceExtracted = (img: ImageEvidence) => {
    setIntakeImage(img);
    const obs = img.extraction_json?.observations || {};
    const current = extractedData || {
      estimated_age_min: null,
      estimated_age_max: null,
      sex: '',
      height_cm: null,
      blood_group: '',
      physical_description: '',
      scars: [],
      birthmarks: [],
      tattoos: [],
      clothing: [],
      jewellery: [],
      recovery_location: '',
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
      const autoNum = 'PM-' + String(cases.length + 1).padStart(3, '0');
      const savedCase = await api.reviewPM({
        review_id: reviewId,
        entity_type: 'PM',
        incident_id: activeIncident.id,
        case_identifier: extractedData.body_number || autoNum,
        approved_data: extractedData,
        decision: 'APPROVED',
        notes: 'Forensic examiner notes verified and approved.',
      });

      if (intakeImage) {
        try {
          await api.reviewImage(
            intakeImage.id,
            'APPROVED',
            intakeImage.extraction_json?.observations || {},
            'Auto-linked during intake commit',
            { pmId: savedCase.id || savedCase.body_number, incidentId: activeIncident.id }
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

  const handleOpenCaseImages = async (pmCase: PMCase) => {
    setActiveCaseForImage(pmCase);
    try {
      const imgs = await api.listImages({ incidentId: activeIncident?.id, pmId: pmCase.id });
      setCaseImages(imgs);
    } catch (e) {
      console.error(e);
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
            Mortuary post-mortem observations with IBM Bob text & Gemini 2.5 Flash cloud multimodal image analysis
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
          <span>New PM Examiner Intake (Text & Photos)</span>
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
                <th className="py-3 px-3">Photos</th>
                <th className="py-3 px-3 text-right">Reconcile</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {cases.map((pm) => (
                <tr key={pm.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3">
                    <button
                      type="button"
                      onClick={() => setInspectedCaseId(pm.body_number)}
                      className="font-bold font-mono text-sky-400 hover:text-sky-300 hover:underline inline-flex items-center gap-1 group text-left"
                      title={`Inspect full forensic record for ${pm.body_number}`}
                    >
                      <span>{pm.body_number}</span>
                      <Eye className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                    </button>
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    {(pm.sex || 'Unknown') + ' · ' + (pm.estimated_age_min ? `${pm.estimated_age_min}-${pm.estimated_age_max} yrs` : 'Unknown')}
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    {pm.height_cm ? `${pm.height_cm} cm` : 'Not measured'}
                  </td>
                  <td className="py-3 px-3 text-slate-300">{pm.blood_group || 'Pending'}</td>
                  <td className="py-3 px-3 font-sans text-slate-400 max-w-[200px] truncate">
                    {pm.scars?.length > 0 && `Scar: ${pm.scars[0]?.location || pm.scars[0]?.description || pm.scars[0]}; `}
                    {pm.tattoos?.length > 0 && `Tattoo: ${pm.tattoos[0]?.location || pm.tattoos[0]?.description || pm.tattoos[0]}`}
                    {!pm.scars?.length && !pm.tattoos?.length && 'None observed'}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-400 truncate max-w-[180px]">
                    {pm.recovery_location || 'N/A'}
                  </td>
                  <td className="py-3 px-3 font-sans">
                    <button
                      onClick={() => handleOpenCaseImages(pm)}
                      className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 text-xs font-medium transition"
                      title="Inspect/Attach Photos"
                    >
                      <Camera className="h-3.5 w-3.5" />
                      <span>Photos</span>
                    </button>
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

      {/* PM Intake Modal with Dual Examiner Notes & Gemini Image Input */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">New Post-Mortem Mortuary Intake</h3>
                  <p className="text-xs text-slate-400">Forensic Field Notes + Gemini 2.5 Flash Photographic Vision</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Section 1: Examiner Notes */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  1. Forensic Examiner Field Notes
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
                rows={3}
                placeholder="Paste verbatim examiner observations: 'Unidentified male body approx 32 to 36 yrs, measured 172 cm, healed surgical scar on left forearm, recovered from Coach B-3...'"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />

              <div className="flex items-center justify-end">
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
                      <span>Parse Notes</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Section Divider */}
            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-slate-800"></div>
              <span className="flex-shrink mx-4 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                2. Post-Mortem Photographic Evidence (Gemini 2.5 Flash)
              </span>
              <div className="flex-grow border-t border-slate-800"></div>
            </div>

            {/* Section 2: Gemini Image Upload Component */}
            <div>
              <ImageUploadSection
                activeIncident={activeIncident}
                recordType="PM"
                onEvidenceApproved={(img) => handleImageEvidenceExtracted(img)}
              />
            </div>

            {/* Structured PM Preview */}
            {extractedData && (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                    Integrated Post-Mortem Profile (Notes + Vision)
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
                    {submitting ? 'Saving to Database...' : 'Commit PM Record'}
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
                  <span>Forensic Photos for Body {activeCaseForImage.body_number}</span>
                </h3>
                <p className="text-xs text-slate-400">Recovery: {activeCaseForImage.recovery_location || 'N/A'}</p>
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
                  Post-Mortem Images ({caseImages.length})
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
              <p className="text-xs text-slate-500 italic">No photographic evidence attached to this body record yet.</p>
            )}

            {/* Upload New Image to this PM Case */}
            <div className="pt-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-2">
                Attach New Photo to {activeCaseForImage.body_number}
              </span>
              <ImageUploadSection
                activeIncident={activeIncident}
                recordType="PM"
                pmId={activeCaseForImage.id}
                onEvidenceApproved={async () => {
                  if (activeCaseForImage) {
                    const imgs = await api.listImages({ incidentId: activeIncident?.id, pmId: activeCaseForImage.id });
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
                  const imgs = await api.listImages({ incidentId: activeIncident?.id, pmId: activeCaseForImage.id });
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
          onNavigateToReconciliation={onNavigateToReconciliation}
        />
      )}
    </div>
  );
};
