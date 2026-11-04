import React, { useState, useEffect } from 'react';
import { Layers, Activity, BrainCircuit, CheckCircle2, ArrowRight } from 'lucide-react';
import { AnalysisResult, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { PhaseTimeline } from '../components/PhaseTimeline';
import { RealisticBatterVisualizer } from '../components/RealisticBatterVisualizer';

interface PhasesPageProps {
  sessionId: string | null;
  onSelectTab: (tab: NavTab) => void;
}

export const PhasesPage: React.FC<PhasesPageProps> = ({ sessionId, onSelectTab }) => {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedPhaseIdx, setSelectedPhaseIdx] = useState<number>(0);

  useEffect(() => {
    if (!sessionId) {
      api.listSessions(1).then((res) => {
        if (res.sessions.length > 0) {
          loadSession(res.sessions[0].session_id);
        } else {
          setLoading(false);
        }
      }).catch(() => setLoading(false));
      return;
    }
    loadSession(sessionId);
  }, [sessionId]);

  const loadSession = async (id: string) => {
    try {
      setLoading(true);
      const data = await api.getAnalysis(id);
      setAnalysis(data);
    } catch (err) {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center space-y-3">
        <Activity className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
        <h3 className="text-sm font-semibold text-white">Loading Batting Action Phases...</h3>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-4">
        <h3 className="text-sm font-bold text-white">No active session selected</h3>
        <button
          onClick={() => onSelectTab('dashboard')}
          className="px-4 py-2 rounded-lg bg-navy-800 text-xs text-white"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  const activePhase = analysis.phases[selectedPhaseIdx] || analysis.phases[0];
  const activeFrameData = analysis.time_series[activePhase?.key_frame || 0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-navy-800">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2">
            <span>Batting Action Phase Recognition</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Temporal Breakdown
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Automated stroke breakdown into 7 technical phases from stance through follow-through for {analysis.shot_type}
          </p>
        </div>

        <button
          onClick={() => onSelectTab('workspace')}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-medium border border-navy-700 transition-colors self-start"
        >
          <Layers className="w-4 h-4 text-brand-400" />
          <span>Technique Workspace</span>
        </button>
      </div>

      {/* Main Interactive Timeline */}
      <PhaseTimeline
        phases={analysis.phases}
        currentFrame={activePhase?.key_frame || 0}
        totalFrames={analysis.analyzed_frames}
        onSelectFrame={(f) => {
          const idx = analysis.phases.findIndex((p) => f >= p.start_frame && f <= p.end_frame);
          if (idx !== -1) setSelectedPhaseIdx(idx);
        }}
      />

      {/* Grid: Phase Cards Selector on Left, Selected Phase Deep Dive on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: List of All Recognized Phases */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Recognized Stroke Phases ({analysis.phases.length})
          </h3>

          <div className="space-y-2">
            {analysis.phases.map((phase, idx) => {
              const isSelected = selectedPhaseIdx === idx;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedPhaseIdx(idx)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'bg-navy-800 border-brand-500/50 shadow-md ring-1 ring-brand-500/30'
                      : 'bg-navy-900/60 border-navy-800 hover:bg-navy-850 hover:border-slate-600'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-white truncate">{phase.phase_name}</span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                      {phase.start_sec}s - {phase.end_sec}s • Keyframe: F{phase.key_frame}
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-navy-950 border border-navy-800 text-brand-400">
                      {(phase.confidence * 100).toFixed(0)}% Conf
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 2 Columns: Detailed Phase Breakdown & Kinematics */}
        {activePhase && (
          <div className="lg:col-span-2 space-y-6 bg-navy-900/80 p-6 rounded-2xl border border-navy-800">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] uppercase font-mono font-semibold text-brand-400 tracking-wider">
                  Phase Inspection
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight mt-0.5">
                  {activePhase.phase_name}
                </h2>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  {activePhase.description}
                </p>
              </div>

              <div className="text-right font-mono text-xs text-slate-400 bg-navy-950 px-3 py-2 rounded-xl border border-navy-800">
                <div>Duration: <strong className="text-white">{(activePhase.end_sec - activePhase.start_sec).toFixed(2)}s</strong></div>
                <div>Frames: <strong className="text-white">{activePhase.start_frame}</strong> to <strong className="text-white">{activePhase.end_frame}</strong></div>
              </div>
            </div>

            {/* Realistic Biomechanical Batter Model */}
            <div className="rounded-2xl overflow-hidden border border-[#303438] bg-[#0A0C0E] shadow-xl">
              <div className="px-4 py-2.5 bg-[#111315] border-b border-[#303438] flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#7FEA35] shadow-sm shadow-[#7FEA35]/50" />
                  <span className="text-xs font-bold uppercase tracking-wider text-[#F5F5F5]">
                    Biomechanical Form Analysis — {analysis.shot_type}
                  </span>
                </div>
                <span className="text-[11px] font-mono font-bold text-[#7FEA35]">
                  Phase {selectedPhaseIdx + 1}/7: {activePhase.phase_name}
                </span>
              </div>
              <RealisticBatterVisualizer
                shotName={analysis.shot_type}
                initialPhaseIndex={Math.min(selectedPhaseIdx, 6)}
                showControls={true}
                autoPlay={false}
                onPhaseChange={(idx) => {
                  if (idx !== selectedPhaseIdx && idx < analysis.phases.length) {
                    setSelectedPhaseIdx(idx);
                  }
                }}
              />
            </div>

            {/* Keyframe Pose Metrics */}
            {activeFrameData && (
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Keyframe {activePhase.key_frame} Kinematic Snapshot
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                  <div className="bg-navy-950 p-3 rounded-xl border border-navy-800">
                    <span className="text-slate-400 text-[10px]">Lead Knee</span>
                    <div className="text-base font-bold text-white mt-1">
                      {activeFrameData.lead_knee_angle ?? '--'}°
                    </div>
                  </div>

                  <div className="bg-navy-950 p-3 rounded-xl border border-navy-800">
                    <span className="text-slate-400 text-[10px]">Rear Knee</span>
                    <div className="text-base font-bold text-white mt-1">
                      {activeFrameData.rear_knee_angle ?? '--'}°
                    </div>
                  </div>

                  <div className="bg-navy-950 p-3 rounded-xl border border-navy-800">
                    <span className="text-slate-400 text-[10px]">Torso Lean</span>
                    <div className="text-base font-bold text-white mt-1">
                      {activeFrameData.torso_inclination ?? '--'}°
                    </div>
                  </div>

                  <div className="bg-navy-950 p-3 rounded-xl border border-navy-800">
                    <span className="text-slate-400 text-[10px]">Stance Width</span>
                    <div className="text-base font-bold text-white mt-1">
                      {activeFrameData.stance_width_norm ? `${activeFrameData.stance_width_norm}x` : '--'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Movement Timing & Coaching Note */}
            <div className="p-4 rounded-xl bg-navy-950 border border-navy-800 text-xs text-slate-400 space-y-1.5">
              <div className="flex items-center space-x-2 text-white font-semibold">
                <BrainCircuit className="w-4 h-4 text-emerald-400" />
                <span>Stroke Timing & Movement Sequencing</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                CricketIQ analyzes movement momentum and directional velocity across each frame to identify your exact preparation, stride commitment, contact window, and follow-through balance.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
