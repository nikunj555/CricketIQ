import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  Dumbbell,
  Columns,
  Zap,
  Loader2,
  Info,
  BookOpen,
  Target
} from 'lucide-react';
import { AnalysisResult, SessionListItem, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { MetricCard } from '../components/MetricCard';
import { PhaseTimeline } from '../components/PhaseTimeline';
import { CoachingFeedbackList } from '../components/CoachingFeedbackList';
import { LearnShotCard } from '../components/LearnShotCard';
import { LearningVideo } from '../types/cricket';

interface WorkspacePageProps {
  sessionId: string | null;
  onSelectTab: (tab: NavTab) => void;
  onSelectSession?: (sessionId: string) => void;
}

function getJointFromMistake(text: string): string | null {
  const lower = text.toLowerCase();
  if (lower.includes('knee')) return 'frontKnee';
  if (lower.includes('elbow')) return 'leadElbow';
  if (lower.includes('head') || lower.includes('eye')) return 'head';
  if (lower.includes('shoulder')) return 'leadShoulder';
  if (lower.includes('wrist') || lower.includes('grip') || lower.includes('hand')) return 'leadWrist';
  if (lower.includes('hip') || lower.includes('torso') || lower.includes('pelvis')) return 'torso';
  if (lower.includes('foot') || lower.includes('stride') || lower.includes('ankle')) return 'frontAnkle';
  return null;
}

export const WorkspacePage: React.FC<WorkspacePageProps> = ({ sessionId, onSelectTab, onSelectSession }) => {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [availableSessions, setAvailableSessions] = useState<SessionListItem[]>([]);
  const [availableShotsList, setAvailableShotsList] = useState<string[]>([]);
  const [overrideShot, setOverrideShot] = useState<string>('');
  const [isConfirmingShot, setIsConfirmingShot] = useState<boolean>(false);
  const [showOverrideSelect, setShowOverrideSelect] = useState<boolean>(false);
  const [showWhyConfidence, setShowWhyConfidence] = useState<boolean>(false);
  const [currentLang, setCurrentLang] = useState<string>('en');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [currentTimeSec, setCurrentTimeSec] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [showSkeletonOverlay, setShowSkeletonOverlay] = useState<boolean>(true);
  const [showAngles, setShowAngles] = useState<boolean>(true);
  const [originalOnly, setOriginalOnly] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'single' | 'synced'>('single');
  const [singleSource, setSingleSource] = useState<'original' | 'annotated'>('original');
  const [activeMistakeJoint, setActiveMistakeJoint] = useState<string | null>(null);
  const [hasEnded, setHasEnded] = useState<boolean>(false);
  const [isSwitchingStriker, setIsSwitchingStriker] = useState<boolean>(false);
  const [dismissMismatch, setDismissMismatch] = useState<boolean>(false);
  const [learningVideos, setLearningVideos] = useState<LearningVideo[]>([]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const syncedVideoRef = useRef<HTMLVideoElement | null>(null);
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

  useEffect(() => {
    if (analysis?.learning_videos && analysis.learning_videos.length > 0) {
      setLearningVideos(analysis.learning_videos);
    } else if (analysis?.shot_type) {
      api.getShotVideos(analysis.shot_type)
        .then((vids) => setLearningVideos(vids || []))
        .catch(() => setLearningVideos([]));
    } else {
      setLearningVideos([]);
    }
  }, [analysis?.shot_type, analysis?.learning_videos]);

  const loadSession = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAnalysis(id);
      setAnalysis(data);
      setOverrideShot(data.shot_type);
      setHasEnded(false);
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
      const updated = await api.reanalyzeShot(analysis.session_id, newShot, currentLang);
      setAnalysis(updated);
      setOverrideShot(updated.shot_type);
      setShowOverrideSelect(false);
    } catch (err: any) {
      alert(`Failed to update shot type: ${err.message}`);
    } finally {
      setIsConfirmingShot(false);
    }
  };

  const handleLanguageChange = async (lang: string) => {
    setCurrentLang(lang);
    if (!analysis) return;
    try {
      const updated = await api.reanalyzeShot(analysis.session_id, analysis.shot_type, lang);
      setAnalysis(updated);
    } catch (err: any) {
      console.warn('Language reanalyze failed:', err);
    }
  };

  const handleReanalyzeAsSelected = async (targetShot: string) => {
    if (!analysis) return;
    try {
      setIsConfirmingShot(true);
      const updated = await api.reanalyzeShot(analysis.session_id, targetShot);
      setAnalysis(updated);
      setOverrideShot(updated.shot_type);
    } catch (err: any) {
      alert(`Failed to re-analyse as ${targetShot}: ${err.message}`);
    } finally {
      setIsConfirmingShot(false);
    }
  };

  const handleSelectStriker = async (trackId: number) => {
    if (!analysis) return;
    try {
      setIsSwitchingStriker(true);
      await api.selectStriker(analysis.session_id, trackId);
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const status = await api.getProcessingStatus(analysis.session_id);
          if (status.status === 'completed') {
            clearInterval(interval);
            await loadSession(analysis.session_id);
            setIsSwitchingStriker(false);
          } else if (status.status === 'failed' || attempts > 60) {
            clearInterval(interval);
            setIsSwitchingStriker(false);
            alert(`Re-processing failed: ${status.error || 'Timeout'}`);
          }
        } catch {
          // ignore transient poll error
        }
      }, 1000);
    } catch (err: any) {
      alert(`Failed to switch striker: ${err.message}`);
      setIsSwitchingStriker(false);
    }
  };

  const handleSessionChange = (newId: string) => {
    loadSession(newId);
    if (onSelectSession) {
      onSelectSession(newId);
    }
  };

  const findFrameIndex = useCallback((timeSec: number): number => {
    if (!analysis || !analysis.time_series || analysis.time_series.length === 0) return 0;
    const ts = analysis.time_series;
    let low = 0;
    let high = ts.length - 1;
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const t = ts[mid]?.timestamp_sec ?? 0;
      if (Math.abs(t - timeSec) < 0.016) return mid;
      if (t < timeSec) low = mid + 1;
      else high = mid - 1;
    }
    return Math.max(0, Math.min(ts.length - 1, low));
  }, [analysis]);

  const getMetricVerdict = useCallback((metricName: string, value: number | null | undefined, phaseName?: string) => {
    if (value == null || !analysis?.metric_comparison_table) {
      return { color: '#38bdf8', verdict: 'ok' };
    }
    const match = analysis.metric_comparison_table.find((m) => {
      const nameMatch = m.metric === metricName || m.metric_name?.toLowerCase().includes(metricName.toLowerCase());
      if (phaseName) {
        return nameMatch && (m.phase?.toLowerCase() === phaseName.toLowerCase() || m.phase_label?.toLowerCase() === phaseName.toLowerCase());
      }
      return nameMatch;
    }) || analysis.metric_comparison_table.find((m) => m.metric === metricName || m.metric_name?.toLowerCase().includes(metricName.toLowerCase()));

    if (!match || match.ideal_min == null || match.ideal_max == null) {
      return { color: '#22c55e', verdict: 'ok' };
    }

    const min = match.ideal_min;
    const max = match.ideal_max;
    const span = Math.max(10, max - min);
    const tol = span * 0.15;

    if (value >= min && value <= max) {
      return { color: '#22c55e', verdict: 'ok' };
    }
    if ((value >= min - tol && value < min) || (value > max && value <= max + tol)) {
      return { color: '#f59e0b', verdict: 'near' };
    }
    return { color: '#ef4444', verdict: 'outside' };
  }, [analysis]);

  const renderCanvasAtTime = useCallback((mediaTime: number) => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !analysis) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.clientWidth;
    const ch = canvas.clientHeight;
    if (cw === 0 || ch === 0) return;

    if (canvas.width !== Math.round(cw * dpr) || canvas.height !== Math.round(ch * dpr)) {
      canvas.width = Math.round(cw * dpr);
      canvas.height = Math.round(ch * dpr);
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cw, ch);

    if (originalOnly || singleSource === 'annotated') {
      ctx.restore();
      return;
    }

    const vw = video.videoWidth || 1920;
    const vh = video.videoHeight || 1080;
    const videoAR = vw / vh;
    const containerAR = cw / ch;

    let renderW = cw;
    let renderH = ch;
    let offsetX = 0;
    let offsetY = 0;

    if (videoAR > containerAR) {
      renderW = cw;
      renderH = cw / videoAR;
      offsetY = (ch - renderH) / 2;
    } else {
      renderH = ch;
      renderW = ch * videoAR;
      offsetX = (cw - renderW) / 2;
    }

    const toX = (nx: number) => offsetX + nx * renderW;
    const toY = (ny: number) => offsetY + ny * renderH;

    const frameIdx = findFrameIndex(mediaTime);
    const metric = analysis.time_series?.[frameIdx];
    const phaseName = metric?.phase || '';
    const isImpact = phaseName.toLowerCase().includes('impact') || phaseName.toLowerCase().includes('contact');

    if (!metric || !metric.pose_detected || !metric.landmarks || metric.landmarks.length < 33) {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.75)';
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.4)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(offsetX + 12, offsetY + 12, 130, 24, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px monospace';
      ctx.fillText('No pose detected', offsetX + 20, offsetY + 28);
      ctx.restore();
      return;
    }

    const lms = metric.landmarks;

    if (showSkeletonOverlay) {
      const connections: [number, number, string][] = [
        [11, 12, '#38bdf8'], [11, 23, '#38bdf8'], [12, 24, '#38bdf8'], [23, 24, '#38bdf8'],
        [11, 13, '#38bdf8'], [13, 15, '#38bdf8'],
        [12, 14, '#94a3b8'], [14, 16, '#94a3b8'],
        [23, 25, '#22c55e'], [25, 27, '#22c55e'],
        [24, 26, '#eab308'], [26, 28, '#eab308']
      ];

      ctx.lineWidth = isImpact ? 3.5 : 2.5;
      connections.forEach(([i, j, defaultColor]) => {
        const p1 = lms[i];
        const p2 = lms[j];
        if (p1 && p2 && (p1.v ?? 1) > 0.25 && (p2.v ?? 1) > 0.25) {
          ctx.beginPath();
          ctx.moveTo(toX(p1.x), toY(p1.y));
          ctx.lineTo(toX(p2.x), toY(p2.y));
          ctx.strokeStyle = defaultColor;
          ctx.stroke();
        }
      });

      [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28].forEach((idx) => {
        const p = lms[idx];
        if (p && (p.v ?? 1) > 0.25) {
          ctx.beginPath();
          ctx.arc(toX(p.x), toY(p.y), isImpact ? 5 : 4, 0, 2 * Math.PI);
          ctx.fillStyle = idx >= 23 ? '#22c55e' : '#38bdf8';
          ctx.fill();
          ctx.strokeStyle = '#020617';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }
      });

      if (metric.bat_detected && metric.bat_tip_x != null && metric.bat_tip_y != null) {
        const wristIdx = analysis.handedness === 'Left' ? 16 : 15;
        const wrist = lms[wristIdx] || lms[15];
        if (wrist) {
          ctx.beginPath();
          ctx.moveTo(toX(wrist.x), toY(wrist.y));
          ctx.lineTo(toX(metric.bat_tip_x), toY(metric.bat_tip_y));
          ctx.strokeStyle = '#f59e0b';
          ctx.lineWidth = 4;
          ctx.lineCap = 'round';
          ctx.stroke();

          ctx.beginPath();
          ctx.arc(toX(metric.bat_tip_x), toY(metric.bat_tip_y), 5, 0, 2 * Math.PI);
          ctx.fillStyle = '#fbbf24';
          ctx.fill();
        }
      }

      if (metric.ball_detected && metric.ball_x != null && metric.ball_y != null) {
        ctx.beginPath();
        ctx.arc(toX(metric.ball_x), toY(metric.ball_y), 6, 0, 2 * Math.PI);
        ctx.fillStyle = '#ef4444';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    if (showAngles) {
      const isLeft = analysis.handedness === 'Left';
      const leadKneeIdx = isLeft ? 26 : 25;
      const rearKneeIdx = isLeft ? 25 : 26;
      const leadElbowIdx = isLeft ? 14 : 13;

      const angleEntries = [
        {
          name: 'lead_knee_angle',
          label: 'Knee',
          val: metric.lead_knee_angle,
          jointIdx: leadKneeIdx,
          pA: isLeft ? 24 : 23,
          pB: leadKneeIdx,
          pC: isLeft ? 28 : 27
        },
        {
          name: 'rear_knee_angle',
          label: 'Rear Knee',
          val: metric.rear_knee_angle,
          jointIdx: rearKneeIdx,
          pA: isLeft ? 23 : 24,
          pB: rearKneeIdx,
          pC: isLeft ? 27 : 28
        },
        {
          name: 'lead_elbow_angle',
          label: 'Elbow',
          val: metric.lead_elbow_angle,
          jointIdx: leadElbowIdx,
          pA: isLeft ? 12 : 11,
          pB: leadElbowIdx,
          pC: isLeft ? 16 : 15
        }
      ];

      angleEntries.forEach((entry) => {
        if (entry.val != null && !isNaN(entry.val)) {
          const joint = lms[entry.jointIdx];
          const ptA = lms[entry.pA];
          const ptC = lms[entry.pC];
          if (joint && (joint.v ?? 1) > 0.25) {
            const jx = toX(joint.x);
            const jy = toY(joint.y);
            const { color } = getMetricVerdict(entry.name, entry.val, phaseName);

            ctx.beginPath();
            if (ptA && ptC) {
              const angA = Math.atan2(toY(ptA.y) - jy, toX(ptA.x) - jx);
              const angC = Math.atan2(toY(ptC.y) - jy, toX(ptC.x) - jx);
              ctx.arc(jx, jy, 18, Math.min(angA, angC), Math.max(angA, angC));
            } else {
              ctx.arc(jx, jy, 18, 0, Math.PI);
            }
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5;
            ctx.stroke();

            const text = `${Math.round(entry.val)}°`;
            ctx.font = 'bold 11px system-ui, -apple-system, sans-serif';
            const metrics = ctx.measureText(text);
            const padX = 5;
            const badgeW = metrics.width + padX * 2;
            const badgeH = 16;
            const bx = jx + 12;
            const by = jy - 8;

            ctx.fillStyle = 'rgba(11, 15, 23, 0.85)';
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.roundRect(bx, by, badgeW, badgeH, 4);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#ffffff';
            ctx.fillText(text, bx + padX, by + 12);
          }
        }
      });

      if (metric.torso_inclination != null) {
        const hip = lms[23];
        if (hip) {
          const { color } = getMetricVerdict('torso_lean', metric.torso_inclination, phaseName);
          const hx = toX(hip.x) - 45;
          const hy = toY(hip.y) - 20;
          const text = `Lean ${Math.round(metric.torso_inclination)}°`;
          ctx.font = 'bold 10px monospace';
          const tw = ctx.measureText(text).width;
          ctx.fillStyle = 'rgba(11, 15, 23, 0.85)';
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.roundRect(hx, hy, tw + 8, 16, 4);
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = color;
          ctx.fillText(text, hx + 4, hy + 12);
        }
      }
    }

    if (isImpact) {
      ctx.fillStyle = 'rgba(245, 158, 11, 0.9)';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(offsetX + 12, offsetY + 12, 125, 26, 6);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#050505';
      ctx.font = 'bold 11px monospace';
      ctx.fillText('⚡ IMPACT FRAME', offsetX + 20, offsetY + 29);
    }

    ctx.restore();
  }, [analysis, findFrameIndex, getMetricVerdict, showSkeletonOverlay, showAngles, originalOnly, singleSource]);

  // Video Frame Loop driven by requestVideoFrameCallback
  useEffect(() => {
    let animId: number;
    let handleVfc: number;
    const video = videoRef.current;
    if (!video) return;

    const onFrame = (now: DOMHighResTimeStamp, metadata?: any) => {
      const mediaTime = metadata?.mediaTime ?? video.currentTime;
      setCurrentTimeSec(mediaTime);
      const f = findFrameIndex(mediaTime);
      setCurrentFrame(f);
      renderCanvasAtTime(mediaTime);

      const dur = video.duration || analysis?.duration_sec || 1;
      if (video.ended || mediaTime >= dur - 0.05) {
        setIsPlaying(false);
        setHasEnded(true);
      }

      if (viewMode === 'synced' && syncedVideoRef.current) {
        const diff = Math.abs(syncedVideoRef.current.currentTime - mediaTime);
        if (diff > 0.08) {
          syncedVideoRef.current.currentTime = mediaTime;
        }
      }

      if ('requestVideoFrameCallback' in video) {
        handleVfc = (video as any).requestVideoFrameCallback(onFrame);
      } else {
        animId = requestAnimationFrame(onFrame);
      }
    };

    if ('requestVideoFrameCallback' in video) {
      handleVfc = (video as any).requestVideoFrameCallback(onFrame);
    } else {
      animId = requestAnimationFrame(onFrame);
    }

    return () => {
      if ('cancelVideoFrameCallback' in video && handleVfc) {
        (video as any).cancelVideoFrameCallback(handleVfc);
      }
      if (animId) cancelAnimationFrame(animId);
    };
  }, [analysis, findFrameIndex, renderCanvasAtTime, viewMode]);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (isPlaying) {
      video.pause();
      if (syncedVideoRef.current) syncedVideoRef.current.pause();
      setIsPlaying(false);
    } else {
      const dur = video.duration || analysis?.duration_sec || 1;
      if (hasEnded || video.ended || video.currentTime >= dur - 0.05) {
        video.currentTime = 0;
        if (syncedVideoRef.current) syncedVideoRef.current.currentTime = 0;
        setCurrentTimeSec(0);
        setCurrentFrame(0);
        setHasEnded(false);
      }
      video.play().then(() => {
        setIsPlaying(true);
        setHasEnded(false);
        if (syncedVideoRef.current) syncedVideoRef.current.play().catch(() => {});
      }).catch((err) => {
        console.warn('Playback play failed:', err);
        setIsPlaying(false);
      });
    }
  };

  const handleReplay = () => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = 0;
    if (syncedVideoRef.current) syncedVideoRef.current.currentTime = 0;
    setCurrentTimeSec(0);
    setCurrentFrame(0);
    setHasEnded(false);
    renderCanvasAtTime(0);
    video.play().then(() => {
      setIsPlaying(true);
      if (syncedVideoRef.current) syncedVideoRef.current.play().catch(() => {});
    }).catch(() => setIsPlaying(false));
  };

  const handleSeekFrame = (targetFrame: number) => {
    const video = videoRef.current;
    if (!video || !analysis) return;
    const metric = analysis.time_series?.[targetFrame];
    const targetTime = metric?.timestamp_sec ?? (targetFrame / (analysis.fps || 30.0));
    video.currentTime = targetTime;
    if (syncedVideoRef.current) syncedVideoRef.current.currentTime = targetTime;
    setCurrentTimeSec(targetTime);
    setCurrentFrame(targetFrame);
    setHasEnded(false);
    renderCanvasAtTime(targetTime);
  };

  const stepFrame = (delta: number) => {
    if (!analysis) return;
    const maxF = Math.max(0, analysis.analyzed_frames - 1);
    const nextF = Math.max(0, Math.min(maxF, currentFrame + delta));
    handleSeekFrame(nextF);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (videoRef.current) videoRef.current.playbackRate = speed;
    if (syncedVideoRef.current) syncedVideoRef.current.playbackRate = speed;
  };

  // Keyboard navigation: Spacebar toggles Play/Pause or Replay, Left/Right steps frames, R restarts
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
  const overallScore = analysis.overall_technique_score ?? analysis.summary?.overall_technique_score ?? null;
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

  // Video URLs for Original and Annotated streams
  const originalVideoUrl = analysis ? api.getVideoUrl(`/api/video/original/${analysis.video_filename}`) : '';
  const annotatedVideoUrl = analysis?.annotated_video_path ? api.getVideoUrl(analysis.annotated_video_path) : '';
  const primaryVideoSource = singleSource === 'annotated' && annotatedVideoUrl ? annotatedVideoUrl : originalVideoUrl;

  // Calibrated Plain-English Confidence Variables
  const shotConf = analysis?.shot_confidence;
  const confPct =
    shotConf?.confidence != null
      ? Math.round(shotConf.confidence)
      : Math.round((analysis?.prediction_confidence ?? 0) * 100);
  const confLevel =
    shotConf?.level ||
    (confPct >= 85 ? 'Very sure' : confPct >= 65 ? 'Fairly sure' : confPct >= 45 ? 'Not very sure' : "Can't tell");
  const confLevelCode =
    shotConf?.level_code ||
    (confPct >= 85 ? 'very_sure' : confPct >= 65 ? 'fairly_sure' : confPct >= 45 ? 'not_sure' : 'cant_tell');

  const confColor =
    confLevelCode === 'very_sure'
      ? 'text-emerald-400'
      : confLevelCode === 'fairly_sure'
      ? 'text-[#7FEA35]'
      : confLevelCode === 'not_sure'
      ? 'text-amber-400'
      : 'text-slate-400';

  const confBarBg =
    confLevelCode === 'very_sure'
      ? 'bg-emerald-400'
      : confLevelCode === 'fairly_sure'
      ? 'bg-[#7FEA35]'
      : confLevelCode === 'not_sure'
      ? 'bg-amber-400'
      : 'bg-slate-500';

  const confBadgeClass =
    confLevelCode === 'very_sure'
      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
      : confLevelCode === 'fairly_sure'
      ? 'bg-lime-950/80 text-lime-300 border-lime-800'
      : confLevelCode === 'not_sure'
      ? 'bg-amber-950/80 text-amber-300 border-amber-800'
      : 'bg-slate-800 text-slate-300 border-slate-700';

  const candidatePills =
    shotConf?.top3?.map((candidate) => {
      const c = candidate as any;
      return {
        shot: c.shot_name ?? c.shot ?? 'Possible shot',
        pct: c.confidence_pct ?? c.pct ?? Math.round((c.calibrated_probability ?? c.calibrated_prob ?? c.score ?? 0) * 100)
      };
    }) ||
    analysis?.shot_classification?.top_candidates?.map((c) => ({
      shot: c.shot_name,
      pct: (c as any).confidence_pct ?? Math.round(c.score * 100)
    })) ||
    [];

  const confidenceReasons =
    shotConf?.reasons && shotConf.reasons.length > 0
      ? shotConf.reasons
      : [
          ...(((analysis?.shot_classification as any)?.evidence || []) as string[]),
          ...(analysis?.camera_view_warning ? [analysis.camera_view_warning] : []),
          'Not enough evidence to provide further confidence details.'
        ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Header: Batting Technique Coach Header with Shot Check Status */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 pb-4 border-b border-[#303438]">
        <div className="space-y-2 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-black text-[#F5F5F5] tracking-tight">
              Batting Analysis: <span className="text-[#7FEA35]">{analysis.shot_type}</span>
            </h1>

            {/* Shot Check Status Badge */}
            {analysis.shot_check_status === 'confirmed' ? (
              <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Shot confirmed</span>
              </span>
            ) : analysis.shot_check_status === 'mismatch' ? (
              <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Shot check: Swing resembles {analysis.predicted_shot_type}</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Could not confirm the shot type</span>
              </span>
            )}

            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-bold">
              {analysis?.session_id}
            </span>
          </div>

          <p className="text-xs text-[#A5A9AD] pt-0.5">
            Technique Benchmark:{' '}
            <span className="text-white font-bold">{analysis?.shot_type}</span> • Video:{' '}
            <span className="text-[#F5F5F5] font-medium">{analysis?.video_filename}</span> •{' '}
            {analysis?.handedness}-Handed • {analysis?.camera_angle} • {analysis?.duration_sec}s
          </p>
        </div>

        {/* Top Action Controls: Session Selector & Tab Shortcuts */}
        <div className="flex flex-wrap items-center gap-2">
          {availableSessions.length > 0 && (
            <div className="flex items-center space-x-2 bg-[#111315] border border-[#303438] px-2.5 py-1 rounded-xl">
              <span className="text-[11px] font-mono uppercase text-[#A5A9AD] font-bold">Select Session:</span>
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

      {/* Shot Mismatch Banner: Only shown when confident swing is another shot and user hasn't dismissed */}
      {!dismissMismatch && analysis.shot_mismatch_warning && (
        <div className="p-4 rounded-xl bg-amber-950/70 border border-amber-600/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-md">
          <div className="flex items-center space-x-2 text-amber-200">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <div className="font-bold text-amber-300 text-sm">{analysis.shot_mismatch_warning}</div>
              <div className="text-[11px] text-amber-200/80">
                Your feedback below is for the shot you selected ({analysis.shot_type}). You can switch if the other shot is correct.
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            {analysis.predicted_shot_type && analysis.predicted_shot_type !== analysis.shot_type && (
              <button
                onClick={() => handleReanalyzeAsSelected(analysis.predicted_shot_type!)}
                disabled={isConfirmingShot}
                className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold transition-colors cursor-pointer shadow"
              >
                Analyse as {analysis.predicted_shot_type}
              </button>
            )}
            <button
              onClick={() => setDismissMismatch(true)}
              className="px-3 py-1.5 rounded-lg bg-[#181B1D] hover:bg-[#25282c] text-white border border-[#303438] font-semibold transition-colors cursor-pointer"
            >
              Keep {analysis.shot_type}
            </button>
          </div>
        </div>
      )}

      {/* Striker Isolation & Candidate Overrides */}
      {analysis.striker_isolation_evidence && (
        <div className="p-3.5 rounded-xl bg-[#111315] border border-[#303438] space-y-2 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <span className={`w-2.5 h-2.5 rounded-full ${
                (analysis.striker_isolation_evidence.confidence ?? 0.85) < 0.40
                  ? 'bg-amber-400 animate-ping'
                  : 'bg-[#7FEA35] animate-pulse'
              }`}></span>
              <span className="font-bold text-white text-xs">
                Striker Locked: Track #{analysis.striker_track_id ?? analysis.striker_isolation_evidence.active_striker_id}{' '}
                <span className="font-normal text-[11px] text-[#A5A9AD]">
                  ({analysis.striker_isolation_evidence.selection_method === 'user_specified_track'
                    ? 'User Selected'
                    : `Auto-detected: ${Math.round((analysis.striker_isolation_evidence.confidence ?? 0.85) * 100)}% confidence`})
                </span>
              </span>
            </div>
            {isSwitchingStriker && (
              <div className="flex items-center space-x-1.5 text-xs text-[#7FEA35]">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Re-analyzing with chosen batter...</span>
              </div>
            )}
          </div>

          {((analysis.striker_candidates && analysis.striker_candidates.length > 1) ||
            (analysis.striker_isolation_evidence.all_tracks && Object.keys(analysis.striker_isolation_evidence.all_tracks).length > 1)) && (
            <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-[#303438]/60">
              <span className="text-[11px] text-[#A5A9AD]">Switch Batter:</span>
              {(analysis.striker_candidates || Object.entries(analysis.striker_isolation_evidence.all_tracks || {}).map(([tid, meta]: [string, any]) => ({
                track_id: Number(tid),
                role: meta.role || 'other',
                confidence: meta.confidence || 0.5,
                striker_score: meta.striker_score || 0.0,
                is_selected: Number(tid) === (analysis.striker_track_id ?? analysis.striker_isolation_evidence?.active_striker_id)
              }))).map((cand: any) => {
                const isActive = cand.track_id === (analysis.striker_track_id ?? analysis.striker_isolation_evidence?.active_striker_id);
                return (
                  <button
                    key={cand.track_id}
                    type="button"
                    onClick={() => !isActive && !isSwitchingStriker && handleSelectStriker(cand.track_id)}
                    disabled={isActive || isSwitchingStriker}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all cursor-pointer ${
                      isActive
                        ? 'bg-[#7FEA35]/15 border border-[#7FEA35] text-[#7FEA35] font-bold'
                        : 'bg-[#181B1D] border border-[#303438] text-[#A5A9AD] hover:text-white'
                    }`}
                  >
                    Person #{cand.track_id} {isActive ? '(Locked)' : ''}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* SECTION A: How this shot should be played */}
      <div id="section-how-to-play" className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#303438]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-lg bg-[#7FEA35]/15 text-[#7FEA35] font-mono font-bold text-xs flex items-center justify-center border border-[#7FEA35]/30">A</span>
              <h2 className="text-base font-bold text-[#F5F5F5] uppercase tracking-wide">
                How this shot should be played: {analysis.shot_type}
              </h2>
            </div>
            <p className="text-xs text-[#A5A9AD] mt-1">
              Textbook mechanical execution steps and key body positions for a proper {analysis.shot_type}.
            </p>
          </div>
          {analysis.guidance_note && (
            <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#181B1D] text-slate-300 border border-[#303438] max-w-md">
              {analysis.guidance_note}
            </span>
          )}
        </div>

        {/* Learn this shot Link Card (replaces masterclass panel) */}
        {learningVideos.length > 0 && (
          <LearnShotCard videos={learningVideos} />
        )}

        {analysis.how_to_play?.bat_path && (
          <div className="bg-[#181B1D] p-3 rounded-xl border border-[#303438] text-xs">
            <span className="font-bold text-[#7FEA35]">Bat Path: </span>
            <span className="text-slate-200">{analysis.how_to_play.bat_path}</span>
          </div>
        )}

        {analysis.how_to_play?.phase_steps && analysis.how_to_play.phase_steps.length > 0 ? (
          <div className="space-y-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#A5A9AD] font-bold">
              Execution Phases & Key Body Positions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {analysis.how_to_play.phase_steps.map((step, idx) => (
                <div key={idx} className="bg-[#181B1D] p-3 rounded-xl border border-[#303438] space-y-1">
                  <div className="text-[11px] font-mono text-[#7FEA35] font-bold">Step {idx + 1}</div>
                  <p className="text-xs text-slate-200 leading-relaxed">{step}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-400">Step-by-step guidance available for {analysis.shot_type}.</p>
        )}

        {analysis.how_to_play?.key_points && analysis.how_to_play.key_points.length > 0 && (
          <div className="pt-2 border-t border-[#303438]/60 space-y-1.5">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#A5A9AD] font-bold">
              Key Technique Cues
            </h3>
            <div className="flex flex-wrap gap-2">
              {analysis.how_to_play.key_points.map((pt, idx) => (
                <span key={idx} className="text-xs bg-[#181B1D] px-2.5 py-1 rounded-lg border border-[#303438] text-slate-300">
                  • {pt}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* SECTION B: What you did */}
      <div id="section-what-you-did" className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#303438]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-lg bg-sky-500/15 text-sky-400 font-mono font-bold text-xs flex items-center justify-center border border-sky-500/30">B</span>
              <h2 className="text-base font-bold text-[#F5F5F5] uppercase tracking-wide">
                What you did: Phase-by-Phase Measurements
              </h2>
            </div>
            <p className="text-xs text-[#A5A9AD] mt-1">
              Your measured body angles across each stroke phase, compared against {analysis.shot_type} ideal benchmark ranges.
            </p>
          </div>
          <div className="text-[11px] font-mono text-sky-300 bg-sky-950/40 border border-sky-800/60 px-3 py-1.5 rounded-xl">
            Camera angle caveat: Evaluated from {analysis.camera_angle || 'side-on'} view. Metrics not reliable from this view are marked 'not measurable from this angle'.
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#303438] text-[11px] font-mono uppercase text-[#A5A9AD]">
                <th className="py-2.5 px-3">Phase</th>
                <th className="py-2.5 px-3">Metric</th>
                <th className="py-2.5 px-3 text-right">What You Did</th>
                <th className="py-2.5 px-3 text-right">Ideal Range</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3 text-center">Data Validity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2226] font-mono">
              {analysis.metric_comparison_table && analysis.metric_comparison_table.length > 0 ? (
                analysis.metric_comparison_table.map((row, rIdx) => {
                  const isOk = row.verdict === 'OK';
                  const isLow = row.verdict === 'Too Low';
                  const isHigh = row.verdict === 'Too High';
                  const isUnavail = row.verdict === 'not measurable from this angle' || row.validity === 'UNAVAILABLE';

                  return (
                    <tr
                      key={rIdx}
                      onClick={() => {
                        if (row.timestamp_sec != null) {
                          handleSeekFrame(findFrameIndex(row.timestamp_sec));
                        } else if (row.frame_index != null) {
                          handleSeekFrame(row.frame_index);
                        }
                      }}
                      className="hover:bg-[#181B1D]/80 transition-colors cursor-pointer"
                      title="Click to seek to this phase frame in the video"
                    >
                      <td className="py-2.5 px-3 font-semibold text-[#F5F5F5]">{row.phase_label}</td>
                      <td className="py-2.5 px-3 text-slate-300 font-sans">{row.metric_name}</td>
                      <td className="py-2.5 px-3 text-right font-bold">
                        {isUnavail ? (
                          <span className="text-slate-500 font-sans italic text-[11px]">not measurable from this angle</span>
                        ) : (
                          <span className="text-white">
                            {row.yours_formatted}{' '}
                            {row.timestamp_sec != null && (
                              <span className="text-[10px] text-[#A5A9AD] font-normal">(@ {row.timestamp_sec}s)</span>
                            )}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-[#A5A9AD]">{row.ideal_range}</td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isOk
                            ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                            : isLow
                            ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            : isHigh
                            ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}>
                          {isOk ? 'Within Range' : isUnavail ? 'N/A' : 'Needs Work'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          row.validity === 'MEASURED'
                            ? 'bg-[#181B1D] text-emerald-400 border border-emerald-900/50'
                            : row.validity === 'MODEL_INFERRED'
                            ? 'bg-[#181B1D] text-purple-400 border border-purple-900/50'
                            : row.validity === 'ESTIMATED'
                            ? 'bg-[#181B1D] text-amber-400 border border-amber-900/50'
                            : 'bg-[#181B1D] text-slate-500 border border-slate-800'
                        }`}>
                          {row.validity}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-slate-500">
                    No comparison metrics available for this session.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION C: Your mistakes */}
      <div id="section-mistakes" className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#303438]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-lg bg-amber-500/15 text-amber-400 font-mono font-bold text-xs flex items-center justify-center border border-amber-500/30">C</span>
              <h2 className="text-base font-bold text-[#F5F5F5] uppercase tracking-wide">
                Your mistakes (Top Technical Faults)
              </h2>
            </div>
            <p className="text-xs text-[#A5A9AD] mt-1">
              Top faults ranked by importance: what went wrong, measured vs ideal, why it matters, and how to fix it.
            </p>
          </div>
          <span className="text-[11px] font-mono text-[#A5A9AD] bg-[#181B1D] px-2.5 py-1 rounded border border-[#303438]">
            {topMistakes.length} Detected Faults
          </span>
        </div>

        {topMistakes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {topMistakes.map((m, idx) => {
              const detectedJoint = getJointFromMistake(m.title + ' ' + (m.measurement || '') + ' ' + (m.why_it_matters || ''));
              const isSelectedFault = activeMistakeJoint === detectedJoint && detectedJoint !== null;
              return (
                <div
                  key={m.id || idx}
                  onClick={() => {
                    if (m.timestamp_sec != null) {
                      handleSeekFrame(findFrameIndex(m.timestamp_sec));
                    } else if (m.frame_index != null) {
                      handleSeekFrame(m.frame_index);
                    }
                    setActiveMistakeJoint(detectedJoint);
                  }}
                  className={`rounded-xl border p-4 space-y-3 flex flex-col justify-between cursor-pointer transition-all ${
                    isSelectedFault
                      ? 'bg-[#181B1D] border-[#7FEA35] shadow-[0_0_15px_rgba(127,234,53,0.15)] ring-1 ring-[#7FEA35]'
                      : 'bg-[#181B1D] border-[#303438] hover:border-[#7FEA35]/50 hover:bg-[#1a1e22]'
                  }`}
                >
                  <div className="space-y-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded border bg-amber-500/15 text-amber-400 border-amber-500/30">
                        Fault #{idx + 1} • {m.phase}
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
                    <h4 className="text-sm font-bold text-[#F5F5F5]">{m.title}</h4>
                    <div className="text-[11px] font-mono text-slate-300 bg-[#111315] p-2.5 rounded-lg border border-[#303438] space-y-1">
                      <div>What went wrong: <strong className="text-white">{m.measurement}</strong></div>
                      <div className="text-[#A5A9AD]">Ideal benchmark: {m.reference_benchmark || m.observed_value}</div>
                    </div>
                    <div>
                      <span className="text-[11px] font-bold text-slate-300 block mb-0.5">Why it matters:</span>
                      <p className="text-xs text-[#A5A9AD] leading-relaxed">{m.why_it_matters}</p>
                    </div>
                  </div>
                  <div className="pt-2.5 border-t border-[#303438] text-xs">
                    <div className="flex items-start space-x-1.5 text-xs text-[#7FEA35]">
                      <Dumbbell className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-[#F5F5F5] font-semibold">Fix / Drill: </strong>
                        <span>{m.practical_drill}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-[#181B1D] border border-[#303438] text-center text-xs text-slate-400">
            No major technical faults identified. Technique aligns with ideal benchmark ranges for {analysis.shot_type}.
          </div>
        )}
      </div>

      {/* SECTION D: The one thing to fix first */}
      <div id="section-fix-first" className="bg-[#111315] rounded-2xl border-2 border-[#7FEA35]/60 p-5 space-y-3 shadow-lg bg-gradient-to-r from-[#111315] via-[#151c14] to-[#111315]">
        <div className="flex items-center space-x-2">
          <span className="w-6 h-6 rounded-lg bg-[#7FEA35] text-black font-mono font-bold text-xs flex items-center justify-center">D</span>
          <h2 className="text-base font-bold text-[#F5F5F5] uppercase tracking-wide flex items-center space-x-2">
            <Target className="w-4 h-4 text-[#7FEA35]" />
            <span>The One Thing To Fix First</span>
          </h2>
        </div>
        {topMistakes.length > 0 ? (
          <div className="space-y-3 pt-1">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="text-sm font-bold text-[#7FEA35] flex items-center space-x-2">
                <span>Priority #1: {topMistakes[0].title}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  {topMistakes[0].phase} Phase
                </span>
              </div>
              {topMistakes[0].timestamp_sec != null && (
                <button
                  onClick={() => handleSeekFrame(findFrameIndex(topMistakes[0].timestamp_sec!))}
                  className="text-xs font-mono text-[#7FEA35] hover:underline cursor-pointer flex items-center space-x-1"
                >
                  <span>Jump to Fault Moment (@ {topMistakes[0].timestamp_sec}s)</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-[#181B1D] p-3 rounded-xl border border-[#303438] space-y-1">
                <div className="font-bold text-slate-200">Why this is your top priority:</div>
                <p className="text-slate-400 leading-relaxed">{topMistakes[0].why_it_matters}</p>
              </div>
              <div className="bg-[#181B1D] p-3 rounded-xl border border-[#7FEA35]/30 space-y-1">
                <div className="font-bold text-[#7FEA35] flex items-center space-x-1.5">
                  <Dumbbell className="w-3.5 h-3.5" />
                  <span>Recommended Correction Drill:</span>
                </div>
                <p className="text-slate-200 leading-relaxed">{topMistakes[0].practical_drill}</p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-300">
            Great execution! No major technical corrections required for this {analysis.shot_type}.
          </p>
        )}
      </div>

      {/* SECTION E: Your score */}
      <div id="section-scores" className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#303438]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-lg bg-emerald-500/15 text-emerald-400 font-mono font-bold text-xs flex items-center justify-center border border-emerald-500/30">E</span>
              <h2 className="text-base font-bold text-[#F5F5F5] uppercase tracking-wide">
                Your Technique Score
              </h2>
            </div>
            <p className="text-xs text-[#A5A9AD] mt-1">
              Calculated strictly from measured kinematic values against ideal ranges for {analysis.shot_type} (no invented numbers).
            </p>
          </div>
          <span className="text-[11px] font-mono text-[#A5A9AD] bg-[#181B1D] px-2.5 py-1 rounded border border-[#303438]">
            Overall & Per-Phase Scores (0–100)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-center">
          {/* Overall Score Dial/Box */}
          <div className="flex items-center space-x-4 bg-[#181B1D] p-4 rounded-xl border border-[#303438]">
            <div
              className={`w-16 h-16 rounded-2xl flex flex-col items-center justify-center font-black border shrink-0 ${
                overallScore != null && overallScore >= 80
                  ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                  : overallScore != null && overallScore >= 65
                  ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                  : overallScore != null
                  ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                  : 'bg-slate-800/50 text-slate-400 border-[#303438]'
              }`}
            >
              <span className="text-2xl font-mono leading-none">{overallScore ?? '—'}</span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#A5A9AD]">/ 100</span>
            </div>
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-[#A5A9AD] font-bold">Overall Rating</div>
              <div className="text-sm font-bold text-white mt-0.5">
                {overallScore == null
                  ? 'Not available'
                  : overallScore >= 85
                  ? 'Textbook Technique'
                  : overallScore >= 70
                  ? 'Solid Baseline'
                  : 'Needs Technical Attention'}
              </div>
              <div className="text-[11px] text-[#A5A9AD] mt-0.5">
                Target: {analysis.shot_type}
              </div>
            </div>
          </div>

          {/* Per-Phase Breakdown Bars */}
          <div className="md:col-span-2 bg-[#181B1D] p-4 rounded-xl border border-[#303438] space-y-2.5">
            <div className="text-xs font-mono uppercase tracking-wider text-[#A5A9AD] font-bold">
              Per-Phase Breakdown
            </div>
            <div className="space-y-2">
              {analysis.phase_scores && Object.keys(analysis.phase_scores).length > 0 ? (
                Object.entries(analysis.phase_scores).map(([phase, score]) => (
                  <div key={phase} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-300 capitalize">{phase.replace('_', ' ')}</span>
                      <span className="text-white font-bold">{score} / 100</span>
                    </div>
                    <div className="h-2 bg-[#111315] rounded-full overflow-hidden border border-[#303438]">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          score >= 80 ? 'bg-[#7FEA35]' : score >= 65 ? 'bg-amber-400' : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, score))}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400">Phase-level technique scores evaluated.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION F: Side-by-side */}
      <div id="section-side-by-side" className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#303438]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-lg bg-purple-500/15 text-purple-400 font-mono font-bold text-xs flex items-center justify-center border border-purple-500/30">F</span>
              <h2 className="text-base font-bold text-[#F5F5F5] uppercase tracking-wide">
                Side-by-Side Video & Reference Analysis
              </h2>
            </div>
            <p className="text-xs text-[#A5A9AD] mt-1">
              Your stroke footage synchronized alongside reference mechanics or annotated pose overlays.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setViewMode('single')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer ${
                viewMode === 'single' ? 'bg-[#7FEA35] text-black font-bold' : 'bg-[#181B1D] text-slate-300'
              }`}
            >
              Single Player
            </button>
            <button
              onClick={() => setViewMode('synced')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer flex items-center space-x-1 ${
                viewMode === 'synced' ? 'bg-[#7FEA35] text-black font-bold' : 'bg-[#181B1D] text-slate-300'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Side-by-Side Synced</span>
            </button>
          </div>
        </div>

        {/* Video Player Display: Single or Synced Side-by-Side */}
        {viewMode === 'single' ? (
          <div className="relative rounded-2xl overflow-hidden bg-black border border-navy-800 shadow-2xl aspect-video flex items-center justify-center group">
            <video
              ref={videoRef}
              src={primaryVideoSource}
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
              className="absolute inset-0 w-full h-full pointer-events-none z-[4]"
            />

            {/* In-Video Live Replay Overlay ONLY when video reaches true end */}
            {hasEnded && (
              <div className="absolute inset-0 bg-navy-950/80 backdrop-blur-sm flex flex-col items-center justify-center space-y-3 z-10 animate-in fade-in duration-200">
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
            {!originalOnly && (
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
            )}
          </div>
        ) : (
          /* Side-by-Side Synced Mode */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Left: Original with Canvas Overlay */}
            <div className="relative rounded-xl overflow-hidden bg-black border border-navy-800 shadow-xl aspect-video flex items-center justify-center">
              <video
                ref={videoRef}
                src={originalVideoUrl}
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
              <canvas
                ref={overlayCanvasRef}
                className="absolute inset-0 w-full h-full pointer-events-none z-[4]"
              />
              <div className="absolute top-2 left-2 bg-navy-950/80 px-2 py-0.5 rounded text-[10px] font-mono text-brand-400 border border-navy-800 pointer-events-none z-[5]">
                Original Video + Canvas Overlay
              </div>
            </div>

            {/* Right: Pre-rendered Annotated Stream OR Reference Text Card if no clip */}
            {annotatedVideoUrl ? (
              <div className="relative rounded-xl overflow-hidden bg-black border border-navy-800 shadow-xl aspect-video flex items-center justify-center">
                <video
                  ref={syncedVideoRef}
                  src={annotatedVideoUrl}
                  className="w-full h-full object-contain"
                  playsInline
                  muted
                />
                <div className="absolute top-2 left-2 bg-navy-950/80 px-2 py-0.5 rounded text-[10px] font-mono text-amber-300 border border-navy-800 pointer-events-none z-[5]">
                  Annotated Stroke Comparison ({analysis.total_frames} Frames)
                </div>
              </div>
            ) : (
              <div className="rounded-xl overflow-hidden bg-[#181B1D] border border-[#303438] p-4 flex flex-col justify-center items-center text-center space-y-3 aspect-video">
                <BookOpen className="w-8 h-8 text-[#7FEA35]" />
                <div className="space-y-2 max-w-md w-full">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    Technique Guidance for {analysis.shot_type}
                  </h4>
                  {learningVideos.length > 0 ? (
                    <div className="text-left w-full">
                      <LearnShotCard videos={learningVideos} />
                    </div>
                  ) : (
                    <p className="text-[11px] text-[#A5A9AD]">
                      Showing text guidance and technique breakdown only.
                    </p>
                  )}
                </div>
                {analysis.how_to_play?.bat_path && (
                  <span className="text-[10px] font-mono text-[#7FEA35] bg-[#111315] px-2.5 py-1 rounded border border-[#303438]">
                    Bat Path: {analysis.how_to_play.bat_path}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Video Player Controls */}
        <div className="bg-[#181B1D] rounded-xl border border-[#303438] p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => stepFrame(-1)}
                className="p-2 rounded-lg bg-[#111315] hover:bg-[#25282c] text-slate-300 border border-[#303438] transition-colors cursor-pointer"
                title="Previous Frame (Left Arrow)"
              >
                <SkipBack className="w-4 h-4" />
              </button>
              <button
                onClick={togglePlay}
                className="p-2.5 rounded-lg bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] font-bold shadow-md transition-all cursor-pointer"
                title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-black" />}
              </button>
              <button
                onClick={() => stepFrame(1)}
                className="p-2 rounded-lg bg-[#111315] hover:bg-[#25282c] text-slate-300 border border-[#303438] transition-colors cursor-pointer"
                title="Next Frame (Right Arrow)"
              >
                <SkipForward className="w-4 h-4" />
              </button>
              <button
                onClick={handleReplay}
                className="p-2 rounded-lg bg-[#111315] hover:bg-[#25282c] text-slate-300 border border-[#303438] transition-colors cursor-pointer"
                title="Replay from Beginning (R)"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {/* Timestamp & Frame Counter */}
            <div className="text-center font-mono text-xs flex flex-wrap items-center justify-center gap-2">
              <div>
                <span className="text-white font-bold">{currentTimeSec.toFixed(2)}s</span>
                <span className="text-slate-500"> / {analysis.duration_sec.toFixed(2)}s</span>
                <span className="text-slate-400 ml-2">
                  (Frame: <strong className="text-white">{currentFrame}</strong> / {analysis.analyzed_frames})
                </span>
              </div>
              <div className="text-[11px] px-2 py-0.5 rounded bg-[#111315] border border-[#303438] text-[#7FEA35]">
                {analysis.fps || 30.0} FPS • Full Length ({analysis.duration_sec.toFixed(2)}s)
              </div>
            </div>

            {/* Playback speed selector */}
            <div className="flex items-center space-x-1 bg-[#111315] p-1 rounded-lg border border-[#303438] text-xs font-mono">
              {[0.25, 0.5, 1.0, 1.5].map((speed) => (
                <button
                  key={speed}
                  onClick={() => handleSpeedChange(speed)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all cursor-pointer ${
                    playbackSpeed === speed ? 'bg-[#181B1D] text-[#7FEA35] font-bold' : 'text-slate-500 hover:text-slate-300'
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
            className="w-full h-1.5 bg-[#111315] rounded-lg appearance-none cursor-pointer accent-[#7FEA35]"
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

      {/* Limitations Disclaimer */}
      <div className="bg-[#111315] border border-[#303438] rounded-xl p-4 text-xs text-slate-500 space-y-2">
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
