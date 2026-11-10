import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Dumbbell,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Target,
  Award,
  Info,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Eye,
  Globe
} from 'lucide-react';
import { CoachingObservation, IssueCard, PlainTopSummary } from '../types/cricket';

interface CoachingFeedbackListProps {
  observations?: CoachingObservation[];
  shotType?: string;
  plainSummary?: PlainTopSummary | null;
  issueCards?: IssueCard[];
  coachingPaused?: boolean;
  pauseReason?: string | null;
  onSelectCandidateShot?: (shot: string) => void;
  topCandidates?: Array<{ shot: string; pct: number }>;
  onSeekToFrame?: (frameIndex: number) => void;
  onLanguageChange?: (lang: string) => void;
  currentLang?: string;
  techniqueScore?: number | null;
}

export const CoachingFeedbackList: React.FC<CoachingFeedbackListProps> = ({
  observations = [],
  shotType = 'Cover Drive',
  plainSummary,
  issueCards = [],
  coachingPaused = false,
  pauseReason,
  onSelectCandidateShot,
  topCandidates = [],
  onSeekToFrame,
  onLanguageChange,
  currentLang = 'en',
  techniqueScore = null
}) => {
  const [expandedProofs, setExpandedProofs] = useState<Record<string, boolean>>({});
  const [selectedProofModalCard, setSelectedProofModalCard] = useState<IssueCard | null>(null);
  const [detailMode, setDetailMode] = useState<'plain' | 'technical'>('plain');

  const toggleProof = (id: string) => {
    setExpandedProofs((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // If coaching is paused due to uncertain shot classification (Mutual Protection)
  if (coachingPaused) {
    return (
      <div className="bg-[#111315] rounded-2xl border-2 border-amber-500/40 p-6 space-y-4 shadow-xl">
        <div className="flex items-start space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white tracking-tight">
              Technique Coaching Paused — Confirm Your Shot
            </h3>
            <p className="text-xs text-[#A5A9AD] leading-relaxed">
              {pauseReason ||
                "We aren't sure which shot you played. Coaching on the wrong shot gives misleading advice. Please confirm your shot to see technique feedback."}
            </p>
          </div>
        </div>

        {topCandidates.length > 0 && (
          <div className="pt-2">
            <div className="text-xs font-semibold text-slate-300 mb-2">Did you play one of these?</div>
            <div className="flex flex-wrap gap-2">
              {topCandidates.map((cand) => (
                <button
                  key={cand.shot}
                  onClick={() => onSelectCandidateShot?.(cand.shot)}
                  className="px-4 py-2 rounded-xl bg-[#181B1D] hover:bg-[#7FEA35] hover:text-[#050505] text-[#F5F5F5] border border-[#303438] hover:border-[#7FEA35] transition-all text-xs font-bold flex items-center space-x-2 cursor-pointer shadow-sm"
                >
                  <span>{cand.shot}</span>
                  <span className="text-[10px] opacity-75 font-mono">({cand.pct}%)</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  const displayCards: IssueCard[] = issueCards.slice(0, 3);

  // Resolve score label
  const scoreNum = plainSummary?.technique_score ?? techniqueScore;
  const scoreBadgeLabel =
    plainSummary?.score_label ??
    (scoreNum == null ? 'Not available' : scoreNum >= 85 ? 'Excellent' : scoreNum >= 70 ? 'Good' : scoreNum >= 50 ? 'Getting there' : 'Needs work');

  const oneFocus = plainSummary?.one_focus_for_next_10_balls ?? (
    displayCards.length > 0
      ? {
          title: `Focus on your ${displayCards[0].target_body_part}`,
          cue: displayCards[0].how_to_fix,
          target_body_part: displayCards[0].target_body_part,
          source_issue_id: displayCards[0].id
        }
      : null
  );

  const strengths = plainSummary?.what_you_did_well ?? observations
    .filter((obs) => obs.severity === 'strength' && obs.measurement_provenance !== 'UNAVAILABLE')
    .map((obs) => ({
      title: obs.title,
      sentence: `${obs.measurement} during ${obs.phase}${obs.timestamp_sec != null ? ` at ${obs.timestamp_sec.toFixed(2)}s` : ''}. ${obs.observed_value}`
    }));

  const unmeasurable = plainSummary?.unmeasurable_notices ?? [];

  return (
    <div className="space-y-6">
      {/* Coaching Controls Bar: Language & Detail Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-[#303438]/80">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-[#7FEA35]/10 text-[#7FEA35] border border-[#7FEA35]/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">Coaching Feedback</h3>
            <p className="text-[11px] text-[#A5A9AD]">Plain English with technical proof one tap away</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Detail Mode Toggle */}
          <div className="inline-flex rounded-lg bg-[#181B1D] p-0.5 border border-[#303438]">
            <button
              onClick={() => setDetailMode('plain')}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-colors ${
                detailMode === 'plain'
                  ? 'bg-[#7FEA35] text-[#050505] font-bold shadow-xs'
                  : 'text-[#A5A9AD] hover:text-white'
              }`}
            >
              Simple
            </button>
            <button
              onClick={() => setDetailMode('technical')}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-colors ${
                detailMode === 'technical'
                  ? 'bg-[#7FEA35] text-[#050505] font-bold shadow-xs'
                  : 'text-[#A5A9AD] hover:text-white'
              }`}
            >
              Detailed
            </button>
          </div>

          {/* Multi-language toggle */}
          {onLanguageChange && (
            <div className="inline-flex rounded-lg bg-[#181B1D] p-0.5 border border-[#303438]">
              <button
                onClick={() => onLanguageChange('en')}
                className={`flex items-center space-x-1 px-2 py-1 text-[11px] font-semibold rounded-md transition-colors ${
                  currentLang === 'en'
                    ? 'bg-[#303438] text-white font-bold'
                    : 'text-[#A5A9AD] hover:text-white'
                }`}
              >
                <span>English</span>
              </button>
              <button
                onClick={() => onLanguageChange('hi')}
                className={`flex items-center space-x-1 px-2 py-1 text-[11px] font-semibold rounded-md transition-colors ${
                  currentLang === 'hi'
                    ? 'bg-[#303438] text-white font-bold'
                    : 'text-[#A5A9AD] hover:text-white'
                }`}
                title="Hindi / Hinglish"
              >
                <Globe className="w-3 h-3" />
                <span>हिंदी</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* B1: Top Summary Box */}
      <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4 shadow-md">
        {/* Top Verdict Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#303438]/60">
          <div className="space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#7FEA35] font-bold">
              Coach's Verdict
            </span>
            <h4 className="text-base font-bold text-white tracking-tight">
              {plainSummary?.one_line_verdict || 'Clip-specific feedback is limited to the measured observations below.'}
            </h4>
          </div>

          {/* Technique Score Badge */}
          <div className="flex items-center space-x-2 shrink-0 bg-[#181B1D] px-3 py-1.5 rounded-xl border border-[#303438]">
            <span className="text-[11px] text-[#A5A9AD] font-medium">Technique:</span>
            <span className="text-sm font-black text-white">{scoreNum == null ? '—' : `${scoreNum.toFixed(0)}/100`}</span>
            <span
              className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded ${
                scoreNum != null && scoreNum >= 85
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : scoreNum != null && scoreNum >= 70
                  ? 'bg-lime-950 text-lime-300 border border-lime-800'
                  : scoreNum != null && scoreNum >= 50
                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                  : 'bg-rose-950 text-rose-300 border border-rose-800'
              }`}
            >
              {scoreBadgeLabel}
            </span>
          </div>
        </div>

        {/* ONE Focus for Next 10 Balls */}
        {oneFocus && (
          <div className="p-4 rounded-xl bg-gradient-to-r from-[#7FEA35]/15 via-[#181B1D] to-[#181B1D] border border-[#7FEA35]/40 flex items-start space-x-3 shadow-inner">
            <div className="p-2 rounded-lg bg-[#7FEA35] text-[#050505] shrink-0 mt-0.5">
              <Target className="w-4 h-4" />
            </div>
            <div className="space-y-0.5">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#7FEA35] font-bold">
                Next 10 Balls — One Single Focus
              </div>
              <div className="text-sm font-bold text-white">{oneFocus.title}</div>
              <p className="text-xs text-[#E1E4E6] leading-relaxed">{oneFocus.cue}</p>
            </div>
          </div>
        )}

        {/* Strengths Row */}
        {strengths.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <div className="text-[11px] font-semibold text-[#A5A9AD] flex items-center space-x-1.5">
              <Award className="w-3.5 h-3.5 text-emerald-400" />
              <span>What went well</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {strengths.map((st, i) => (
                <div
                  key={i}
                  className="bg-[#181B1D] p-2.5 rounded-xl border border-emerald-500/20 text-xs text-[#F5F5F5] flex items-start space-x-2"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white font-semibold">{st.title}: </strong>
                    <span className="text-[#A5A9AD]">{st.sentence}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unmeasurable Notices */}
        {unmeasurable.length > 0 && (
          <div className="space-y-1.5 pt-1">
            {unmeasurable.map((notice, i) => (
              <div
                key={i}
                className="bg-sky-950/40 border border-sky-800/60 rounded-xl p-2.5 text-xs text-sky-200 flex items-start space-x-2"
              >
                <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                <span>{notice}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* B2: Top 3 Plain-English Issue Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-mono uppercase tracking-wider text-[#A5A9AD] font-bold">
            What to improve
          </h4>
          <span className="text-[11px] text-[#A5A9AD]">Showing top {displayCards.length}</span>
        </div>

        {displayCards.length === 0 ? (
          <div className="bg-[#111315] rounded-xl border border-[#303438] p-6 text-center space-y-1">
            <CheckCircle2 className="w-8 h-8 text-[#7FEA35] mx-auto mb-2" />
            <div className="text-sm font-bold text-white">No measured improvement point available</div>
            <p className="text-xs text-[#A5A9AD]">
              This clip did not produce a supported, timestamped measurement to compare with a reference range.
            </p>
          </div>
        ) : (
          displayCards.map((card) => {
            const isExpanded = !!expandedProofs[card.id] || detailMode === 'technical';
            const severityClass =
              card.severity_code === 'high'
                ? 'bg-rose-950/80 text-rose-300 border-rose-800'
                : card.severity_code === 'medium'
                ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                : 'bg-slate-800 text-slate-300 border-slate-700';

            return (
              <div
                key={card.id}
                className="bg-[#111315] rounded-2xl border border-[#303438] hover:border-[#4B5055] transition-all p-5 space-y-4 shadow-sm"
              >
                {/* Issue Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${severityClass}`}>
                        {card.severity_label}
                      </span>
                      <span className="text-[11px] font-mono text-[#A5A9AD]">{card.where_and_when}</span>
                    </div>
                    <h5 className="text-base font-bold text-white tracking-tight">{card.title}</h5>
                    <p className="text-xs font-mono text-[#A5A9AD]">
                      {card.proof.technical_metric_name}: {card.proof.measured_value.toFixed(1)}{card.proof.unit}
                      {' · '}{card.proof.timestamp_sec != null ? `${card.proof.timestamp_sec.toFixed(2)}s` : card.where_and_when}
                      {' · Reference '}{card.proof.ideal_min.toFixed(0)}–{card.proof.ideal_max.toFixed(0)}{card.proof.unit}
                    </p>
                  </div>

                  {/* Visual Fix Buttons */}
                  <div className="flex items-center space-x-1.5 shrink-0">
                    {onSeekToFrame && card.loop_window && (
                      <button
                        onClick={() => onSeekToFrame(card.loop_window.center_frame)}
                        className="px-2.5 py-1 rounded-lg bg-[#181B1D] hover:bg-[#303438] text-xs font-semibold text-[#F5F5F5] border border-[#303438] transition-colors flex items-center space-x-1 cursor-pointer"
                        title="Loop this moment in the video"
                      >
                        <RotateCcw className="w-3 h-3 text-[#7FEA35]" />
                        <span className="hidden sm:inline">Loop Moment</span>
                      </button>
                    )}
                    <button
                      onClick={() => setSelectedProofModalCard(card)}
                      className="px-2.5 py-1 rounded-lg bg-[#181B1D] hover:bg-[#303438] text-xs font-semibold text-[#F5F5F5] border border-[#303438] transition-colors flex items-center space-x-1 cursor-pointer"
                      title="View visual freeze-frame with correction arrow"
                    >
                      <Eye className="w-3 h-3 text-[#7FEA35]" />
                      <span className="hidden sm:inline">You vs Ideal</span>
                    </button>
                  </div>
                </div>

                {/* Plain-English Body */}
                <div className="space-y-2.5 text-xs">
                  {/* Why it matters */}
                  <div className="text-[#F5F5F5] leading-relaxed">
                    <strong className="text-white font-semibold">Why it matters: </strong>
                    <span className="text-[#A5A9AD]">{card.why_it_matters}</span>
                  </div>

                  {/* Feel cue */}
                  <div className="bg-[#181B1D] p-3 rounded-xl border border-[#303438] text-[#F5F5F5] flex items-start space-x-2.5">
                    <div className="p-1 rounded-md bg-[#7FEA35]/15 text-[#7FEA35] shrink-0 mt-0.5">
                      <Target className="w-3.5 h-3.5" />
                    </div>
                    <div className="leading-relaxed">
                      <strong className="text-white font-semibold">How to feel it on the next ball: </strong>
                      <span className="text-[#E1E4E6]">{card.feel_cue}</span>
                    </div>
                  </div>

                  {/* One Drill */}
                  {card.drill && (
                    <div className="bg-[#181B1D] p-3 rounded-xl border border-[#303438] text-xs text-[#A5A9AD] space-y-1">
                      <div className="flex items-center space-x-1.5 text-white font-semibold">
                        <Dumbbell className="w-3.5 h-3.5 text-[#7FEA35]" />
                        <span>Drill: {card.drill.name}</span>
                      </div>
                      <p className="leading-relaxed">{card.drill.instructions}</p>
                    </div>
                  )}
                </div>

                {/* Collapsible Proof Layer */}
                <div className="pt-1 border-t border-[#303438]/50">
                  <button
                    onClick={() => toggleProof(card.id)}
                    className="flex items-center justify-between w-full text-[11px] font-mono text-[#A5A9AD] hover:text-white py-1 transition-colors cursor-pointer"
                  >
                    <span className="flex items-center space-x-1.5">
                      <Sparkles className="w-3 h-3 text-[#7FEA35]" />
                      <span>{isExpanded ? 'Hide technical proof' : 'Show proof (joint angles & sensor data)'}</span>
                    </span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {isExpanded && card.proof && (
                    <div className="mt-3 p-3.5 rounded-xl bg-[#0B0C0E] border border-[#303438] space-y-3 font-mono text-[11px]">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        <div className="bg-[#181B1D] p-2 rounded-lg border border-[#303438]">
                          <div className="text-[10px] text-[#A5A9AD]">Measured</div>
                          <div className="text-xs font-bold text-white">
                            {card.proof.measured_value.toFixed(1)}
                            {card.proof.unit}
                          </div>
                        </div>
                        <div className="bg-[#181B1D] p-2 rounded-lg border border-[#303438]">
                          <div className="text-[10px] text-[#A5A9AD]">Ideal Range</div>
                          <div className="text-xs font-bold text-[#7FEA35]">
                            {card.proof.ideal_min.toFixed(0)}–{card.proof.ideal_max.toFixed(0)}
                            {card.proof.unit}
                          </div>
                        </div>
                        <div className="bg-[#181B1D] p-2 rounded-lg border border-[#303438]">
                          <div className="text-[10px] text-[#A5A9AD]">Timing</div>
                          <div className="text-xs font-bold text-white">
                            {card.proof.timestamp_sec != null ? `${card.proof.timestamp_sec.toFixed(2)}s` : 'Impact'}
                          </div>
                        </div>
                        <div className="bg-[#181B1D] p-2 rounded-lg border border-[#303438]">
                          <div className="text-[10px] text-[#A5A9AD]">Confidence</div>
                          <div className="text-xs font-bold text-white">
                            {Math.round(card.proof.measurement_confidence * 100)}%
                          </div>
                        </div>
                      </div>

                      {/* Sparkline visualization */}
                      {card.proof.sparkline && card.proof.sparkline.length > 2 && (
                        <div className="space-y-1">
                          <div className="text-[10px] text-[#A5A9AD] flex justify-between">
                            <span>{card.proof.technical_metric_name} Trajectory</span>
                            <span>Target: {card.proof.ideal_min.toFixed(0)}–{card.proof.ideal_max.toFixed(0)}{card.proof.unit}</span>
                          </div>
                          <div className="h-10 w-full bg-[#181B1D] rounded-lg p-1.5 flex items-end space-x-1">
                            {card.proof.sparkline.map((val, sIdx) => {
                              const minVal = Math.min(...card.proof.sparkline, card.proof.ideal_min);
                              const maxVal = Math.max(...card.proof.sparkline, card.proof.ideal_max);
                              const range = Math.max(1, maxVal - minVal);
                              const heightPct = Math.max(15, Math.min(100, ((val - minVal) / range) * 100));
                              const isWithin = val >= card.proof.ideal_min && val <= card.proof.ideal_max;
                              return (
                                <div
                                  key={sIdx}
                                  className={`flex-1 rounded-xs transition-all ${
                                    isWithin ? 'bg-[#7FEA35]' : 'bg-amber-400'
                                  }`}
                                  style={{ height: `${heightPct}%` }}
                                  title={`${val}${card.proof.unit}`}
                                />
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Visual Freeze-Frame "You vs Ideal" Modal */}
      {selectedProofModalCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="bg-[#111315] border border-[#303438] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-[#303438]">
              <div className="flex items-center space-x-2">
                <Target className="w-5 h-5 text-[#7FEA35]" />
                <h4 className="text-base font-bold text-white">Visual Fix: You vs Ideal Benchmark</h4>
              </div>
              <button
                onClick={() => setSelectedProofModalCard(null)}
                className="text-slate-400 hover:text-white text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-[#181B1D] border border-[#303438] text-xs space-y-1">
                <div className="font-bold text-white">{selectedProofModalCard.title}</div>
                <div className="text-[#A5A9AD]">{selectedProofModalCard.how_to_fix}</div>
              </div>

              {/* Side-by-side or correction schematic */}
              <div className="grid grid-cols-2 gap-3 p-4 bg-[#0B0C0E] rounded-xl border border-[#303438] text-center">
                <div className="space-y-2">
                  <span className="text-[11px] font-mono uppercase text-amber-400 font-bold">Your Execution</span>
                  <div className="h-32 rounded-lg bg-[#181B1D] border border-amber-500/30 flex flex-col items-center justify-center p-2 text-xs text-slate-300">
                    <span className="text-2xl font-black text-white">
                      {selectedProofModalCard.proof.measured_value.toFixed(1)}°
                    </span>
                    <span className="text-[10px] text-amber-400 mt-1 font-mono">
                      {selectedProofModalCard.proof.measured_value > selectedProofModalCard.proof.ideal_max
                        ? 'Too straight'
                        : 'Over-bent'}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-[11px] font-mono uppercase text-[#7FEA35] font-bold">Ideal Benchmark</span>
                  <div className="h-32 rounded-lg bg-[#181B1D] border border-[#7FEA35]/30 flex flex-col items-center justify-center p-2 text-xs text-slate-300">
                    <span className="text-2xl font-black text-[#7FEA35]">
                      {selectedProofModalCard.proof.ideal_min.toFixed(0)}°–{selectedProofModalCard.proof.ideal_max.toFixed(0)}°
                    </span>
                    <span className="text-[10px] text-[#7FEA35] mt-1 font-mono">Balanced sweet-spot</span>
                  </div>
                </div>
              </div>

              {/* Directional cue arrow */}
              <div className="p-3 rounded-xl bg-[#7FEA35]/10 border border-[#7FEA35]/30 flex items-center space-x-2 text-xs text-white">
                <ArrowRight className="w-4 h-4 text-[#7FEA35] shrink-0" />
                <span>
                  <strong>Correction: </strong>
                  {selectedProofModalCard.feel_cue}
                </span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedProofModalCard(null)}
                className="px-4 py-2 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] text-xs font-bold transition-colors cursor-pointer"
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
