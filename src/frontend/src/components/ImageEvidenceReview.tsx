import React, { useState } from 'react';
import {
  Image as ImageIcon,
  CheckCircle2,
  XCircle,
  Edit3,
  RotateCw,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  ZoomIn,
  Eye,
  Plus,
  Trash2,
  Info,
  Layers,
  Check,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import {
  ImageEvidence,
  ClothingObservation,
  JewelleryObservation,
  TattooObservation,
  ScarObservation,
} from '../types';

interface ImageEvidenceReviewProps {
  image: ImageEvidence;
  amId?: string;
  pmId?: string;
  incidentId?: string;
  recordType?: 'AM' | 'PM';
  onReviewCompleted?: (updated: ImageEvidence) => void;
  onClose?: () => void;
}

export const ImageEvidenceReview: React.FC<ImageEvidenceReviewProps> = ({
  image,
  amId,
  pmId,
  incidentId,
  recordType,
  onReviewCompleted,
  onClose,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [showFullImage, setShowFullImage] = useState(false);
  const [currentImage, setCurrentImage] = useState<ImageEvidence>(image);

  // Editable observation state
  const rawObs = currentImage.extraction_json?.observations || {
    clothing: [],
    jewellery: [],
    tattoos: [],
    scars_or_marks: [],
    physical_characteristics: [],
    visible_text: [],
    other_observations: [],
  };

  const [clothing, setClothing] = useState<ClothingObservation[]>(rawObs.clothing || []);
  const [jewellery, setJewellery] = useState<JewelleryObservation[]>(rawObs.jewellery || []);
  const [tattoos, setTattoos] = useState<TattooObservation[]>(rawObs.tattoos || []);
  const [scars, setScars] = useState<ScarObservation[]>(rawObs.scars_or_marks || []);

  const quality = currentImage.extraction_json?.image_quality || {
    status: 'GOOD',
    occlusion: false,
    lighting: 'ADEQUATE',
    resolution_assessment: 'SUFFICIENT',
  };

  const targetCase = currentImage.am_id || amId || currentImage.pm_id || pmId;

  const handleRetryAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await api.analyzeImage(currentImage.id);
      const updated = await api.getImageAnalysis(currentImage.id);
      setCurrentImage(updated);
      const newObs = updated.extraction_json?.observations || {};
      setClothing(newObs.clothing || []);
      setJewellery(newObs.jewellery || []);
      setTattoos(newObs.tattoos || []);
      setScars(newObs.scars_or_marks || []);
      if (onReviewCompleted) onReviewCompleted(updated);
    } catch (err: any) {
      alert(`Image Analysis Error: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReviewDecision = async (
    decision: 'APPROVED' | 'MODIFIED_AND_APPROVED' | 'REJECTED'
  ) => {
    setSubmitting(true);
    try {
      const approvedPayload = {
        observations: {
          clothing,
          jewellery,
          tattoos,
          scars_or_marks: scars,
          physical_characteristics: rawObs.physical_characteristics || [],
          visible_text: rawObs.visible_text || [],
          other_observations: rawObs.other_observations || [],
        },
        summary: currentImage.extraction_json?.summary,
      };

      const updated = await api.reviewImage(
        currentImage.id,
        decision,
        approvedPayload,
        reviewNotes,
        {
          amId: currentImage.am_id || amId,
          pmId: currentImage.pm_id || pmId,
          incidentId: currentImage.incident_id || incidentId,
          autoCreateCase: true,
          recordType: recordType || (currentImage.am_id ? 'AM' : (currentImage.pm_id ? 'PM' : undefined)),
        }
      );
      setCurrentImage(updated);
      setIsEditing(false);
      if (onReviewCompleted) onReviewCompleted(updated);
      if (onClose) onClose();
    } catch (err: any) {
      alert(`Review Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const imageUrl = api.getImageFileUrl(currentImage.id);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
      {/* Header */}
      <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-sky-600 flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white">Multimodal Evidence Review</h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                {currentImage.gemini_model || 'gemini-2.5-flash'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {currentImage.original_filename} ({currentImage.image_type}) · SHA-256: {currentImage.sha256.slice(0, 10)}...
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-mono px-2.5 py-1 rounded-lg border font-semibold ${
              currentImage.human_review_status === 'APPROVED' || currentImage.human_review_status === 'MODIFIED_AND_APPROVED'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : currentImage.human_review_status === 'REJECTED'
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse'
            }`}
          >
            {currentImage.human_review_status === 'PENDING_REVIEW'
              ? 'PENDING HUMAN REVIEW'
              : currentImage.human_review_status}
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Body: Split View (Image on Left, Extracted Evidence on Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-hidden">
        {/* Left: Image Viewer & Metadata (5 Cols) */}
        <div className="lg:col-span-5 bg-slate-950/80 p-5 border-r border-slate-800 flex flex-col justify-between overflow-y-auto space-y-4">
          <div className="space-y-3">
            <div className="relative group rounded-xl overflow-hidden border border-slate-800 bg-slate-900 aspect-video sm:aspect-square flex items-center justify-center">
              <img
                src={imageUrl}
                alt={currentImage.original_filename}
                className="max-h-full max-w-full object-contain cursor-pointer"
                onClick={() => setShowFullImage(true)}
              />
              <button
                onClick={() => setShowFullImage(true)}
                className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-950/80 text-slate-200 hover:text-white border border-slate-700 shadow-md backdrop-blur-sm opacity-90 group-hover:opacity-100 transition"
                title="View Full Resolution Image"
              >
                <ZoomIn className="h-4 w-4" />
              </button>
            </div>

            {/* Quality Assessment & Image Metadata */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2 text-xs">
              <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
                <span>Image Forensics</span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                    quality.status === 'GOOD'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}
                >
                  Quality: {quality.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-slate-400 text-[11px]">
                <div>
                  Occlusion: <span className="font-semibold text-slate-200">{quality.occlusion ? 'Yes' : 'None'}</span>
                </div>
                <div>
                  Lighting: <span className="font-semibold text-slate-200">{quality.lighting || 'Standard'}</span>
                </div>
                <div>
                  Size: <span className="font-semibold text-slate-200">{(currentImage.file_size / 1024).toFixed(1)} KB</span>
                </div>
                <div>
                  Type: <span className="font-semibold text-slate-200">{currentImage.image_type}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-500 truncate">
                SHA-256: {currentImage.sha256}
              </div>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleRetryAnalysis}
              disabled={analyzing}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-750 text-sky-400 text-xs font-semibold border border-slate-700 transition"
            >
              <RotateCw className={`h-3.5 w-3.5 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Analyzing with Gemini 2.5 Flash...' : 'Re-Run Gemini Analysis'}</span>
            </button>
          </div>
        </div>

        {/* Right: Structured Evidence Review (7 Cols) */}
        <div className="lg:col-span-7 p-6 overflow-y-auto space-y-5">
          {/* Interpol / Ethical Boundary Banner */}
          <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-300 text-xs flex items-start gap-2.5">
            <Info className="h-4 w-4 text-sky-400 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] leading-relaxed">
              <b>Mandatory Forensic Safeguard:</b> Gemini visual confidence scores denote visual observation clarity, NOT identity probability. Gemini does not match faces or make identification decisions.
            </p>
          </div>

          {/* Database Persistence & Case Status Banner */}
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400 flex-shrink-0" />
              <span>
                <b>Database Persistence Active:</b> Verified clothing, jewellery, tattoos & scars will be stored into{' '}
                <span className="font-mono font-bold text-white bg-slate-900 px-1.5 py-0.5 rounded border border-slate-700">
                  {targetCase || 'Database Case Record'}
                </span>
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
              Live DB Sync
            </span>
          </div>

          {/* Observations Header & Edit Toggle */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Observable Visual Evidence
              </h3>
              <p className="text-[11px] text-slate-400">
                Extracted from image and subject to human forensic verification
              </p>
            </div>

            <button
              onClick={() => setIsEditing(!isEditing)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border transition ${
                isEditing
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                  : 'bg-slate-800 hover:bg-slate-750 text-slate-300 border-slate-700'
              }`}
            >
              <Edit3 className="h-3.5 w-3.5" />
              <span>{isEditing ? 'Editing Mode Active' : 'Edit Observations'}</span>
            </button>
          </div>

          {/* Clothing Observations */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Visible Clothing ({clothing.length})
              </span>
              {isEditing && (
                <button
                  type="button"
                  onClick={() =>
                    setClothing([
                      ...clothing,
                      { item_type: 'garment', color: '', description: '', status: 'OBSERVED', confidence: 0.9 },
                    ])
                  }
                  className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
                >
                  <Plus className="h-3 w-3" /> Add Item
                </button>
              )}
            </div>

            {clothing.length > 0 ? (
              <div className="space-y-2">
                {clothing.map((c, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    {isEditing ? (
                      <div className="flex-1 grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={c.description || ''}
                          placeholder="Description (e.g. blue collared shirt)"
                          onChange={(e) => {
                            const updated = [...clothing];
                            updated[idx].description = e.target.value;
                            setClothing(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs col-span-2"
                        />
                        <input
                          type="text"
                          value={c.color || ''}
                          placeholder="Color (e.g. blue)"
                          onChange={(e) => {
                            const updated = [...clothing];
                            updated[idx].color = e.target.value;
                            setClothing(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs"
                        />
                        <input
                          type="text"
                          value={c.item_type || ''}
                          placeholder="Item (e.g. shirt)"
                          onChange={(e) => {
                            const updated = [...clothing];
                            updated[idx].item_type = e.target.value;
                            setClothing(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs"
                        />
                      </div>
                    ) : (
                      <div>
                        <span className="font-semibold text-white">
                          {c.description || `${c.color || ''} ${c.item_type || 'clothing'}`.trim()}
                        </span>
                        {c.notes && <p className="text-[11px] text-slate-400 mt-0.5">{c.notes}</p>}
                      </div>
                    )}

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                        Conf: {(c.confidence * 100).toFixed(0)}%
                      </span>
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => setClothing(clothing.filter((_, i) => i !== idx))}
                          className="p-1 text-rose-400 hover:text-rose-300"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No visible clothing items detected in this image.</p>
            )}
          </div>

          {/* Jewellery Observations */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Visible Jewellery & Accessories ({jewellery.length})
              </span>
              {isEditing && (
                <button
                  type="button"
                  onClick={() =>
                    setJewellery([
                      ...jewellery,
                      { item_type: 'ring', material_or_color: 'silver', description: '', status: 'OBSERVED', confidence: 0.85 },
                    ])
                  }
                  className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
                >
                  <Plus className="h-3 w-3" /> Add Jewellery
                </button>
              )}
            </div>

            {jewellery.length > 0 ? (
              <div className="space-y-2">
                {jewellery.map((j, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    {isEditing ? (
                      <div className="flex-1 grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={j.description || ''}
                          placeholder="Description (e.g. silver-colored ring)"
                          onChange={(e) => {
                            const updated = [...jewellery];
                            updated[idx].description = e.target.value;
                            setJewellery(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs col-span-2"
                        />
                        <input
                          type="text"
                          value={j.location || ''}
                          placeholder="Location (e.g. right ring finger)"
                          onChange={(e) => {
                            const updated = [...jewellery];
                            updated[idx].location = e.target.value;
                            setJewellery(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs"
                        />
                        <input
                          type="text"
                          value={j.material_or_color || ''}
                          placeholder="Material/Color"
                          onChange={(e) => {
                            const updated = [...jewellery];
                            updated[idx].material_or_color = e.target.value;
                            setJewellery(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs"
                        />
                      </div>
                    ) : (
                      <div>
                        <span className="font-semibold text-white">
                          {j.description || `${j.material_or_color || ''} ${j.item_type || 'jewellery'}`.trim()}
                        </span>
                        {j.location && (
                          <span className="text-slate-400 font-mono text-[11px] ml-2">
                            ({j.location})
                          </span>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                        Conf: {(j.confidence * 100).toFixed(0)}%
                      </span>
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => setJewellery(jewellery.filter((_, i) => i !== idx))}
                          className="p-1 text-rose-400 hover:text-rose-300"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No visible jewellery detected.</p>
            )}
          </div>

          {/* Tattoo Observations */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Visible Tattoos ({tattoos.length})
              </span>
              {isEditing && (
                <button
                  type="button"
                  onClick={() =>
                    setTattoos([
                      ...tattoos,
                      { description: '', location: 'shoulder', status: 'OBSERVED', confidence: 0.85 },
                    ])
                  }
                  className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
                >
                  <Plus className="h-3 w-3" /> Add Tattoo
                </button>
              )}
            </div>

            {tattoos.length > 0 ? (
              <div className="space-y-2">
                {tattoos.map((t, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    {isEditing ? (
                      <div className="flex-1 grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={t.description || ''}
                          placeholder="Tattoo description (e.g. bird in flight)"
                          onChange={(e) => {
                            const updated = [...tattoos];
                            updated[idx].description = e.target.value;
                            setTattoos(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs col-span-2"
                        />
                        <input
                          type="text"
                          value={t.location || ''}
                          placeholder="Location (e.g. right shoulder)"
                          onChange={(e) => {
                            const updated = [...tattoos];
                            updated[idx].location = e.target.value;
                            setTattoos(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs col-span-2"
                        />
                      </div>
                    ) : (
                      <div>
                        <span className="font-semibold text-white">{t.description || 'Tattoo observed'}</span>
                        {t.location && (
                          <span className="text-sky-400 font-mono text-[11px] ml-2">
                            [Location: {t.location}]
                          </span>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                        Conf: {(t.confidence * 100).toFixed(0)}%
                      </span>
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => setTattoos(tattoos.filter((_, i) => i !== idx))}
                          className="p-1 text-rose-400 hover:text-rose-300"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No visible tattoos detected.</p>
            )}
          </div>

          {/* Scars & Marks Observations */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Visible Scars & Distinguishing Marks ({scars.length})
              </span>
              {isEditing && (
                <button
                  type="button"
                  onClick={() =>
                    setScars([
                      ...scars,
                      { description: '', location: 'forearm', mark_type: 'scar', status: 'OBSERVED', confidence: 0.8 },
                    ])
                  }
                  className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
                >
                  <Plus className="h-3 w-3" /> Add Scar/Mark
                </button>
              )}
            </div>

            {scars.length > 0 ? (
              <div className="space-y-2">
                {scars.map((s, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    {isEditing ? (
                      <div className="flex-1 grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={s.description || ''}
                          placeholder="Description (e.g. 3 cm linear scar)"
                          onChange={(e) => {
                            const updated = [...scars];
                            updated[idx].description = e.target.value;
                            setScars(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs col-span-2"
                        />
                        <input
                          type="text"
                          value={s.location || ''}
                          placeholder="Location (e.g. left forearm)"
                          onChange={(e) => {
                            const updated = [...scars];
                            updated[idx].location = e.target.value;
                            setScars(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs"
                        />
                        <input
                          type="text"
                          value={s.mark_type || ''}
                          placeholder="Type (scar, birthmark, mole)"
                          onChange={(e) => {
                            const updated = [...scars];
                            updated[idx].mark_type = e.target.value;
                            setScars(updated);
                          }}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs"
                        />
                      </div>
                    ) : (
                      <div>
                        <span className="font-semibold text-white">{s.description || 'Mark observed'}</span>
                        {s.location && (
                          <span className="text-amber-400 font-mono text-[11px] ml-2">
                            [{s.location}]
                          </span>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                        Conf: {(s.confidence * 100).toFixed(0)}%
                      </span>
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => setScars(scars.filter((_, i) => i !== idx))}
                          className="p-1 text-rose-400 hover:text-rose-300"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No visible scars or marks detected.</p>
            )}
          </div>

          {/* Review Notes Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Forensic Reviewer Notes (Optional)
            </label>
            <input
              type="text"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="e.g. Visual features verified against family photographic reference"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 font-mono"
            />
          </div>

          {/* Action Buttons: Accept All, Edit, Reject */}
          <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-end gap-2.5">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleReviewDecision('REJECTED')}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-rose-950/60 text-slate-300 hover:text-rose-200 border border-slate-700 text-xs font-bold transition disabled:opacity-50"
            >
              <XCircle className="h-4 w-4 text-rose-400" />
              <span>Reject Evidence</span>
            </button>

            {isEditing ? (
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleReviewDecision('MODIFIED_AND_APPROVED')}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold shadow-lg shadow-sky-600/20 transition disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                <span>Save Modifications & Verify</span>
              </button>
            ) : (
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleReviewDecision('APPROVED')}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 transition disabled:opacity-50"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>Accept All as Verified Evidence</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Lightbox Modal for Full-Resolution Image */}
      {showFullImage && (
        <div
          className="fixed inset-0 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-4 z-[99] cursor-zoom-out"
          onClick={() => setShowFullImage(false)}
        >
          <div className="relative max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl p-2 shadow-2xl overflow-hidden">
            <img
              src={imageUrl}
              alt={currentImage.original_filename}
              className="max-h-[85vh] max-w-full object-contain rounded-xl mx-auto"
            />
            <div className="absolute bottom-4 left-4 right-4 bg-slate-950/80 backdrop-blur-sm p-2.5 rounded-xl border border-slate-800 text-xs text-white flex items-center justify-between">
              <span>{currentImage.original_filename}</span>
              <span className="font-mono text-sky-400">SHA-256: {currentImage.sha256}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
