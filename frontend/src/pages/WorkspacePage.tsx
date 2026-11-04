import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Eye,
  Activity,
  Layers,
  Sparkles,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Check,
  Edit3,
  Dumbbell
} from 'lucide-react';
import { AnalysisResult, SessionListItem, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { MetricCard } from '../components/MetricCard';
import { PhaseTimeline } from '../components/PhaseTimeline';
import { CoachingFeedbackList } from '../components/CoachingFeedbackList';
import { RealisticBatterVisualizer } from '../components/RealisticBatterVisualizer';

interface WorkspacePageProps {
  sessionId: string | null;
  onSelectTab: (tab: NavTab) => void;
  onSelectSession?: (sessionId: string) => void;
}

export const WorkspacePage: React.FC<WorkspacePageProps> = ({ sessionId, onSelectTab, onSelectSession }) => {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [availableSessions, setAvailableSessions] = useState<SessionListItem[]>([]);
  const [availableShotsList, setAvailableShotsList] = useState<string[]>([]);
  const [overrideShot, setOverrideShot] = useState<string>('');
  const [isConfirmingShot, setIsConfirmingShot] = useState<boolean>(false);
  const [showOverrideSelect, setShowOverrideSelect] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [currentTimeSec, setCurrentTimeSec] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(0.5);
  const [showSkeletonOverlay, setShowSkeletonOverlay] = useState<boolean>(true);
  const [show3DComparison, setShow3DComparison] = useState<boolean>(false);
  const [hasEnded, setHasEnded] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Load available sessions list for shot switching dropdown
  useEffect(() => {
    api.listSessions(50).then((res) => {
      setAvailableSessions(res.sessions || []);
    }).catch(() => {});

    api.getShots().then((res) => {
      setAvailableShotsList(res.shots.map((s) => s.name));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!sessionId) {
      // Default to first available session if none selected
      api.listSessions(10).then((res) => {
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
      setError(null);
      const data = await api.getAnalysis(id);
      setAnalysis(data);
      setOverrideShot(data.shot_type);
    } catch (err: any) {
      setError(err.message || 'Failed to load session analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmShot = async (newShot: string) => {
    if (!analysis) return;
    try {
      setIsConfirmingShot(true);
      await api.confirmShotType(analysis.session_id, newShot);
      await loadSession(analysis.session_id);
      setShowOverrideSelect(false);
    } catch (err: any) {
      alert(`Failed to update shot type: ${err.message}`);
    } finally {
      setIsConfirmingShot(false);
    }
  };

  const handleSessionChange = (newId: string) => {
    loadSession(newId);
    if (onSelectSession) {
      onSelectSession(newId);
    }
  };

  // Synchronized Canvas Skeleton Drawing
  const renderSkeletonFrame = (frameIdx: number) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas || !videoRef.current) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!showSkeletonOverlay || !analysis) return;

    const metric = analysis.time_series[frameIdx];
    if (!metric) return;

    const w = canvas.width;
    const h = canvas.height;

    const lms = (metric as any).landmarks;
    if (lms && lms.length >= 33) {
      const connections = [
        [11, 12], [11, 23], [12, 24], [23, 24], // Torso
        [11, 13], [13, 15], [12, 14], [14, 16], // Arms
        [23, 25], [25, 27], [24, 26], [26, 28]  // Legs
      ];

      ctx.lineWidth = 3;
      connections.forEach(([i, j]) => {
        const p1 = lms[i];
        const p2 = lms[j];
        if (p1 && p2 && (p1.v ?? 1) > 0.3 && (p2.v ?? 1) > 0.3) {
          ctx.beginPath();
          ctx.moveTo(p1.x * w, p1.y * h);
          ctx.lineTo(p2.x * w, p2.y * h);
          if (i === 23 || i === 25) {
            ctx.strokeStyle = '#22c55e'; // Lead leg green
          } else if (i === 24 || i === 26) {
            ctx.strokeStyle = '#eab308'; // Rear leg amber
          } else {
            ctx.strokeStyle = '#38bdf8'; // Torso/arms cyan
          }
          ctx.stroke();
        }
      });

      // Joint Dots
      [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28].forEach((idx) => {
        const p = lms[idx];
        if (p && (p.v ?? 1) > 0.3) {
          ctx.beginPath();
          ctx.arc(p.x * w, p.y * h, 4, 0, 2 * Math.PI);
          ctx.fillStyle = idx >= 23 ? '#22c55e' : '#38bdf8';
          ctx.fill();
          ctx.strokeStyle = '#020617';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }
      });

      // Modular Bat Tracking Line
      if (metric.bat_detected && metric.bat_tip_x != null && metric.bat_tip_y != null) {
        const batX = metric.bat_tip_x;
        const batY = metric.bat_tip_y;
        const wristIdx = analysis.handedness === 'Left' ? 16 : 15;
        const wrist = lms[wristIdx] || lms[15];
        if (wrist) {
          ctx.beginPath();
          ctx.moveTo(wrist.x * w, wrist.y * h);
          ctx.lineTo(batX * w, batY * h);
          ctx.strokeStyle = '#f59e0b';
          ctx.lineWidth = 5;
          ctx.lineCap = 'round';
          ctx.stroke();

          // Bat tip marker
          ctx.beginPath();
          ctx.arc(batX * w, batY * h, 5, 0, 2 * Math.PI);
          ctx.fillStyle = '#fbbf24';
          ctx.fill();
        }
      }

      // Ball Trajectory Point
      if (metric.ball_detected && metric.ball_x != null && metric.ball_y != null) {
        const ballX = metric.ball_x;
        const ballY = metric.ball_y;
        ctx.beginPath();
        ctx.arc(ballX * w, ballY * h, 6, 0, 2 * Math.PI);
        ctx.fillStyle = '#ef4444';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  };

  // Re-draw skeleton when frame or overlay toggle changes
  useEffect(() => {
    renderSkeletonFrame(currentFrame);
  }, [currentFrame, showSkeletonOverlay, analysis]);

  const handleTimeUpdate = () => {
    if (videoRef.current && analysis) {
      const t = videoRef.current.currentTime;
      setCurrentTimeSec(t);
      const fps = analysis.fps || 30.0;
      const f = Math.min(analysis.analyzed_frames - 1, Math.floor(t * fps));
      setCurrentFrame(f);
      renderSkeletonFrame(f);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      if (hasEnded || videoRef.current.ended || videoRef.current.currentTime >= (videoRef.current.duration || 1) - 0.05) {
        videoRef.current.currentTime = 0;
        setCurrentFrame(0);
        setCurrentTimeSec(0);
        setHasEnded(false);
      }
      const p = videoRef.current.play();
      if (p !== undefined) {
        p.then(() => {
          setIsPlaying(true);
          setHasEnded(false);
        }).catch((err) => {
          console.warn('Playback error:', err);
          setIsPlaying(false);
        });
      }
    }
  };

  const handleReplay = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    setCurrentTimeSec(0);
    setCurrentFrame(0);
    setHasEnded(false);
    renderSkeletonFrame(0);
    const p = videoRef.current.play();
    if (p !== undefined) {
      p.then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.warn('Replay play failed:', err);
        setIsPlaying(false);
      });
    }
  };

  const handleSeekFrame = (targetFrame: number) => {
    if (videoRef.current && analysis) {
      const fps = analysis.fps || 30.0;
      const targetTime = targetFrame / fps;
      videoRef.current.currentTime = targetTime;
      setCurrentTimeSec(targetTime);
      setCurrentFrame(targetFrame);
      setHasEnded(false);
      renderSkeletonFrame(targetFrame);
    }
  };

  const stepFrame = (delta: number) => {
    if (analysis) {
      const next = Math.max(0, Math.min(analysis.analyzed_frames - 1, currentFrame + delta));
      handleSeekFrame(next);
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const handleToggleOverlay = (show: boolean) => {
    setShowSkeletonOverlay(show);
    if (!show && overlayCanvasRef.current) {
      const ctx = overlayCanvasRef.current.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, overlayCanvasRef.current.width, overlayCanvasRef.current.height);
    }
  };

  // Keyboard navigation: Spacebar toggles Play/Pause or Replays, Left/Right steps frames
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.code === 'Space') {
        e.preventDefault();
        if (hasEnded) {
          handleReplay();
        } else {
          togglePlay();
        }
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        stepFrame(-1);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        stepFrame(1);
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        handleReplay();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPlaying, hasEnded, currentFrame, analysis]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center space-y-3">
        <Activity className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
        <h3 className="text-sm font-semibold text-white">Loading Batting Analysis Workspace...</h3>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <ShieldAlert className="w-10 h-10 text-amber-400 mx-auto" />
        <h3 className="text-base font-bold text-white">No Active Analysis Session</h3>
        <p className="text-xs text-slate-400">
          {error || 'Please select an existing session from the Dashboard or upload a new batting video.'}
        </p>
        <button
          onClick={() => onSelectTab('upload')}
          className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-brand-500 text-navy-950 font-bold text-xs"
        >
          <span>Upload Batting Video</span>
        </button>
      </div>
    );
  }

  // Active frame metric
  const currentMetric = analysis.time_series[currentFrame] || {};
  const currentPhase = currentMetric.phase || 'Analyzing';
  const overallScore = analysis.overall_technique_score ?? analysis.summary?.overall_technique_score ?? 82;
  const topMistakes = analysis.top_mistakes || [];

  const getPhaseIndex = (p: string) => {
    const pl = (p || '').toLowerCase();
    if (pl.includes('stance')) return 0;
    if (pl.includes('backlift')) return 1;
    if (pl.includes('stride')) return 2;
    if (pl.includes('downswing')) return 3;
    if (pl.includes('impact') || pl.includes('contact')) return 4;
    if (pl.includes('follow')) return 5;
    if (pl.includes('recovery') || pl.includes('finish')) return 6;
    return 4;
  };

  // Video URL depending on overlay toggle
  const videoSource = showSkeletonOverlay && analysis.annotated_video_path
    ? api.getVideoUrl(analysis.annotated_video_path)
    : api.getVideoUrl(`/api/video/original/${analysis.video_filename}`);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Session Breadcrumb Bar with Shot / Session Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#303438]">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <h1 className="text-xl sm:text-2xl font-black text-[#F5F5F5] tracking-tight uppercase">
              {analysis.shot_type} Technique Workspace
            </h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-bold">
              {analysis.session_id}
            </span>
          </div>
          <p className="text-xs text-[#A5A9AD]">
            Video: <span className="text-[#F5F5F5] font-medium">{analysis.video_filename}</span> • {analysis.handedness}-Handed • {analysis.camera_angle} • {analysis.duration_sec}s
          </p>
        </div>

        {/* Shot Selection Switcher Dropdown */}
        <div className="flex flex-wrap items-center gap-2">
          {availableSessions.length > 0 && (
            <div className="flex items-center space-x-2 bg-[#111315] border border-[#303438] px-2.5 py-1 rounded-xl">
              <span className="text-[11px] font-mono uppercase text-[#A5A9AD] font-bold">Select Shot:</span>
              <select
                value={analysis.session_id}
                onChange={(e) => handleSessionChange(e.target.value)}
                className="bg-transparent text-xs font-bold text-[#7FEA35] focus:outline-none cursor-pointer max-w-[240px]"
                title="Switch Shot Video & Analysis Session"
              >
                {availableSessions.map((s) => (
                  <option key={s.session_id} value={s.session_id} className="bg-[#181B1D] text-[#F5F5F5]">
                    {s.shot_type} — {s.video_filename}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => onSelectTab('biomechanics')}
            className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-[#181B1D] hover:bg-[#111315] text-[#F5F5F5] text-xs font-semibold border border-[#303438] transition-colors cursor-pointer"
          >
            <span>Biomechanics</span>
            <ArrowRight className="w-3.5 h-3.5 text-[#7FEA35]" />
          </button>
          <button
            onClick={() => onSelectTab('comparison')}
            className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-[#181B1D] hover:bg-[#111315] text-[#F5F5F5] text-xs font-semibold border border-[#303438] transition-colors cursor-pointer"
          >
            <span>Compare</span>
            <ArrowRight className="w-3.5 h-3.5 text-[#38BDF8]" />
          </button>
        </div>
      </div>

      {/* Benchmark Header */}
      <div className="bg-[#111315] border border-[#303438] rounded-xl px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#7FEA35] font-bold px-2 py-0.5 rounded bg-[#7FEA35]/10 border border-[#7FEA35]/25">
            Benchmark
          </span>
          <span className="text-xs font-bold text-[#F5F5F5]">{analysis.shot_type} Ideal Technique</span>
          <span className="text-[11px] text-[#A5A9AD] hidden sm:inline">• Reference ranges from coaching biomechanics for this shot</span>
        </div>
        <span className="text-[10px] font-mono text-[#A5A9AD] bg-[#181B1D] px-2 py-0.5 rounded border border-[#303438]">
          MCC / Cricket Australia Biomechanical Framework
        </span>
      </div>

      {/* Soft Warning Banner if Shot Mismatch Detected */}
      {analysis.shot_mismatch_warning && (
        <div className="p-3.5 rounded-xl bg-amber-950/60 border border-amber-600/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-md">
          <div className="flex items-center space-x-2 text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="font-medium">{analysis.shot_mismatch_warning}</span>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => handleConfirmShot(analysis.predicted_shot_type || '')}
              disabled={isConfirmingShot}
              className="px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold transition-colors cursor-pointer"
            >
              Analyse as {analysis.predicted_shot_type}
            </button>
          </div>
        </div>
      )}

      {/* Camera View Notice if Not Standard Side-On */}
      {analysis.camera_view_warning && (
        <div className="p-3 rounded-xl bg-sky-950/60 border border-sky-800/60 flex items-center space-x-2 text-xs text-sky-200 shadow-sm">
          <Eye className="w-4 h-4 text-sky-400 shrink-0" />
          <span>{analysis.camera_view_warning}</span>
        </div>
      )}

      {/* AI Kinematic Classification & Manual Confirmation Banner */}
      <div className="p-4 rounded-2xl bg-[#111315] border border-[#303438] shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-[#7FEA35]/10 border border-[#7FEA35]/30 text-[#7FEA35] text-xs font-mono font-bold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI Classification: {analysis.predicted_shot_type || analysis.shot_type}</span>
            </div>

            {analysis.prediction_confidence != null && (
              <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#181B1D] border border-[#303438] text-[#F5F5F5]">
                Confidence: <strong className="text-[#7FEA35]">{Math.round((analysis.prediction_confidence || 0) * 100)}%</strong>
              </span>
            )}

            {analysis.user_confirmed_shot_type ? (
              <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                <CheckCircle2 className="w-3 h-3" />
                <span>Confirmed by User: {analysis.user_confirmed_shot_type}</span>
              </span>
            ) : analysis.shot_classification?.is_uncertain ? (
              <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950/80 text-amber-400 border border-amber-800">
                <AlertTriangle className="w-3 h-3" />
                <span>Ambiguous Kinematics</span>
              </span>
            ) : (
              <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-sky-950/80 text-sky-400 border border-sky-800">
                <Check className="w-3 h-3" />
                <span>Kinematic Match</span>
              </span>
            )}
          </div>

          <p className="text-xs text-[#A5A9AD] leading-relaxed max-w-3xl">
            {analysis.shot_classification?.rationale ||
              `Evaluated against 2D landmark trajectories (lead knee flexion, rear knee drop, stride expansion, and torso tilt). Current active shot: ${analysis.shot_type}.`}
          </p>
        </div>

        {/* Shot Confirmation / Override Controls */}
        <div className="flex items-center gap-2 shrink-0">
          {!showOverrideSelect ? (
            <div className="flex items-center gap-2">
              {!analysis.user_confirmed_shot_type && (
                <button
                  onClick={() => handleConfirmShot(analysis.predicted_shot_type || analysis.shot_type)}
                  disabled={isConfirmingShot}
                  className="px-3 py-1.5 rounded-lg bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] text-xs font-bold transition-colors cursor-pointer flex items-center space-x-1.5 shadow-sm"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Confirm as {analysis.predicted_shot_type || analysis.shot_type}</span>
                </button>
              )}
              <button
                onClick={() => setShowOverrideSelect(true)}
                className="px-3 py-1.5 rounded-lg bg-[#181B1D] hover:bg-[#303438] text-[#F5F5F5] text-xs font-semibold border border-[#303438] transition-colors cursor-pointer flex items-center space-x-1.5"
              >
                <Edit3 className="w-3.5 h-3.5 text-[#A5A9AD]" />
                <span>Override Shot Type</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-[#181B1D] p-1.5 rounded-xl border border-[#303438]">
              <select
                value={overrideShot}
                onChange={(e) => setOverrideShot(e.target.value)}
                className="bg-[#111315] text-[#F5F5F5] text-xs border border-[#303438] rounded-lg px-2.5 py-1 focus:outline-none focus:border-[#7FEA35]"
              >
                {availableShotsList.map((shotName) => (
                  <option key={shotName} value={shotName}>
                    {shotName}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handleConfirmShot(overrideShot)}
                disabled={isConfirmingShot}
                className="px-3 py-1 rounded-lg bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] text-xs font-bold transition-colors cursor-pointer"
              >
                {isConfirmingShot ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => setShowOverrideSelect(false)}
                className="px-2 py-1 rounded-lg bg-[#111315] text-[#A5A9AD] hover:text-[#F5F5F5] text-xs"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Coach Report: Prominent Overall Technique Score & Top 3 Mistakes */}
      <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#303438]">
          <div className="flex items-center space-x-4">
            <div
              className={`w-16 h-16 rounded-2xl flex flex-col items-center justify-center font-black border ${
                overallScore >= 80
                  ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                  : overallScore >= 65
                  ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                  : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
              }`}
            >
              <span className="text-2xl font-mono leading-none">{overallScore}</span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#A5A9AD]">/ 100</span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-black text-[#F5F5F5] uppercase tracking-tight">Coach Technique Score</h2>
                <span
                  className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${
                    overallScore >= 85
                      ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                      : overallScore >= 70
                      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                      : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                  }`}
                >
                  {overallScore >= 85
                    ? 'Textbook Technique'
                    : overallScore >= 70
                    ? 'Solid Baseline'
                    : 'Needs Technical Attention'}
                </span>
              </div>
              <p className="text-xs text-[#A5A9AD] mt-0.5">
                Evaluated against standardized biomechanical ideal tolerances for{' '}
                <strong className="text-[#F5F5F5]">{analysis.shot_type}</strong>.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShow3DComparison(!show3DComparison)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center space-x-1.5 ${
                show3DComparison
                  ? 'bg-[#7FEA35] text-[#050505] border-[#7FEA35] font-bold'
                  : 'bg-[#181B1D] text-[#F5F5F5] border-[#303438] hover:bg-[#303438]'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{show3DComparison ? 'Hide 3D Reference Model' : 'Compare with 3D Model'}</span>
            </button>
          </div>
        </div>

        {/* Top 3 Mistakes Cards */}
        {topMistakes.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#A5A9AD] font-bold flex items-center space-x-1.5">
              <span>Primary Technique Faults & Corrective Drills</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {topMistakes.map((m, idx) => (
                <div
                  key={m.id || idx}
                  className="bg-[#181B1D] rounded-xl border border-[#303438] p-3.5 space-y-2 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                        m.severity === 'strength'
                          ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                          : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                      }`}>
                        {m.severity === 'strength' ? 'Optimal Technique' : `Fault #${idx + 1} • ${m.phase}`}
                      </span>
                      {m.measurement_provenance && (
                        <span className="text-[10px] font-mono text-[#A5A9AD]">
                          {m.measurement_provenance}
                        </span>
                      )}
                    </div>
                    {m.thumbnail_path && (
                      <div className="rounded-lg overflow-hidden border border-[#303438] aspect-video bg-black">
                        <img
                          src={api.getVideoUrl(m.thumbnail_path)}
                          alt={m.title}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}
                    <h4 className="text-xs font-bold text-[#F5F5F5]">{m.title}</h4>
                    <div className="text-[11px] font-mono text-slate-300 bg-[#111315] p-2 rounded border border-[#303438]">
                      <div>Measured: <strong className="text-white">{m.measurement}</strong></div>
                      <div className="text-[#A5A9AD]">Ideal: {m.reference_benchmark || m.observed_value}</div>
                    </div>
                    <p className="text-xs text-[#A5A9AD] leading-relaxed">{m.why_it_matters}</p>
                  </div>
                  <div className="pt-2 border-t border-[#303438] text-xs">
                    <div className="flex items-start space-x-1.5 text-xs text-[#7FEA35]">
                      <Dumbbell className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-[#F5F5F5] font-semibold">Drill: </strong>
                        <span>{m.practical_drill}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Side-by-Side 3D Model Comparison View when enabled */}
      {show3DComparison && (
        <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-3 animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-2 border-b border-[#303438]">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#7FEA35] font-bold flex items-center space-x-2">
              <Sparkles className="w-4 h-4" />
              <span>Side-by-Side Technique Comparison: Player vs MCC 3D Model</span>
            </h3>
            <span className="text-xs font-mono text-[#A5A9AD]">
              Synchronized Phase: <strong className="text-white">{currentPhase}</strong>
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="text-xs font-mono text-[#A5A9AD] font-bold">1. Player Pose & Skeleton (Frame {currentFrame})</div>
              <div className="rounded-xl overflow-hidden border border-[#303438] aspect-video bg-black flex items-center justify-center">
                <img
                  src={api.getVideoUrl(analysis.thumbnail_path)}
                  alt="Player skeleton"
                  className="w-full h-full object-contain"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="text-xs font-mono text-[#7FEA35] font-bold">2. Realistic 3D Reference Model ({analysis.shot_type})</div>
              <div className="rounded-xl overflow-hidden border border-[#303438] aspect-video bg-[#0d0f11]">
                <RealisticBatterVisualizer
                  shotName={analysis.shot_type}
                  initialPhaseIndex={getPhaseIndex(currentPhase)}
                  handedness={analysis.handedness as any}
                  cameraView={analysis.detected_camera_view || 'side'}
                  showControls={false}
                  className="w-full h-full"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Metric Comparison Table */}
      {analysis.metric_comparison_table && analysis.metric_comparison_table.length > 0 && (
        <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#303438]">
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-[#F5F5F5] font-bold flex items-center space-x-2">
                <Layers className="w-4 h-4 text-[#7FEA35]" />
                <span>Phase-by-Phase Metric Comparison Table</span>
              </h3>
              <p className="text-[11px] text-[#A5A9AD] mt-0.5">
                Every evaluated kinematic metric across stroke phases compared directly to {analysis.shot_type} reference benchmark ranges.
              </p>
            </div>
            <span className="text-[11px] font-mono text-[#A5A9AD] bg-[#181B1D] px-2.5 py-1 rounded border border-[#303438]">
              {analysis.metric_comparison_table.length} Parameters Evaluated
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#303438] text-[11px] font-mono uppercase text-[#A5A9AD]">
                  <th className="py-2.5 px-3">Phase</th>
                  <th className="py-2.5 px-3">Metric</th>
                  <th className="py-2.5 px-3 text-right">Yours</th>
                  <th className="py-2.5 px-3 text-right">Ideal Range</th>
                  <th className="py-2.5 px-3 text-center">Verdict</th>
                  <th className="py-2.5 px-3 text-center">Validity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2226] font-mono">
                {analysis.metric_comparison_table.map((row, rIdx) => {
                  const isOk = row.verdict === 'OK';
                  const isLow = row.verdict === 'Too Low';
                  const isHigh = row.verdict === 'Too High';

                  return (
                    <tr key={rIdx} className="hover:bg-[#181B1D]/60 transition-colors">
                      <td className="py-2 px-3 font-semibold text-[#F5F5F5]">{row.phase_label}</td>
                      <td className="py-2 px-3 text-slate-300 font-sans">{row.metric_name}</td>
                      <td className="py-2 px-3 text-right font-bold text-white">
                        {row.yours_formatted}
                      </td>
                      <td className="py-2 px-3 text-right text-[#A5A9AD]">{row.ideal_range}</td>
                      <td className="py-2 px-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isOk
                            ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                            : isLow
                            ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            : isHigh
                            ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}>
                          {row.verdict}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        <span className="text-[10px] text-[#A5A9AD]">{row.validity}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Main Grid: Video Player + HUD on Left, Key Summary Metrics on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Video Workspace & Controls */}
        <div className="lg:col-span-2 space-y-4">
          <div className="relative rounded-2xl overflow-hidden bg-black border border-navy-800 shadow-2xl aspect-video flex items-center justify-center group">
            <video
              ref={videoRef}
              src={videoSource}
              onTimeUpdate={handleTimeUpdate}
              onEnded={() => {
                setIsPlaying(false);
                setHasEnded(true);
              }}
              onPlay={() => {
                setIsPlaying(true);
                setHasEnded(false);
              }}
              onPause={() => setIsPlaying(false)}
              className="w-full h-full object-contain"
              playsInline
            />

            {/* Client-Side Canvas Skeleton Overlay */}
            <canvas
              ref={overlayCanvasRef}
              className={`absolute inset-0 w-full h-full pointer-events-none z-[4] ${
                showSkeletonOverlay ? 'opacity-100' : 'opacity-0'
              } transition-opacity duration-150`}
            />

            {/* In-Video Live Replay Overlay when video finishes */}
            {hasEnded && (
              <div className="absolute inset-0 bg-navy-950/75 backdrop-blur-sm flex flex-col items-center justify-center space-y-3 z-10 animate-in fade-in duration-200">
                <button
                  onClick={handleReplay}
                  className="flex items-center space-x-2 px-6 py-3 rounded-xl bg-brand-500 hover:bg-brand-400 text-navy-950 font-black text-sm shadow-2xl shadow-brand-500/30 transform hover:scale-105 active:scale-95 transition-all cursor-pointer"
                >
                  <RotateCcw className="w-5 h-5 stroke-[2.5]" />
                  <span>Replay Practice Stroke</span>
                </button>
                <p className="text-xs text-slate-300 font-mono">Press Space or 'R' to replay</p>
              </div>
            )}

            {/* In-Video Live HUD Overlay */}
            <div className="absolute top-3 left-3 bg-navy-950/85 backdrop-blur-md border border-navy-800 px-3 py-2 rounded-xl text-xs font-mono space-y-0.5 shadow-lg pointer-events-none z-[5]">
              <div className="text-brand-400 font-bold flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
                <span>Phase: {currentPhase}</span>
              </div>
              <div className="text-slate-300 text-[11px]">
                Knee: <strong className="text-white">{currentMetric.lead_knee_angle ?? '--'}°</strong> | Elbow: <strong className="text-white">{currentMetric.lead_elbow_angle ?? '--'}°</strong> | Lean: <strong className="text-white">{currentMetric.torso_inclination ?? '--'}°</strong>
              </div>
              {currentMetric.bat_detected && currentMetric.bat_angle_deg !== null && (
                <div className="text-amber-400 text-[10px] flex items-center space-x-1">
                  <span>Bat: <strong>{currentMetric.bat_angle_deg}°</strong></span>
                  {currentMetric.bat_speed_norm && (
                    <span>• Speed: <strong>{Number(currentMetric.bat_speed_norm).toFixed(1)}</strong></span>
                  )}
                  {currentMetric.ball_detected && <span className="text-rose-400">• Ball in frame</span>}
                </div>
              )}
            </div>

            {/* In-Video Toggle Overlay Switch */}
            <div className="absolute top-3 right-3 flex items-center space-x-1 bg-navy-950/85 backdrop-blur-md border border-navy-800 p-1 rounded-lg text-xs z-[5]">
              <button
                onClick={() => handleToggleOverlay(true)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-all cursor-pointer ${
                  showSkeletonOverlay ? 'bg-brand-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Skeleton Overlay
              </button>
              <button
                onClick={() => handleToggleOverlay(false)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-all cursor-pointer ${
                  !showSkeletonOverlay ? 'bg-brand-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Original Video
              </button>
            </div>
          </div>

          {/* Interactive Player Controls */}
          <div className="bg-navy-900/90 rounded-xl border border-navy-800 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => stepFrame(-1)}
                  className="p-2 rounded-lg bg-navy-950 hover:bg-navy-800 text-slate-300 border border-navy-800 transition-colors"
                  title="Previous Frame (Left Arrow)"
                >
                  <SkipBack className="w-4 h-4" />
                </button>
                <button
                  onClick={togglePlay}
                  className="p-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-navy-950 font-bold shadow-md transition-all cursor-pointer"
                  title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-navy-950" />}
                </button>
                <button
                  onClick={() => stepFrame(1)}
                  className="p-2 rounded-lg bg-navy-950 hover:bg-navy-800 text-slate-300 border border-navy-800 transition-colors"
                  title="Next Frame (Right Arrow)"
                >
                  <SkipForward className="w-4 h-4" />
                </button>
                <button
                  onClick={handleReplay}
                  className="p-2 rounded-lg bg-navy-950 hover:bg-navy-800 text-slate-300 border border-navy-800 transition-colors cursor-pointer"
                  title="Replay from Beginning (R)"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>

              {/* Timestamp & Frame Counter */}
              <div className="text-center font-mono text-xs">
                <span className="text-white font-bold">{currentTimeSec.toFixed(2)}s</span>
                <span className="text-slate-500"> / {analysis.duration_sec.toFixed(2)}s</span>
                <span className="text-slate-400 ml-2">
                  (F: <strong className="text-white">{currentFrame}</strong>/{analysis.analyzed_frames})
                </span>
              </div>

              {/* Playback speed selector */}
              <div className="flex items-center space-x-1 bg-navy-950 p-1 rounded-lg border border-navy-800 text-xs font-mono">
                {[0.25, 0.5, 1.0].map((speed) => (
                  <button
                    key={speed}
                    onClick={() => handleSpeedChange(speed)}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                      playbackSpeed === speed ? 'bg-navy-800 text-brand-400 font-bold' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>

            {/* Frame Scrubber Slider */}
            <input
              type="range"
              min={0}
              max={Math.max(1, analysis.analyzed_frames - 1)}
              value={currentFrame}
              onChange={(e) => handleSeekFrame(Number(e.target.value))}
              className="w-full h-1.5 bg-navy-950 rounded-lg appearance-none cursor-pointer accent-brand-500"
            />
          </div>

          {/* Phase Timeline synchronized with video cursor */}
          <PhaseTimeline
            phases={analysis.phases}
            currentFrame={currentFrame}
            totalFrames={analysis.analyzed_frames}
            onSelectFrame={handleSeekFrame}
          />
        </div>

        {/* Right Column: Key Biomechanical Summary & Active Frame Stats */}
        <div className="space-y-4">
          <div className="bg-navy-900/80 rounded-xl border border-navy-800 p-4 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span>Impact Kinematic Snapshot</span>
              <span className="text-[10px] font-mono text-brand-400">MCC Standard</span>
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                title="Lead Knee Flexion"
                value={analysis.summary.lead_knee_flexion_at_impact}
                unit="°"
                benchmark="115°–135°"
                status={
                  analysis.summary.lead_knee_flexion_at_impact &&
                  analysis.summary.lead_knee_flexion_at_impact >= 115 &&
                  analysis.summary.lead_knee_flexion_at_impact <= 135
                    ? 'optimal'
                    : 'warning'
                }
                description="Interior angle of front leg at estimated bat contact window."
              />

              <MetricCard
                title="Lead Elbow Flexion"
                value={analysis.summary.lead_elbow_flexion_at_impact}
                unit="°"
                benchmark="135°–160°"
                status={
                  analysis.summary.lead_elbow_flexion_at_impact &&
                  analysis.summary.lead_elbow_flexion_at_impact < 125
                    ? 'warning'
                    : 'optimal'
                }
                description="Shoulder-elbow-wrist interior angle at impact."
              />

              <MetricCard
                title="Lead Arm Extension"
                value={
                  analysis.summary.lead_arm_extension_at_impact
                    ? Number((analysis.summary.lead_arm_extension_at_impact * 100).toFixed(0))
                    : null
                }
                unit="%"
                benchmark="85%–95%"
                status="optimal"
                description="Straight-line arm extension into the shot."
              />

              <MetricCard
                title="Torso Forward Lean"
                value={analysis.summary.torso_lean_at_impact}
                unit="°"
                benchmark="20°–32°"
                status="optimal"
                description="Spine inclination from vertical image axis at contact."
              />

              <MetricCard
                title="Head Stability"
                value={analysis.summary.head_stability_index}
                unit="index"
                benchmark="< 0.08"
                status="optimal"
                description="Standard deviation of normalized head displacement across execution."
              />

              <MetricCard
                title="Max Stance Width"
                value={analysis.summary.stance_width_ratio_max}
                unit="x torso"
                benchmark="1.3x–1.7x"
                status="info"
                description="Inter-ankle distance divided by torso height."
              />
            </div>
          </div>

          {/* Current Frame Instantaneous Readout */}
          <div className="bg-navy-900/80 rounded-xl border border-navy-800 p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Frame {currentFrame} Instantaneous Pose
              </h4>
              <span className="text-[10px] font-mono text-cricket-sky">
                Conf: {(currentMetric.confidence * 100).toFixed(0)}%
              </span>
            </div>

            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex items-center justify-between p-2 rounded bg-navy-950 border border-navy-800/80">
                <span className="text-slate-400">Current Phase:</span>
                <span className="text-brand-400 font-semibold">{currentPhase}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-navy-950 border border-navy-800/80">
                <span className="text-slate-400">Lead Knee / Elbow:</span>
                <span className="text-white font-semibold">
                  {currentMetric.lead_knee_angle ?? '--'}° / {currentMetric.lead_elbow_angle ?? '--'}°
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-navy-950 border border-navy-800/80">
                <span className="text-slate-400">Torso Inclination:</span>
                <span className="text-white font-semibold">{currentMetric.torso_inclination ?? '--'}°</span>
              </div>
              {currentMetric.bat_detected && currentMetric.bat_angle_deg !== null && (
                <div className="flex items-center justify-between p-2 rounded bg-navy-950 border border-navy-800/80">
                  <span className="text-amber-400">Bat Angle / Speed:</span>
                  <span className="text-amber-300 font-semibold">
                    {currentMetric.bat_angle_deg}° {currentMetric.bat_speed_norm ? `(${Number(currentMetric.bat_speed_norm).toFixed(1)})` : ''}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Model Pipeline Metadata Card */}
          <div className="bg-navy-900/80 rounded-xl border border-navy-800 p-4 space-y-2 text-xs">
            <h4 className="font-semibold text-slate-300 flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-brand-400" />
              <span>Inference Pipeline</span>
            </h4>
            <div className="text-[11px] text-slate-400 space-y-1 font-mono">
              <div>Pose: {analysis.model_metadata.pose_estimator}</div>
              <div>Phase Model: {analysis.model_metadata.phase_classifier}</div>
              <div>Sampling: 1 in {analysis.sample_rate} frame(s)</div>
              <div>Tracking Success: {analysis.model_metadata.tracking_rate}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Explainable Coaching Feedback */}
      <div className="pt-4">
        <CoachingFeedbackList
          observations={analysis.coaching_feedback}
          shotType={analysis.shot_type}
        />
      </div>

      {/* Limitations Disclaimer */}
      <div className="bg-navy-950 border border-navy-800/80 rounded-xl p-4 text-xs text-slate-500 space-y-2">
        <div className="flex items-center space-x-2 text-slate-400 font-semibold">
          <ShieldAlert className="w-4 h-4 text-amber-500" />
          <span>Biomechanical & Ethical Limitations</span>
        </div>
        <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-500">
          {analysis.limitations.map((lim, i) => (
            <li key={i}>{lim}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
