import React, { useState, useEffect, useMemo } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  X,
  Upload,
  Video,
  ShieldCheck,
  Layers,
  Sparkles,
  Compass,
  Crosshair,
  Dumbbell
} from 'lucide-react';
import { CricketShot, ReferenceDetail, LearningVideo } from '../types/cricket';
import { api } from '../services/api';
import { getShotAnimation, ShotAnimationDefinition } from '../data/shotAnimations';
import { LearnShotCard } from './LearnShotCard';

interface ShotPreviewModalProps {
  shot: CricketShot;
  onClose: () => void;
  onStartPractice: (shot: CricketShot) => void;
  onUploadAttempt: (shot: CricketShot) => void;
}

const PHASE_KEYS = ['stance', 'backlift', 'stride', 'downswing', 'impact', 'follow_through', 'recovery'];

export const ShotPreviewModal: React.FC<ShotPreviewModalProps> = ({
  shot,
  onClose,
  onStartPractice,
  onUploadAttempt,
}) => {
  const [refDetail, setRefDetail] = useState<ReferenceDetail | null>(null);
  const [learningVideos, setLearningVideos] = useState<LearningVideo[]>([]);
  const [activePhaseIndex, setActivePhaseIndex] = useState<number>(0);

  // Authoritative shot animation cues
  const shotAnimation: ShotAnimationDefinition | null = useMemo(() => {
    return getShotAnimation(shot.name || shot.id);
  }, [shot.id, shot.name]);

  useEffect(() => {
    loadReference();
    api.getShotVideos(shot.name || shot.id)
      .then((vids) => setLearningVideos(vids || []))
      .catch(() => setLearningVideos([]));
  }, [shot.id, shot.name]);

  const loadReference = async () => {
    try {
      const data = await api.getShotReference(shot.id);
      setRefDetail(data);
    } catch {
      // Keep graceful fallback for reference text
    }
  };

  const phases = useMemo(() => {
    return PHASE_KEYS.map((pk) => {
      const kf = shotAnimation?.phases?.[pk];
      return {
        phase_name: kf?.label || pk.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        frame_window: pk === 'stance' ? '0% - 15%' : pk === 'backlift' ? '15% - 35%' : pk === 'stride' ? '35% - 50%' : pk === 'downswing' ? '50% - 65%' : pk === 'impact' ? '65% - 75%' : pk === 'follow_through' ? '75% - 90%' : '90% - 100%',
        description: kf?.cue || `Textbook biomechanics for ${shot.name}`,
        lead_knee_target: `${kf?.leadLeg?.kneeAngleDeg || 125}°`,
        key_cue: kf?.cue || 'Hold shape and balance'
      };
    });
  }, [shotAnimation, shot.name]);

  const currentPhase = phases[activePhaseIndex] || phases[0];
  const activePhaseKey = PHASE_KEYS[activePhaseIndex] || 'stance';
  const activeKeyframeData = shotAnimation?.phases?.[activePhaseKey];

  return (
    <div className="fixed inset-0 z-50 bg-[#050505]/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 animate-in fade-in duration-150 overflow-y-auto">
      <div className="bg-[#181B1D] border border-[#303438] rounded-2xl max-w-4xl w-full max-h-[92vh] overflow-y-auto shadow-2xl p-5 sm:p-7 space-y-6">
        {/* Modal Header */}
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-[#303438]">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30">
                {shot.category}
              </span>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-[#111315] text-[#F5F5F5] border border-[#303438]">
                {shot.difficulty}
              </span>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-[#111315] text-[#7FEA35] border border-[#303438] flex items-center space-x-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#7FEA35]" />
                <span>Biomechanical reference: authored baseline (tunable)</span>
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#F5F5F5] tracking-tight">
              {shot.name}
            </h2>
            {shot.technique_notes && (
              <div className="text-xs text-[#7FEA35] font-medium flex items-center gap-1.5 pt-0.5">
                <Compass className="w-3.5 h-3.5 shrink-0" />
                <span>Intent: {shot.technique_notes}</span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-[#111315] border border-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#303438] transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Ball Trajectory & Shot Profile Info Banner */}
        <div className="p-3.5 rounded-xl bg-[#111315] border border-[#303438] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0 animate-ping" />
            <Crosshair className="w-4 h-4 text-rose-400 shrink-0" />
            <div>
              <span className="text-[#A5A9AD]">Delivery Line & Length: </span>
              <strong className="text-[#F5F5F5]">
                {shotAnimation ? `${shotAnimation.ballTrajectory.line} • ${shotAnimation.ballTrajectory.length}` : 'Good Length • Off Stump'}
              </strong>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-[#A5A9AD]">Bat Swing Plane:</span>
            <span className="font-mono text-[#7FEA35] font-semibold uppercase px-2 py-0.5 rounded bg-[#181B1D] border border-[#303438]">
              {shotAnimation?.swingPlane ? shotAnimation.swingPlane.replace('_', ' ') : 'Vertical'}
            </span>
          </div>
        </div>

        {/* Learn this shot Link Card */}
        {learningVideos.length > 0 && (
          <LearnShotCard videos={learningVideos} />
        )}

        {/* Shot Overview Description */}
        <p className="text-xs text-[#A5A9AD] leading-relaxed">
          {refDetail?.description || shot.description}
        </p>

        {/* 7-Phase Movement Breakdown Timeline */}
        <div className="space-y-3 pt-2 border-t border-[#303438]">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider font-mono flex items-center space-x-2">
              <Layers className="w-4 h-4 text-[#7FEA35]" />
              <span>7 Movement Phases Breakdown</span>
            </h4>
            <span className="text-[11px] font-mono text-[#A5A9AD]">
              Click phase to inspect technique cues
            </span>
          </div>

          {/* Phase Segment Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-1.5">
            {phases.map((p, idx) => {
              const isSelected = activePhaseIndex === idx;
              return (
                <button
                  key={p.phase_name}
                  onClick={() => setActivePhaseIndex(idx)}
                  className={`p-2 rounded-xl text-left border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#7FEA35]/15 border-[#7FEA35] text-[#7FEA35] shadow-sm'
                      : 'bg-[#111315] border-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D]'
                  }`}
                >
                  <div className="text-[10px] font-mono text-[#A5A9AD] uppercase">{p.frame_window}</div>
                  <div className={`text-xs font-bold truncate ${isSelected ? 'text-[#7FEA35]' : 'text-[#F5F5F5]'}`}>
                    {p.phase_name}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Phase Deep Dive Card */}
          <div className="p-4 rounded-xl bg-[#111315] border border-[#303438] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-[#7FEA35] uppercase font-mono">
                  Phase {activePhaseIndex + 1}: {currentPhase.phase_name}
                </span>
                <span className="text-[10px] font-mono text-[#A5A9AD] px-2 py-0.5 rounded bg-[#181B1D]">
                  {currentPhase.frame_window}
                </span>
              </div>
              <span className="text-xs font-mono text-[#F5F5F5]">
                Target Lead Knee: <strong className="text-[#7FEA35]">{currentPhase.lead_knee_target}</strong>
              </span>
            </div>
            <p className="text-xs text-[#F5F5F5] leading-relaxed">
              {currentPhase.description}
            </p>
            <div className="text-[11px] text-[#A5A9AD] flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#7FEA35]" />
              <span><strong>Key Coaching Cue: </strong>{activeKeyframeData?.cue || currentPhase.key_cue}</span>
            </div>

            {/* Phase Checkpoints */}
            {activeKeyframeData?.techniquePoints && (
              <div className="pt-2 border-t border-[#303438]/50 space-y-1.5">
                <span className="text-[10px] font-mono font-bold text-[#7FEA35] uppercase tracking-wider">
                  Phase Checkpoints:
                </span>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs text-[#A5A9AD]">
                  {activeKeyframeData.techniquePoints.map((pt, i) => (
                    <li key={i} className="flex items-start space-x-1.5">
                      <span className="text-[#7FEA35] font-bold">•</span>
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Biomechanical Stance & Footwork Breakdown */}
        {refDetail && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-[#303438]">
            <div className="p-3.5 rounded-xl bg-[#111315] border border-[#303438] space-y-1.5">
              <div className="text-[11px] font-mono font-bold text-[#7FEA35] uppercase">
                1. Recommended Stance
              </div>
              <p className="text-xs text-[#A5A9AD] leading-relaxed">
                {refDetail.stance_setup}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-[#111315] border border-[#303438] space-y-1.5">
              <div className="text-[11px] font-mono font-bold text-[#7FEA35] uppercase">
                2. Footwork & Weight Transfer
              </div>
              <p className="text-xs text-[#A5A9AD] leading-relaxed">
                {refDetail.footwork_weight_transfer}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-[#111315] border border-[#303438] space-y-1.5">
              <div className="text-[11px] font-mono font-bold text-[#7FEA35] uppercase">
                3. Body Positioning & Angle
              </div>
              <p className="text-xs text-[#A5A9AD] leading-relaxed">
                {refDetail.body_positioning}
              </p>
            </div>
          </div>
        )}

        {/* Technique Points, Common Mistakes & Practice Drills */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-[#303438]">
          {/* Key Checkpoints */}
          <div className="p-4 rounded-xl bg-[#111315] border border-[#303438] space-y-2.5">
            <h4 className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider font-mono flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-[#7FEA35]" />
              <span>Key Checkpoints</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-[#A5A9AD]">
              {(refDetail?.technique_points?.length ? refDetail.technique_points : activeKeyframeData?.techniquePoints || []).map((pt, i) => (
                <li key={i} className="flex items-start space-x-2">
                  <span className="text-[#7FEA35] font-bold">•</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Common Mistakes */}
          <div className="p-4 rounded-xl bg-[#111315] border border-rose-900/40 space-y-2.5">
            <h4 className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider font-mono flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>Common Mistakes</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-[#A5A9AD]">
              {(shotAnimation?.commonMistakes || []).map((m, i) => (
                <li key={i} className="flex items-start space-x-2">
                  <span className="text-rose-400 font-bold">•</span>
                  <span>{m}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Recommended Technical Drills */}
          <div className="p-4 rounded-xl bg-[#111315] border border-[#303438] space-y-2.5">
            <h4 className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider font-mono flex items-center space-x-2">
              <Dumbbell className="w-4 h-4 text-[#38BDF8]" />
              <span>Recommended Drills</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-[#A5A9AD]">
              {(shotAnimation?.drills || []).map((drill, i) => (
                <li key={i} className="flex items-start space-x-2">
                  <span className="text-[#38BDF8] font-bold">{i + 1}.</span>
                  <span>{drill}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-[#303438]">
          <button
            onClick={() => {
              onUploadAttempt(shot);
              onClose();
            }}
            className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-[#111315] hover:bg-[#303438] text-[#F5F5F5] text-xs font-bold border border-[#303438] hover:border-[#7FEA35]/40 transition-colors cursor-pointer flex items-center justify-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>Upload Video Attempt</span>
          </button>
          <button
            onClick={() => {
              onStartPractice(shot);
              onClose();
            }}
            className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] text-xs font-extrabold transition-all cursor-pointer flex items-center justify-center space-x-2 shadow-lg shadow-[#7FEA35]/20"
          >
            <Video className="w-4 h-4 fill-current" />
            <span>Practice in Live Coach</span>
          </button>
        </div>
      </div>
    </div>
  );
};
