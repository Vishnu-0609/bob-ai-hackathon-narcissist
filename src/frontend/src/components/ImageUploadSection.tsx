import React, { useState, useRef, useEffect } from 'react';
import {
  Upload,
  Image as ImageIcon,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  X,
  Plus,
  RotateCw,
  Eye,
  Trash2,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import { ImageEvidence, Incident } from '../types';
import { ImageEvidenceReview } from './ImageEvidenceReview';

interface ImageUploadSectionProps {
  activeIncident: Incident | null;
  recordType: 'AM' | 'PM';
  amId?: string;
  pmId?: string;
  onEvidenceApproved?: (image: ImageEvidence) => void;
}

interface UploadItem {
  id: string;
  file: File;
  previewUrl: string;
  imageType: string;
  status: 'QUEUED' | 'UPLOADING' | 'ANALYZING' | 'DONE' | 'ERROR';
  error?: string;
  imageEvidence?: ImageEvidence;
}

export const ImageUploadSection: React.FC<ImageUploadSectionProps> = ({
  activeIncident,
  recordType,
  amId,
  pmId,
  onEvidenceApproved,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isProcessingAll, setIsProcessingAll] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeReviewImage, setActiveReviewImage] = useState<ImageEvidence | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const amTypes = ['PORTRAIT', 'FULL_BODY', 'CLOTHING', 'TATTOO', 'SCAR', 'JEWELLERY', 'OTHER'];
  const pmTypes = ['BODY_OVERVIEW', 'CLOTHING', 'TATTOO', 'SCAR', 'JEWELLERY', 'INJURY', 'DENTAL', 'OTHER'];
  const availableTypes = recordType === 'AM' ? amTypes : pmTypes;
  const defaultType = recordType === 'AM' ? 'PORTRAIT' : 'BODY_OVERVIEW';

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      items.forEach((it) => {
        if (it.previewUrl) URL.revokeObjectURL(it.previewUrl);
      });
    };
  }, []);

  const addFiles = (fileList: FileList | File[]) => {
    setErrorMsg(null);
    const newItems: UploadItem[] = [];
    const validExtensions = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];

    Array.from(fileList).forEach((file) => {
      if (!validExtensions.includes(file.type.toLowerCase())) {
        setErrorMsg(`"${file.name}" skipped: unsupported format (use JPG, PNG, WEBP).`);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setErrorMsg(`"${file.name}" skipped: exceeds 10 MB limit.`);
        return;
      }

      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      newItems.push({
        id,
        file,
        previewUrl: URL.createObjectURL(file),
        imageType: defaultType,
        status: 'QUEUED',
      });
    });

    if (newItems.length > 0) {
      setItems((prev) => [...prev, ...newItems]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const handleRemoveItem = (id: string) => {
    setItems((prev) => {
      const target = prev.find((it) => it.id === id);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((it) => it.id !== id);
    });
  };

  const handleUpdateItemType = (id: string, newType: string) => {
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, imageType: newType } : it))
    );
  };

  const processSingleItem = async (item: UploadItem) => {
    if (!activeIncident) return;

    // Set uploading state
    setItems((prev) =>
      prev.map((it) => (it.id === item.id ? { ...it, status: 'UPLOADING', error: undefined } : it))
    );

    try {
      const formData = new FormData();
      formData.append('file', item.file);
      formData.append('incident_id', activeIncident.id);
      formData.append('image_type', item.imageType);
      if (amId) formData.append('am_id', amId);
      if (pmId) formData.append('pm_id', pmId);

      // 1. Upload to server
      const imageRecord = await api.uploadImage(formData);

      // 2. Set analyzing state
      setItems((prev) =>
        prev.map((it) => (it.id === item.id ? { ...it, status: 'ANALYZING' } : it))
      );

      // 3. Trigger Gemini Cloud Multimodal Extraction
      await api.analyzeImage(imageRecord.id);
      const fullRecord = await api.getImageAnalysis(imageRecord.id);

      // 4. Set done state
      setItems((prev) =>
        prev.map((it) =>
          it.id === item.id
            ? { ...it, status: 'DONE', imageEvidence: fullRecord }
            : it
        )
      );

      if (onEvidenceApproved) {
        onEvidenceApproved(fullRecord);
      }
    } catch (err: any) {
      setItems((prev) =>
        prev.map((it) =>
          it.id === item.id
            ? { ...it, status: 'ERROR', error: err.message || 'Analysis failed' }
            : it
        )
      );
    }
  };

  const handleProcessAll = async () => {
    if (!activeIncident) return;
    setIsProcessingAll(true);
    setErrorMsg(null);

    const queuedItems = items.filter((it) => it.status === 'QUEUED' || it.status === 'ERROR');

    // Run parallel analysis across all queued images
    await Promise.all(queuedItems.map((item) => processSingleItem(item)));

    setIsProcessingAll(false);
  };

  const handleClearAll = () => {
    items.forEach((it) => {
      if (it.previewUrl) URL.revokeObjectURL(it.previewUrl);
    });
    setItems([]);
    setErrorMsg(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const queuedCount = items.filter((it) => it.status === 'QUEUED').length;
  const analyzingCount = items.filter((it) => it.status === 'ANALYZING' || it.status === 'UPLOADING').length;
  const completedCount = items.filter((it) => it.status === 'DONE').length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-indigo-500 to-sky-600 flex items-center justify-center">
            <ImageIcon className="h-4 w-4 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                {recordType} Multimodal Photo Evidence
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-bold">
                Parallel Gemini 2.5 Flash
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Multi-image batch upload & simultaneous cloud AI visual extraction
            </p>
          </div>
        </div>

        {items.length > 0 && (
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[11px]">
              {items.length} Photos ({completedCount} Extracted)
            </span>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Drag & Drop Multi-file Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2.5 ${
          dragActive
            ? 'border-sky-400 bg-sky-500/10'
            : 'border-slate-700 bg-slate-950 hover:border-slate-600 hover:bg-slate-950/80'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.webp"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              addFiles(e.target.files);
            }
          }}
        />

        <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center text-sky-400 border border-slate-700 shadow-md">
          <Upload className="h-5 w-5" />
        </div>

        <div>
          <p className="text-xs font-semibold text-slate-200">
            Drag multiple photos here <span className="text-slate-400">OR</span>{' '}
            <span className="text-sky-400 underline font-bold">Browse Multi-Files</span>
          </p>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Select multiple JPG, JPEG, PNG, WEBP files · Up to 10 MB per image
          </p>
        </div>
      </div>

      {/* Multi-Image Queue Grid */}
      {items.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="h-4 w-4 text-sky-400" />
              <span>Upload Queue ({items.length})</span>
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 text-xs font-semibold transition"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Add More</span>
              </button>

              <button
                type="button"
                disabled={isProcessingAll}
                onClick={handleClearAll}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700 text-xs transition"
              >
                Clear All
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[380px] overflow-y-auto pr-1">
            {items.map((item) => {
              const obs: any = item.imageEvidence?.extraction_json?.observations || {};
              const clothingCount = obs.clothing?.length || 0;
              const jewelleryCount = obs.jewellery?.length || 0;
              const tattooCount = obs.tattoos?.length || 0;
              const scarCount = (obs.scars_or_marks?.length || 0);

              return (
                <div
                  key={item.id}
                  className="bg-slate-950 rounded-xl p-3 border border-slate-800 flex items-start gap-3 relative group hover:border-slate-700 transition"
                >
                  {/* Thumbnail Preview */}
                  <div className="h-20 w-20 rounded-lg overflow-hidden bg-slate-900 border border-slate-800 flex-shrink-0 flex items-center justify-center">
                    <img
                      src={item.previewUrl}
                      alt={item.file.name}
                      className="h-full w-full object-contain"
                    />
                  </div>

                  {/* Details & Status */}
                  <div className="flex-1 min-w-0 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white truncate max-w-[140px]" title={item.file.name}>
                        {item.file.name}
                      </span>

                      {item.status === 'QUEUED' && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(item.id)}
                          className="text-slate-500 hover:text-rose-400 transition"
                          title="Remove from queue"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>

                    <div className="text-[10px] text-slate-400 font-mono">
                      {((item.file.size || 0) / 1024).toFixed(1)} KB
                    </div>

                    {/* Image Classification */}
                    {item.status === 'QUEUED' ? (
                      <select
                        value={item.imageType}
                        onChange={(e) => handleUpdateItemType(item.id, e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 font-mono"
                      >
                        {availableTypes.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="text-[10px] font-mono text-slate-400">
                        Type: <span className="text-slate-200 font-semibold">{item.imageType}</span>
                      </div>
                    )}

                    {/* Status Badge */}
                    <div className="pt-0.5">
                      {item.status === 'QUEUED' && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          Queued for Analysis
                        </span>
                      )}

                      {item.status === 'UPLOADING' && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse">
                          <RotateCw className="h-2.5 w-2.5 animate-spin" /> Uploading...
                        </span>
                      )}

                      {item.status === 'ANALYZING' && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 animate-pulse font-semibold">
                          <Sparkles className="h-2.5 w-2.5 animate-spin" /> Gemini 2.5 Flash Extracting...
                        </span>
                      )}

                      {item.status === 'DONE' && (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between gap-1">
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                              <CheckCircle2 className="h-2.5 w-2.5" /> Extracted
                            </span>

                            {item.imageEvidence && (
                              <button
                                type="button"
                                onClick={() => setActiveReviewImage(item.imageEvidence || null)}
                                className="inline-flex items-center gap-1 text-[10px] font-bold text-sky-400 hover:text-sky-300 hover:underline"
                              >
                                <Eye className="h-3 w-3" />
                                <span>Inspect</span>
                              </button>
                            )}
                          </div>

                          {/* Extracted Traits Summary */}
                          <div className="flex items-center gap-1 flex-wrap text-[9px] font-mono text-slate-300">
                            {clothingCount > 0 && <span className="px-1.5 py-0.5 rounded bg-slate-800">{clothingCount} cloth</span>}
                            {jewelleryCount > 0 && <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">{jewelleryCount} jewl</span>}
                            {tattooCount > 0 && <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">{tattooCount} tat</span>}
                            {scarCount > 0 && <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300">{scarCount} scar</span>}
                          </div>
                        </div>
                      )}

                      {item.status === 'ERROR' && (
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 truncate max-w-[120px]" title={item.error}>
                            {item.error || 'Failed'}
                          </span>
                          <button
                            type="button"
                            onClick={() => processSingleItem(item)}
                            className="text-[10px] text-sky-400 hover:underline"
                          >
                            Retry
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-800">
            <div className="text-xs text-slate-400 font-mono">
              {queuedCount > 0 && <span>{queuedCount} queued · </span>}
              {analyzingCount > 0 && <span className="text-sky-400 animate-pulse">{analyzingCount} analyzing in parallel... · </span>}
              {completedCount > 0 && <span className="text-emerald-400">{completedCount} completed</span>}
            </div>

            <button
              type="button"
              disabled={isProcessingAll || queuedCount === 0}
              onClick={handleProcessAll}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-sky-500/20 disabled:opacity-50 transition cursor-pointer"
            >
              {isProcessingAll ? (
                <>
                  <RotateCw className="h-4 w-4 animate-spin" />
                  <span>Analyzing {analyzingCount} Photos in Parallel...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Analyze {queuedCount > 0 ? `All (${queuedCount} Photos)` : 'Photos'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Review Modal for Individual Extracted Photo */}
      {activeReviewImage && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="max-w-4xl w-full">
            <ImageEvidenceReview
              image={activeReviewImage}
              amId={amId}
              pmId={pmId}
              incidentId={activeIncident?.id}
              recordType={recordType}
              onClose={() => setActiveReviewImage(null)}
              onReviewCompleted={(updated) => {
                setActiveReviewImage(null);
                setItems((prev) =>
                  prev.map((it) =>
                    it.imageEvidence?.id === updated.id
                      ? { ...it, imageEvidence: updated }
                      : it
                  )
                );
                if (onEvidenceApproved) onEvidenceApproved(updated);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
