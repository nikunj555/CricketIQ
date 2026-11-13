import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Gauge,
  CheckCircle2,
  AlertTriangle,
  X,
  Upload,
  Video,
  Award,
  ChevronRight,
  ShieldCheck,
  Info,
  Layers,
  Sparkles,
  Compass,
  Crosshair,
  Dumbbell,
  Shuffle
} from 'lucide-react';
import { CricketShot, ReferenceDetail } from '../types/cricket';
import { api } from '../services/api';
import { RealisticBatterVisualizer } from './RealisticBatterVisualizer';
import { Batter3DCanvas } from './3d/Batter3DCanvas';
import { getShotAnimation, ShotAnimationDefinition } from '../data/shotAnimations';
import { createShotVariant, nextShotVariant } from '../data/shotVariants';
import { getShotTechnique } from '../data/shotTechnique';

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
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [previewMode, setPreviewMode] = useState<'blueprint' | '3d' | 'video'>('blueprint');
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(0.75);
  const [activePhaseIndex, setActivePhaseIndex] = useState<number>(0); // Default to Stance
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [isVariationActive, setIsVariationActive] = useState<boolean>(false);
  const [variantId, setVariantId] = useState(0);
  const [replayToken, setReplayToken] = useState(0);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Authoritative shot animation from shotAnimations.ts
  const shotAnimation: ShotAnimationDefinition | null = useMemo(() => {
    return getShotAnimation(shot.name || shot.id);
  }, [shot.id, shot.name]);
  const animationVariant = useMemo(() => {
    if (!isVariationActive) return undefined;
    return createShotVariant(variantId, shot.name || shot.id);
  }, [isVariationActive, variantId, shot.id, shot.name]);

  useEffect(() => {
    setIsVariationActive(false);
    setVariantId(0);
    setReplayToken(0);
  }, [shot.id]);

  useEffect(() => {
    loadReference();
  }, [shot.id]);

  const loadReference = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getShotReference(shot.id);
      setRefDetail(data);
    } catch (err: any) {
      console.warn('Reference load notice:', err.message);
      if (shot.reference_video_url) {
        setRefDetail({
          id: shot.reference_id || 'ref_default',
          shot_id: shot.id,
          shot_name: shot.name,
          player_name: shot.reference_player || 'National Academy Benchmark',
          source: shot.reference_source || 'Verified Cricket Biomechanics Reference',
          video_url: shot.reference_video_url,
          thumbnail_url: shot.reference_thumbnail_url,
          camera_view: 'Side View',
          verification_status: 'verified',
          description: shot.description,
          stance_setup: 'Balanced standard batting stance with feet shoulder-width apart.',
          footwork_weight_transfer: 'Controlled stride and synchronized weight transfer.',
          body_positioning: 'Upright torso with head stationed over the ball line.',
          technique_points: [
            shot.technique_notes || `Maintain textbook execution for ${shot.name}.`,
            'High front elbow guiding the vertical plane.',
            'Lead knee flexes to absorb momentum.',
            'Hold the finish to verify balance.'
          ],
          common_mistakes: shotAnimation?.commonMistakes || [
            'Playing away from the body without full commitment to footwork',
            'Closing or opening the bat face prematurely through impact',
            'Collapsing the front knee or losing balance during downswing'
          ],
          phases: [
            { phase_name: 'Stance', frame_window: '0% - 20%', description: 'Initial balanced ready position.', lead_knee_target: '165° - 170°', key_cue: 'Relaxed grip, soft knees' },
            { phase_name: 'Backlift', frame_window: '20% - 35%', description: 'Backswing initiated toward slips.', lead_knee_target: '160° - 165°', key_cue: 'Top hand directs bat face' },
            { phase_name: 'Stride', frame_window: '35% - 50%', description: 'Decisive footwork establishing base.', lead_knee_target: '135° - 150°', key_cue: 'Head leads stride' },
            { phase_name: 'Downswing', frame_window: '50% - 65%', description: 'Bat accelerates smoothly into swing arc.', lead_knee_target: '125° - 135°', key_cue: 'Lead elbow leads path' },
            { phase_name: 'Impact window', frame_window: '65% - 74%', description: 'Bat strikes ball under eye line.', lead_knee_target: '118° - 128°', key_cue: 'Eyes locked on contact' },
            { phase_name: 'Follow-through', frame_window: '74% - 88%', description: 'Smooth deceleration through line.', lead_knee_target: '130° - 145°', key_cue: 'Hold pose for balance' },
            { phase_name: 'Recovery', frame_window: '88% - 100%', description: 'Controlled reset toward neutral.', lead_knee_target: '160° - 168°', key_cue: 'Push back into stance' },
          ],
          key_metrics: {
            lead_knee_flexion_at_impact: 124.0,
            torso_lean_at_impact: 25.0,
            head_stability_index: 0.035
          }
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const setSpeed = (spd: number) => {
    setPlaybackSpeed(spd);
    if (videoRef.current) {
      videoRef.current.playbackRate = spd;
    }
  };

  const handleRestart = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleCustomUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    try {
      setUploading(true);
      const fd = new FormData();
      fd.append('file', uploadFile);
      fd.append('shot_id', shot.id);
      fd.append('player_name', 'Custom Authorized Reference');
      fd.append('source', 'User Uploaded Reference');
      await api.uploadCustomReference(fd);
      setShowUploadModal(false);
      loadReference();
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const videoSource = refDetail?.video_url
    ? api.getVideoUrl(refDetail.video_url)
    : shot.reference_video_url
    ? api.getVideoUrl(shot.reference_video_url)
    : null;

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
            {/* Coaching Intent */}
            {(() => {
              const tech = getShotTechnique(shot.name || shot.id);
              return tech?.intent ? (
                <div className="text-xs text-[#7FEA35] font-medium flex items-center gap-1.5 pt-0.5">
                  <Compass className="w-3.5 h-3.5 shrink-0" />
                  <span>Intent: {tech.intent}</span>
                </div>
              ) : null;
            })()}
            {refDetail && (
              <p className="text-xs text-[#A5A9AD] flex items-center space-x-2">
                <span className="text-[#F5F5F5] font-semibold">{refDetail.player_name}</span>
                <span>•</span>
                <span className="text-[#A5A9AD]">{refDetail.source}</span>
                <span>•</span>
                <span className="font-mono text-[11px] text-[#7FEA35]">{refDetail.camera_view}</span>
              </p>
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

        {/* Preview Mode Selector: 3D Kinematics vs 2D Blueprint vs Authentic Video */}
        <div className="flex flex-wrap items-center justify-between border-b border-[#303438] pb-3 gap-2">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPreviewMode('3d')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center space-x-1.5 cursor-pointer ${
                previewMode === '3d'
                  ? 'bg-[#7FEA35] text-black shadow-md'
                  : 'bg-[#111315] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Reference Technique Model</span>
            </button>
            <button
              onClick={() => setPreviewMode('blueprint')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center space-x-1.5 cursor-pointer ${
                previewMode === 'blueprint'
                  ? 'bg-[#00f0ff] text-black shadow-md'
                  : 'bg-[#111315] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>2D Kinematic Blueprint</span>
            </button>
            <button
              onClick={() => setPreviewMode('video')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center space-x-1.5 cursor-pointer ${
                previewMode === 'video'
                  ? 'bg-[#7FEA35] text-black shadow-md'
                  : 'bg-[#111315] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438]'
              }`}
            >
              <Video className="w-3.5 h-3.5" />
              <span>Authentic Video Footage</span>
            </button>
          </div>
          <span className="text-[11px] font-mono text-[#A5A9AD] hidden md:inline">
            {previewMode === '3d'
              ? 'WebGL forward kinematics on 3D pitch'
              : previewMode === 'blueprint'
              ? 'Multi-view 2D biomechanical blueprint'
              : 'Masterclass benchmark footage'}
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 -mt-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsVariationActive(false)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                !isVariationActive
                  ? 'bg-[#7FEA35] text-black font-bold shadow-sm'
                  : 'bg-[#111315] border border-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D]'
              }`}
            >
              Original Motion
            </button>
            <button
              onClick={() => {
                if (!isVariationActive) {
                  setIsVariationActive(true);
                } else {
                  setVariantId((prev) => nextShotVariant(prev, shot.name || shot.id).id);
                }
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                isVariationActive
                  ? 'bg-[#7FEA35] text-black font-bold shadow-sm'
                  : 'bg-[#111315] border border-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D]'
              }`}
            >
              <Shuffle className="w-3.5 h-3.5" />
              {isVariationActive ? `Variation ${((variantId % 3) + 3) % 3 + 1} of 3` : 'Enable Variations'}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[#A5A9AD] font-mono">
              {!isVariationActive
                ? `Authored ${shot.name} textbook technique`
                : `Natural human spread · Variation ${((variantId % 3) + 3) % 3 + 1} of 3`}
            </span>
            <button
              onClick={() => setReplayToken((n) => n + 1)}
              className="px-3 py-1.5 rounded-lg border border-[#303438] bg-[#111315] text-[#F5F5F5] text-xs font-semibold flex items-center gap-1.5 hover:bg-[#181B1D] cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Replay
            </button>
          </div>
        </div>

        {/* Main Visualizer / Video Player Section */}
        {previewMode === '3d' ? (
          <Batter3DCanvas
            shotName={shot.name}
            variant={animationVariant}
            replayToken={replayToken}
            tempoScale={animationVariant ? animationVariant.tempo : 1.0}
            height={390}
            showTrail={true}
            showControls={true}
            showPhaseScrubber={true}
            showCameraPresets={true}
            autoOrbitDefault={false}
          />
        ) : previewMode === 'blueprint' ? (
          <RealisticBatterVisualizer
            shotId={shot.id}
            shotName={shot.name}
            variant={animationVariant}
            replayToken={replayToken}
            category={shot.category}
            initialPhaseIndex={activePhaseIndex}
            onPhaseChange={(idx) => setActivePhaseIndex(idx)}
            autoPlay={true}
            showControls={false}
          />
        ) : (
          <div className="space-y-3">
            <div className="relative rounded-2xl overflow-hidden bg-[#0A0C0E] border border-[#303438] aspect-video max-h-[380px] w-full flex items-center justify-center">
              {videoSource ? (
                <video
                  ref={videoRef}
                  src={videoSource}
                  loop
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-contain"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
              ) : (
                <div className="text-center p-8 space-y-3">
                  <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
                  <h4 className="text-sm font-bold text-[#F5F5F5]">No Authentic Footage Available</h4>
                  <p className="text-xs text-[#A5A9AD] max-w-md">
                    CricketIQ refuses to show generic substitute videos for unrelated shots. You can upload an authorized reference video below.
                  </p>
                  <button
                    onClick={() => setShowUploadModal(true)}
                    className="px-4 py-2 rounded-xl bg-[#7FEA35] text-black text-xs font-bold hover:bg-[#94EE58] cursor-pointer"
                  >
                    Upload Reference Video
                  </button>
                </div>
              )}

              {/* Video Controls Overlay */}
              {videoSource && (
                <div className="absolute bottom-3 left-3 right-3 bg-[#0B0D0F]/90 backdrop-blur-md px-4 py-2.5 rounded-xl border border-[#303438] flex items-center justify-between text-xs text-[#F5F5F5]">
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={togglePlay}
                      className="p-1.5 rounded-lg bg-[#181B1D] hover:bg-[#303438] text-[#7FEA35] transition-colors cursor-pointer"
                      title={isPlaying ? 'Pause' : 'Play'}
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-[#7FEA35]" />}
                    </button>
                    <button
                      onClick={handleRestart}
                      className="p-1.5 rounded-lg bg-[#181B1D] hover:bg-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] transition-colors cursor-pointer"
                      title="Replay"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <span className="text-[11px] font-mono text-[#A5A9AD]">
                      {refDetail?.player_name || 'Master Class'}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-[#A5A9AD] font-mono">Speed:</span>
                    {[0.5, 0.75, 1.0].map((spd) => (
                      <button
                        key={spd}
                        onClick={() => setSpeed(spd)}
                        className={`px-2 py-1 rounded text-[11px] font-mono font-semibold cursor-pointer transition-all ${
                          playbackSpeed === spd
                            ? 'bg-[#7FEA35] text-black'
                            : 'bg-[#181B1D] text-[#A5A9AD] hover:text-[#F5F5F5]'
                        }`}
                      >
                        {spd}x
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <p className="text-xs text-[#A5A9AD] leading-relaxed">
              {refDetail?.description || shot.description}
            </p>
          </div>
        )}

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
          {/* Key Technique Points */}
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
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-[#303438]">
          <button
            onClick={() => setShowUploadModal(true)}
            className="w-full sm:w-auto px-4 py-2 rounded-xl bg-[#111315] hover:bg-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] text-xs font-semibold border border-[#303438] transition-colors cursor-pointer flex items-center justify-center space-x-1.5"
            title="Upload an authorized coach/player video to replace or supplement this reference"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Custom Reference</span>
          </button>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
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

        {/* Custom Reference Upload Sub-modal */}
        {showUploadModal && (
          <div className="fixed inset-0 z-60 bg-black/80 flex items-center justify-center p-4">
            <div className="bg-[#181B1D] border border-[#303438] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
              <div className="flex items-center justify-between pb-3 border-b border-[#303438]">
                <h3 className="text-sm font-bold text-[#F5F5F5]">
                  Upload Reference Video: {shot.name}
                </h3>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="text-[#A5A9AD] hover:text-[#F5F5F5]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-[#A5A9AD]">
                Upload an authorized MP4/MOV recording demonstrating textbook execution of this stroke. It will be immediately registered in the reference database.
              </p>
              <form onSubmit={handleCustomUpload} className="space-y-4">
                <input
                  type="file"
                  accept="video/mp4,video/quicktime,video/webm"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-[#A5A9AD] file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-[#7FEA35] file:text-black cursor-pointer"
                  required
                />
                <div className="flex items-center justify-end space-x-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowUploadModal(false)}
                    className="px-3 py-1.5 rounded-lg bg-[#111315] text-[#A5A9AD] text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={uploading || !uploadFile}
                    className="px-4 py-1.5 rounded-lg bg-[#7FEA35] text-black text-xs font-bold disabled:opacity-50"
                  >
                    {uploading ? 'Uploading...' : 'Save Reference'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
