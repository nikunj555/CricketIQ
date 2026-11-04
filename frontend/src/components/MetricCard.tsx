import React from 'react';
import { Info } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number | null | undefined;
  unit?: string;
  benchmark?: string;
  status?: 'optimal' | 'warning' | 'info' | 'neutral';
  description?: string;
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  benchmark,
  status = 'neutral',
  description,
  icon,
}) => {
  const statusStyles = {
    optimal: 'border-emerald-500/30 bg-emerald-950/10 text-emerald-400',
    warning: 'border-amber-500/30 bg-amber-950/10 text-amber-400',
    info: 'border-sky-500/30 bg-sky-950/10 text-sky-400',
    neutral: 'border-navy-800 bg-navy-900/60 text-slate-300',
  };

  const statusBadge = {
    optimal: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    info: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
    neutral: 'bg-slate-800/60 text-slate-400 border border-slate-700/50',
  };

  const displayVal = value !== null && value !== undefined ? value : 'Unavailable';

  return (
    <div className={`p-4 rounded-xl border ${statusStyles[status]} transition-all duration-200 hover:border-slate-600 shadow-sm relative group`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2">
          {icon && <div className="text-slate-400 group-hover:text-brand-400 transition-colors">{icon}</div>}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">{title}</h3>
        </div>
        {description && (
          <div className="relative cursor-help" title={description}>
            <Info className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300" />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline space-x-1.5">
        <span className="text-2xl font-bold font-mono tracking-tight text-white">{displayVal}</span>
        {unit && value !== null && value !== undefined && (
          <span className="text-xs font-mono text-slate-400">{unit}</span>
        )}
      </div>

      {benchmark && (
        <div className="mt-2 flex items-center justify-between text-[11px] pt-2 border-t border-navy-800/80">
          <span className="text-slate-400">Target Range</span>
          <span className={`px-1.5 py-0.5 rounded font-mono ${statusBadge[status]}`}>{benchmark}</span>
        </div>
      )}
    </div>
  );
};
