import React from 'react';
import { CoachingObservation } from '../types/cricket';
import { CheckCircle2, AlertTriangle, HelpCircle, Dumbbell, ShieldAlert } from 'lucide-react';

interface CoachingFeedbackListProps {
  observations: CoachingObservation[];
  shotType?: string;
}

export const CoachingFeedbackList: React.FC<CoachingFeedbackListProps> = ({
  observations,
  shotType = 'Cover Drive',
}) => {
  if (!observations || observations.length === 0) {
    return (
      <div className="bg-navy-900/60 rounded-xl border border-navy-800 p-6 text-center">
        <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-white">Consistent Execution</h4>
        <p className="text-xs text-slate-400 mt-1">
          Extracted kinematic features aligned within expected coaching tolerance bands.
        </p>
      </div>
    );
  }

  const severityMeta = {
    strength: {
      badge: 'bg-emerald-950 text-emerald-300 border-emerald-800',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      border: 'border-emerald-500/30',
      tag: 'Technical Strength',
    },
    review: {
      badge: 'bg-amber-950 text-amber-300 border-amber-800',
      icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
      border: 'border-amber-500/40',
      tag: 'Area to Review',
    },
    consideration: {
      badge: 'bg-sky-950 text-sky-300 border-sky-800',
      icon: <HelpCircle className="w-4 h-4 text-sky-400" />,
      border: 'border-sky-500/30',
      tag: 'Technique Note',
    },
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <span>Explainable Coaching Observations</span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              Grounded Evidence
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Observations derived directly from measured joint angles and temporal phase landmarks for {shotType}.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {observations.map((obs) => {
          const meta = severityMeta[obs.severity] || severityMeta.consideration;

          return (
            <div
              key={obs.id}
              className={`bg-navy-900/90 rounded-xl border ${meta.border} p-5 space-y-3.5 shadow-sm hover:border-slate-500 transition-all`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center space-x-2.5">
                  <div className="p-1.5 rounded-lg bg-navy-950 border border-navy-800">
                    {meta.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white tracking-tight">{obs.title}</h4>
                    <span className="text-[11px] font-mono text-slate-400">
                      Category: {obs.category} • Phase: {obs.phase}
                      {obs.timestamp_sec != null && ` • @${obs.timestamp_sec.toFixed(2)}s`}
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {obs.measurement_provenance && (
                    <span
                      className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
                        obs.measurement_provenance === 'MEASURED'
                          ? 'bg-blue-950 text-blue-300 border-blue-800'
                          : 'bg-amber-950 text-amber-300 border-amber-800'
                      }`}
                      title={
                        obs.measurement_provenance === 'MEASURED'
                          ? 'Extracted directly from MediaPipe 2D joint landmarks'
                          : 'Estimated via proxy heuristics or linear edge tracking'
                      }
                    >
                      {obs.measurement_provenance}
                    </span>
                  )}
                  <span className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded border ${meta.badge}`}>
                    {meta.tag}
                  </span>
                </div>
              </div>

              {/* Measured Evidence Box */}
              <div className="bg-navy-950/80 rounded-lg p-3 border border-navy-800 text-xs space-y-1">
                <div className="flex items-center justify-between text-slate-300 font-mono">
                  <span>Measured Evidence:</span>
                  <span className="text-white font-semibold">{obs.measurement}</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  Observation: <strong className="text-slate-200">{obs.observed_value}</strong>
                  {obs.reference_benchmark && ` | ${obs.reference_benchmark}`}
                </p>
              </div>

              {/* Why it matters */}
              <div className="text-xs text-slate-300">
                <span className="text-brand-400 font-medium">Why it matters: </span>
                {obs.why_it_matters}
              </div>

              {/* Practical Drill */}
              <div className="flex items-start space-x-2 text-xs bg-navy-800/40 p-2.5 rounded-lg border border-navy-800 text-slate-200">
                <Dumbbell className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-brand-400">Recommended Practice Drill: </strong>
                  <span>{obs.practical_drill}</span>
                </div>
              </div>

              {/* Uncertainty & Limitation */}
              <div className="flex items-start space-x-2 text-[11px] text-slate-500 pt-1">
                <ShieldAlert className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                <span>
                  <strong>Limitation: </strong>
                  {obs.limitation}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
