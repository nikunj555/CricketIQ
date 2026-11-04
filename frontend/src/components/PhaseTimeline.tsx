import React from 'react';
import { PhaseSegment } from '../types/cricket';

interface PhaseTimelineProps {
  phases: PhaseSegment[];
  currentFrame?: number;
  totalFrames: number;
  onSelectFrame?: (frame: number) => void;
}

const PHASE_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  'Stance / Setup': {
    bg: 'bg-slate-700/60',
    border: 'border-slate-500',
    text: 'text-slate-300',
    badge: 'bg-slate-800 text-slate-300 border-slate-600',
  },
  'Backswing / Preparation': {
    bg: 'bg-indigo-900/60',
    border: 'border-indigo-500',
    text: 'text-indigo-300',
    badge: 'bg-indigo-950 text-indigo-300 border-indigo-700',
  },
  'Stride / Weight Transfer': {
    bg: 'bg-blue-900/60',
    border: 'border-blue-500',
    text: 'text-blue-300',
    badge: 'bg-blue-950 text-blue-300 border-blue-700',
  },
  'Downswing / Execution': {
    bg: 'bg-cyan-900/60',
    border: 'border-cyan-500',
    text: 'text-cyan-300',
    badge: 'bg-cyan-950 text-cyan-300 border-cyan-700',
  },
  'Impact / Contact Window': {
    bg: 'bg-amber-600/70',
    border: 'border-amber-400',
    text: 'text-amber-200',
    badge: 'bg-amber-950 text-amber-300 border-amber-600',
  },
  'Follow-through': {
    bg: 'bg-emerald-900/60',
    border: 'border-emerald-500',
    text: 'text-emerald-300',
    badge: 'bg-emerald-950 text-emerald-300 border-emerald-700',
  },
  'Recovery': {
    bg: 'bg-teal-900/60',
    border: 'border-teal-500',
    text: 'text-teal-300',
    badge: 'bg-teal-950 text-teal-300 border-teal-700',
  },
};

export const PhaseTimeline: React.FC<PhaseTimelineProps> = ({
  phases,
  currentFrame = 0,
  totalFrames,
  onSelectFrame,
}) => {
  if (!phases || phases.length === 0 || totalFrames <= 0) {
    return (
      <div className="p-4 bg-navy-900/60 rounded-xl border border-navy-800 text-slate-400 text-xs">
        No phase timeline available for this video session.
      </div>
    );
  }

  const cursorPercent = Math.min(100, Math.max(0, (currentFrame / Math.max(1, totalFrames - 1)) * 100));

  return (
    <div className="bg-navy-900/80 rounded-xl border border-navy-800 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-400 animate-pulse" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Batting Action Phase Timeline
          </h4>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          Frame: <strong className="text-white">{currentFrame}</strong> / {totalFrames}
        </span>
      </div>

      {/* Segmented Timeline Bar */}
      <div className="relative h-9 w-full bg-navy-950 rounded-lg overflow-hidden border border-navy-800 flex shadow-inner">
        {phases.map((seg, idx) => {
          const segDuration = Math.max(1, seg.end_frame - seg.start_frame + 1);
          const widthPct = (segDuration / totalFrames) * 100;
          const styling = PHASE_COLORS[seg.phase_name] || {
            bg: 'bg-navy-800',
            border: 'border-slate-600',
            text: 'text-slate-300',
            badge: 'bg-slate-800',
          };

          return (
            <button
              key={idx}
              onClick={() => onSelectFrame && onSelectFrame(seg.key_frame)}
              style={{ width: `${widthPct}%` }}
              title={`${seg.phase_name} (${seg.start_sec}s - ${seg.end_sec}s | Conf: ${(seg.confidence * 100).toFixed(0)}%)`}
              className={`h-full ${styling.bg} border-r border-navy-900/80 relative group flex items-center justify-center px-1 text-center transition-all hover:brightness-125 focus:outline-none`}
            >
              <span className={`text-[10px] font-medium font-sans truncate ${styling.text}`}>
                {seg.phase_name.split('/')[0].trim()}
              </span>
            </button>
          );
        })}

        {/* Video Scrubber Cursor Line */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg pointer-events-none transition-all duration-75 z-20"
          style={{ left: `${cursorPercent}%` }}
        >
          <div className="w-2.5 h-2.5 bg-white rounded-full -ml-1 -top-1 absolute shadow-md" />
        </div>
      </div>

      {/* Phase Legend Pills */}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {phases.map((p, idx) => {
          const styling = PHASE_COLORS[p.phase_name] || {
            badge: 'bg-slate-800 text-slate-300 border-slate-700',
          };
          const isCurrent = currentFrame >= p.start_frame && currentFrame <= p.end_frame;
          return (
            <button
              key={idx}
              onClick={() => onSelectFrame && onSelectFrame(p.key_frame)}
              className={`text-[11px] px-2 py-1 rounded-md border font-mono transition-all flex items-center space-x-1.5 ${
                styling.badge
              } ${isCurrent ? 'ring-2 ring-white/70 font-semibold' : 'opacity-85 hover:opacity-100'}`}
            >
              <span>{p.phase_name}</span>
              <span className="opacity-60 text-[10px]">({p.start_sec}s)</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
