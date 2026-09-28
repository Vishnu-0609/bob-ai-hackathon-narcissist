import React from 'react';

interface EvidenceBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({ status, size = 'sm' }) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-400 border-slate-700';
  let label = status;

  if (norm === 'MATCH') {
    colorClasses = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    label = 'MATCH';
  } else if (norm === 'MISMATCH') {
    colorClasses = 'bg-rose-500/15 text-rose-400 border-rose-500/30';
    label = 'MISMATCH';
  } else if (norm === 'UNKNOWN') {
    colorClasses = 'bg-amber-500/15 text-amber-400 border-amber-500/30';
    label = 'UNKNOWN';
  } else if (norm === 'NOT_AVAILABLE') {
    colorClasses = 'bg-slate-800/80 text-slate-500 border-slate-700';
    label = 'NOT AVAILABLE';
  } else if (norm === 'STRONG_CANDIDATE') {
    colorClasses = 'bg-sky-500/20 text-sky-300 border-sky-500/40';
    label = 'STRONG CANDIDATE';
  } else if (norm === 'MODERATE_CANDIDATE') {
    colorClasses = 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
    label = 'MODERATE CANDIDATE';
  } else if (norm === 'CONTRADICTION_REVIEW' || norm === 'STRONG_CONTRADICTION') {
    colorClasses = 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
    label = 'CONTRADICTION REVIEW';
  } else if (norm === 'CONFIRMED_BY_FORENSIC_TEAM') {
    colorClasses = 'bg-emerald-600/25 text-emerald-300 border-emerald-500/50 font-semibold';
    label = 'CONFIRMED BY REVIEW';
  } else if (norm === 'REJECTED') {
    colorClasses = 'bg-slate-800 text-slate-400 border-slate-700 line-through';
    label = 'REJECTED';
  } else if (norm === 'NEEDS_REVIEW') {
    colorClasses = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    label = 'NEEDS REVIEW';
  }

  const paddingClass = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-3 py-1 text-xs';

  return (
    <span className={`inline-flex items-center rounded-md font-mono border ${paddingClass} ${colorClasses}`}>
      {label}
    </span>
  );
};
