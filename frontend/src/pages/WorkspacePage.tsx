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
  Loader2
} from 'lucide-react';
import { AnalysisResult, SessionListItem, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { MetricCard } from '../components/MetricCard';
import { PhaseTimeline } from '../components/PhaseTimeline';
import { CoachingFeedbackList } from '../components/CoachingFeedbackList';
import { RealisticBatterVisualizer, getPoseForShotAndPhase } from '../components/RealisticBatterVisualizer';
import { Batter3DCanvas } from '../components/3d/Batter3DCanvas';

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
  const [showIdealGhost, setShowIdealGhost] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'single' | 'synced'>('single');
  const [singleSource, setSingleSource] = useState<'original' | 'annotated'>('original');
  const [show3DComparison, setShow3DComparison] = useState<boolean>(false);
  const [comparisonType, setComparisonType] = useState<'3d' | 'blueprint'>('3d');
  const [activeMistakeJoint, setActiveMistakeJoint] = useState<string | null>(null);
  const [hasEnded, setHasEnded] = useState<boolean>(false);
  const [isSwitchingStriker, setIsSwitchingStriker] = useState<boolean>(false);

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

    if (showIdealGhost && isImpact) {
      try {
        const idealPose = getPoseForShotAndPhase(analysis.shot_type, 4, 'side', analysis.handedness as any);
        if (idealPose) {
          const hipL = lms[23];
          const hipR = lms[24];
          const batterHipX = hipL && hipR ? (toX(hipL.x) + toX(hipR.x)) / 2 : cw / 2;
          const batterHipY = hipL && hipR ? (toY(hipL.y) + toY(hipR.y)) / 2 : ch / 2;
          const scale = renderH * 0.45;

          const gToX = (pt: [number, number]) => batterHipX + pt[0] * scale;
          const gToY = (pt: [number, number]) => batterHipY + pt[1] * scale;

          ctx.save();
          ctx.setLineDash([5, 4]);
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.75)';

          const ghostConnections: [ [number, number], [number, number] ][] = [
            [idealPose.chest, idealPose.neck],
            [idealPose.neck, idealPose.head],
            [idealPose.leadShoulder, idealPose.leadElbow],
            [idealPose.leadElbow, idealPose.leadWrist],
            [idealPose.rearShoulder, idealPose.rearElbow],
            [idealPose.rearElbow, idealPose.rearWrist],
            [idealPose.leadHip, idealPose.leadKnee],
            [idealPose.leadKnee, idealPose.leadAnkle],
            [idealPose.rearHip, idealPose.rearKnee],
            [idealPose.rearKnee, idealPose.rearAnkle],
            [idealPose.batHandle, idealPose.batTip]
          ];

          ghostConnections.forEach(([p1, p2]) => {
            ctx.beginPath();
            ctx.moveTo(gToX(p1), gToY(p1));
            ctx.lineTo(gToX(p2), gToY(p2));
            ctx.stroke();
          });

          ctx.restore();
        }
      } catch (e) {
        // Fallback
      }
    }

    ctx.restore();
  }, [analysis, findFrameIndex, getMetricVerdict, showSkeletonOverlay, showAngles, originalOnly, showIdealGhost, singleSource]);

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
      {/* Top Session Breadcrumb Bar with Calibrated Shot Confidence Headline */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 pb-4 border-b border-[#303438]">
        <div className="space-y-2 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            {confLevelCode === 'cant_tell' ? (
              <h1 className="text-xl sm:text-2xl font-black text-slate-300 tracking-tight">
                Shot: <span className="text-slate-400">Can't tell</span>{' '}
                <span className="text-sm font-semibold text-[#A5A9AD]">({confPct}%)</span>
              </h1>
            ) : (
              <h1 className="text-xl sm:text-2xl font-black text-[#F5F5F5] tracking-tight">
                {analysis?.predicted_shot_type || analysis?.shot_type}:{' '}
                <span className={confColor}>{confLevel}</span>{' '}
                <span className="text-sm font-semibold text-[#A5A9AD]">({confPct}%)</span>
              </h1>
            )}

            <span className={`text-xs font-mono px-2 py-0.5 rounded border font-bold ${confBadgeClass}`}>
              {confLevel}
            </span>

            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-bold">
              {analysis?.session_id}
            </span>
          </div>

          {/* Calibrated Shot Confidence Bar */}
          <div className="flex items-center space-x-3 max-w-md pt-0.5">
            <div className="flex-1 h-2 bg-[#181B1D] rounded-full overflow-hidden border border-[#303438]">
              <div
                className={`h-full rounded-full transition-all duration-500 ${confBarBg}`}
                style={{ width: `${Math.min(100, Math.max(8, confPct))}%` }}
              />
            </div>
            <button
              onClick={() => setShowWhyConfidence(!showWhyConfidence)}
              className="text-[11px] font-mono text-[#A5A9AD] hover:text-[#7FEA35] transition-colors cursor-pointer flex items-center space-x-1"
            >
              <span>Why this confidence?</span>
              <span className="text-[10px]">{showWhyConfidence ? '▲' : '▼'}</span>
            </button>
          </div>

          {/* Why this confidence accordion */}
          {showWhyConfidence && (
            <div className="p-3 bg-[#111315] rounded-xl border border-[#303438] max-w-lg space-y-1 text-xs text-[#A5A9AD]">
              <div className="text-[11px] font-bold text-white mb-1">Confidence Breakdown:</div>
              {confidenceReasons.map((r, i) => (
                <div key={i} className="flex items-start space-x-2">
                  <span className="text-[#7FEA35] font-bold">•</span>
                  <span>{r}</span>
                </div>
              ))}
            </div>
          )}

          {/* Top-3 Candidates Pill Buttons */}
          {candidatePills.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] text-[#A5A9AD] font-semibold mr-1">Candidates:</span>
              {candidatePills.slice(0, 3).map((cand) => (
                <button
                  key={cand.shot}
                  onClick={() => handleConfirmShot(cand.shot)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center space-x-1.5 ${
                    (analysis?.predicted_shot_type || analysis?.shot_type) === cand.shot
                      ? 'bg-[#7FEA35]/20 text-[#7FEA35] border-[#7FEA35]/50'
                      : 'bg-[#181B1D] text-[#A5A9AD] border-[#303438] hover:text-white hover:border-[#7FEA35]'
                  }`}
                  title={`Switch technique analysis to ${cand.shot}`}
                >
                  <span>{cand.shot}</span>
                  <span className="text-[10px] font-mono opacity-80">{cand.pct}%</span>
                </button>
              ))}
            </div>
          )}

          <p className="text-xs text-[#A5A9AD] pt-1">
            Technique Benchmark:{' '}
            <span className="text-white font-bold">{analysis?.shot_type}</span> • Video:{' '}
            <span className="text-[#F5F5F5] font-medium">{analysis?.video_filename}</span> •{' '}
            {analysis?.handedness}-Handed • {analysis?.camera_angle} • {analysis?.duration_sec}s
          </p>
        </div>

        {/* Shot Selection Switcher Dropdown */}
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

      {/* Honest Discrepancy Notice Banner */}
      {analysis.shot_mismatch_warning && (
        <div className="p-3.5 rounded-xl bg-amber-950/70 border border-amber-600/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-md">
          <div className="flex items-center space-x-2 text-amber-200">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <div className="font-bold text-amber-300 text-sm">{analysis.shot_mismatch_warning}</div>
              <div className="text-[11px] text-amber-200/80">
                Technique comparison is currently scored against the detected stroke ({analysis.shot_type}).
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            {analysis.user_selected_shot && analysis.user_selected_shot !== analysis.shot_type && (
              <button
                onClick={() => handleReanalyzeAsSelected(analysis.user_selected_shot!)}
                disabled={isConfirmingShot}
                className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold transition-colors cursor-pointer shadow"
              >
                Re-analyse as {analysis.user_selected_shot}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Striker Isolation & Manual Override */}
      {analysis.striker_isolation_evidence && (
        <div className="p-4 rounded-xl bg-[#111315] border border-[#303438] space-y-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <span className={`w-2.5 h-2.5 rounded-full ${
                (analysis.striker_isolation_evidence.confidence ?? 0.85) < 0.40
                  ? 'bg-amber-400 animate-ping'
                  : 'bg-[#7FEA35] animate-pulse'
              }`}></span>
              <span className="font-bold text-white text-sm">
                Striker: Track #{analysis.striker_track_id ?? analysis.striker_isolation_evidence.active_striker_id}{' '}
                <span className="font-normal text-xs text-[#A5A9AD]">
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

          {(analysis.striker_isolation_evidence.confidence ?? 0.85) < 0.40 ? (
            <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-600/50 text-amber-200 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>No clear striker detected — please select the batter manually from the candidates below.</span>
            </div>
          ) : (
            <p className="text-[11px] text-[#A5A9AD]">
              Bowler and non-strikers are excluded from kinematic analysis. Skeleton tracking is locked onto Track #{analysis.striker_track_id ?? analysis.striker_isolation_evidence.active_striker_id}.
            </p>
          )}

          {/* Candidate Tracks Override Buttons */}
          {((analysis.striker_candidates && analysis.striker_candidates.length > 1) ||
            (analysis.striker_isolation_evidence.all_tracks && Object.keys(analysis.striker_isolation_evidence.all_tracks).length > 1)) && (
            <div className="space-y-1.5 pt-1 border-t border-[#303438]/60">
              <span className="text-[11px] font-medium text-[#A5A9AD] block">
                Detected People in Frame (Click a person to lock tracking onto them):
              </span>
              <div className="flex flex-wrap gap-2">
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
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer flex items-center space-x-1.5 ${
                        isActive
                          ? 'bg-[#7FEA35]/15 border-2 border-[#7FEA35] text-[#7FEA35] font-bold shadow'
                          : 'bg-[#181B1D] border border-[#303438] text-[#F5F5F5] hover:border-[#7FEA35]/60 hover:text-white'
                      }`}
                    >
                      <span>
                        Person #{cand.track_id} ({cand.role.toUpperCase()})
                      </span>
                      {isActive ? (
                        <span className="text-[10px] px-1 py-0.2 rounded bg-[#7FEA35] text-black font-bold">LOCKED</span>
                      ) : (
                        <span className="text-[10px] text-[#A5A9AD]">Select</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {analysis.striker_selection_reason && (
            <p className="text-xs text-[#7FEA35] bg-[#7FEA35]/10 p-2.5 rounded-lg border border-[#7FEA35]/25">
              {analysis.striker_selection_reason}
            </p>
          )}

          {/* Biomechanical Cues Snapshot */}
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono pt-1">
            <span className="px-2 py-0.5 rounded bg-[#181B1D] text-slate-300 border border-[#303438]">
              Bat In Hand: {analysis.striker_isolation_evidence.cues?.cue1_bat_in_hand != null ? `${Math.round(analysis.striker_isolation_evidence.cues.cue1_bat_in_hand * 100)}%` : 'Verified'}
            </span>
            <span className="px-2 py-0.5 rounded bg-[#181B1D] text-slate-300 border border-[#303438]">
              Crease Anchor: {analysis.striker_isolation_evidence.cues?.cue2_position_crease != null ? `${Math.round(analysis.striker_isolation_evidence.cues.cue2_position_crease * 100)}%` : 'Stable'}
            </span>
            <span className="px-2 py-0.5 rounded bg-[#181B1D] text-slate-300 border border-[#303438]">
              Rotational Swing: {analysis.striker_isolation_evidence.cues?.cue3_motion_signature != null ? `${Math.round(analysis.striker_isolation_evidence.cues.cue3_motion_signature * 100)}%` : 'True'}
            </span>
            <span className="px-2 py-0.5 rounded bg-[#181B1D] text-slate-300 border border-[#303438]">
              Batting Stance: {analysis.striker_isolation_evidence.cues?.cue4_batting_stance != null ? `${Math.round(analysis.striker_isolation_evidence.cues.cue4_batting_stance * 100)}%` : 'Active'}
            </span>
          </div>
        </div>
      )}

      {/* Tracking Dropout Alert */}
      {analysis.tracking_dropout_warning && (
        <div className="p-3.5 rounded-xl bg-orange-950/60 border border-orange-700/60 flex items-center space-x-2 text-xs text-orange-200">
          <ShieldAlert className="w-4 h-4 text-orange-400 shrink-0" />
          <span>{analysis.tracking_dropout_warning}</span>
        </div>
      )}

      {/* Top Candidates Display */}
      {analysis.shot_classification?.top_candidates && analysis.shot_classification.top_candidates.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#111315] border border-[#303438] space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-white flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#7FEA35]" />
              <span>Possible shot matches</span>
            </span>
            <span className="text-[11px] font-mono text-[#A5A9AD]">
              Stage 1 Family: <strong className="text-sky-400">{(analysis.shot_classification as any).family || 'Evaluated'}</strong>
            </span>
          </div>
          {(analysis.shot_classification as any).evidence?.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {(analysis.shot_classification as any).evidence.map((item: string, idx: number) => (
                <span key={idx} className="px-2 py-1 rounded-md bg-[#181B1D] border border-[#303438] text-[10px] text-[#A5A9AD]">{item}</span>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {analysis.shot_classification.top_candidates.slice(0, 3).map((cand, idx) => (
              <div
                key={cand.shot_name}
                className={`p-2.5 rounded-lg border flex items-center justify-between ${
                  idx === 0
                    ? 'bg-[#7FEA35]/10 border-[#7FEA35]/30 text-white'
                    : 'bg-[#181B1D] border-[#303438] text-slate-300'
                }`}
              >
                <div className="space-y-0.5">
                  <div className="text-xs font-bold flex items-center space-x-1.5">
                    <span className="text-[10px] font-mono text-slate-400">#{idx + 1}</span>
                    <span>{cand.shot_name}</span>
                  </div>
                  <div className="w-24 bg-navy-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full ${idx === 0 ? 'bg-[#7FEA35]' : 'bg-sky-400'}`}
                      style={{ width: `${Math.round(cand.score * 100)}%` }}
                    />
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono font-bold text-white">
                    {Math.round(cand.score * 100)}%
                  </span>
                  {idx > 0 && (
                    <button
                      onClick={() => handleConfirmShot(cand.shot_name)}
                      className="block text-[10px] text-sky-400 hover:underline cursor-pointer"
                    >
                      Select
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-black text-[#F5F5F5] uppercase tracking-tight">Coach Technique Score</h2>
                <span
                  className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${
                    overallScore != null && overallScore >= 85
                      ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                      : overallScore != null && overallScore >= 70
                      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                      : overallScore != null
                      ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                      : 'bg-slate-800/50 text-slate-400 border-[#303438]'
                  }`}
                >
                  {overallScore == null
                    ? 'Not available'
                    : overallScore >= 85
                    ? 'Textbook Technique'
                    : overallScore >= 70
                    ? 'Solid Baseline'
                    : 'Needs Technical Attention'}
                </span>
              </div>
              <p className="text-xs text-[#A5A9AD] mt-0.5">
                {overallScore == null
                  ? `No supported reference range is available for ${analysis.shot_type}.`
                  : <>Evaluated against the available biomechanical reference ranges for <strong className="text-[#F5F5F5]">{analysis.shot_type}</strong>.</>}
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
                      setShow3DComparison(true);
                    }}
                    className={`rounded-xl border p-3.5 space-y-2 flex flex-col justify-between cursor-pointer transition-all ${
                      isSelectedFault
                        ? 'bg-[#181B1D] border-[#7FEA35] shadow-[0_0_15px_rgba(127,234,53,0.15)] ring-1 ring-[#7FEA35]'
                        : 'bg-[#181B1D] border-[#303438] hover:border-[#7FEA35]/50 hover:bg-[#1a1e22]'
                    }`}
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
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Side-by-Side 3D Model Comparison View when enabled */}
      {show3DComparison && (
        <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-3 animate-in fade-in duration-150">
          <div className="flex flex-wrap items-center justify-between pb-2 border-b border-[#303438] gap-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[#7FEA35] font-bold flex items-center space-x-2">
              <Sparkles className="w-4 h-4" />
              <span>Side-by-Side Technique Comparison: Player vs Ideal Benchmark Ghost</span>
            </h3>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono text-[#A5A9AD] mr-2">
                Phase: <strong className="text-white">{currentPhase}</strong>
              </span>
              <button
                onClick={() => setComparisonType('3d')}
                className={`px-2.5 py-1 text-[10px] font-mono font-bold rounded-lg transition-colors cursor-pointer ${
                  comparisonType === '3d'
                    ? 'bg-[#7FEA35] text-[#050505]'
                    : 'bg-[#181B1D] text-[#A5A9AD] hover:text-white'
                }`}
              >
                3D Forward Kinematics
              </button>
              <button
                onClick={() => setComparisonType('blueprint')}
                className={`px-2.5 py-1 text-[10px] font-mono font-bold rounded-lg transition-colors cursor-pointer ${
                  comparisonType === 'blueprint'
                    ? 'bg-[#00f0ff] text-[#050505]'
                    : 'bg-[#181B1D] text-[#A5A9AD] hover:text-white'
                }`}
              >
                2D Blueprint
              </button>
            </div>
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
              <div className="text-xs font-mono text-[#7FEA35] font-bold">
                2. Ideal Benchmark ({analysis.shot_type})
                {activeMistakeJoint && (
                  <span className="ml-2 text-rose-400 font-normal">
                    · Joint cue: {activeMistakeJoint}
                  </span>
                )}
              </div>
              <div className="rounded-xl overflow-hidden border border-[#303438] aspect-video bg-[#0d0f11]">
                {comparisonType === '3d' ? (
                  <Batter3DCanvas
                    shotName={analysis.shot_type}
                    isGhost={true}
                    ghostColor="#00f0ff"
                    highlightJoint={activeMistakeJoint}
                    showControls={false}
                    showPhaseScrubber={false}
                    showCameraPresets={true}
                    autoOrbitDefault={false}
                    height="100%"
                  />
                ) : (
                  <RealisticBatterVisualizer
                    shotName={analysis.shot_type}
                    initialPhaseIndex={getPhaseIndex(currentPhase)}
                    handedness={analysis.handedness as any}
                    cameraView={analysis.detected_camera_view || 'side'}
                    showControls={false}
                    className="w-full h-full"
                  />
                )}
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
          {/* Top Video Toolbar: View Mode & Overlay Toggles */}
          <div className="bg-[#111315] border border-[#303438] rounded-xl px-3.5 py-2 flex flex-wrap items-center justify-between gap-2 shadow-sm text-xs">
            {/* View Mode & Video Source Switcher */}
            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => setViewMode('single')}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  viewMode === 'single'
                    ? 'bg-[#7FEA35] text-[#050505] font-bold shadow-sm'
                    : 'text-[#A5A9AD] hover:text-[#F5F5F5] bg-[#181B1D]'
                }`}
                title="Single Player with Dynamic Canvas Overlay"
              >
                Single Player
              </button>
              <button
                onClick={() => setViewMode('synced')}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center space-x-1 ${
                  viewMode === 'synced'
                    ? 'bg-[#7FEA35] text-[#050505] font-bold shadow-sm'
                    : 'text-[#A5A9AD] hover:text-[#F5F5F5] bg-[#181B1D]'
                }`}
                title="Synchronized Side-by-Side: Original with Overlay vs Annotated"
              >
                <Columns className="w-3.5 h-3.5" />
                <span>Side-by-Side Synced</span>
              </button>

              {viewMode === 'single' && (
                <div className="ml-2 pl-2 border-l border-[#303438] flex items-center space-x-1">
                  <button
                    onClick={() => { setSingleSource('original'); setOriginalOnly(false); }}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all cursor-pointer ${
                      singleSource === 'original' && !originalOnly
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold'
                        : 'text-[#A5A9AD] hover:text-white'
                    }`}
                  >
                    Original + Overlay
                  </button>
                  {annotatedVideoUrl && (
                    <button
                      onClick={() => setSingleSource('annotated')}
                      className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all cursor-pointer ${
                        singleSource === 'annotated'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
                          : 'text-[#A5A9AD] hover:text-white'
                      }`}
                    >
                      Annotated MP4
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Overlays and Visual Guides Toggles */}
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                onClick={() => {
                  setOriginalOnly(!originalOnly);
                  if (!originalOnly) {
                    setShowSkeletonOverlay(false);
                    setShowAngles(false);
                    setShowIdealGhost(false);
                  } else {
                    setShowSkeletonOverlay(true);
                    setShowAngles(true);
                  }
                }}
                className={`px-2 py-1 rounded-md text-[11px] font-mono border transition-all cursor-pointer ${
                  originalOnly
                    ? 'bg-[#7FEA35] text-[#050505] border-[#7FEA35] font-bold'
                    : 'bg-[#181B1D] text-[#A5A9AD] border-[#303438] hover:text-white'
                }`}
                title="Toggle Original Video Only (No Overlays)"
              >
                Original Only
              </button>

              {!originalOnly && (
                <>
                  <button
                    onClick={() => setShowSkeletonOverlay(!showSkeletonOverlay)}
                    className={`px-2 py-1 rounded-md text-[11px] font-mono border transition-all cursor-pointer ${
                      showSkeletonOverlay
                        ? 'bg-brand-500/20 text-brand-400 border-brand-500/40 font-bold'
                        : 'bg-[#181B1D] text-[#A5A9AD] border-[#303438] hover:text-white'
                    }`}
                    title="Toggle Striker Skeleton Lines"
                  >
                    Skeleton: {showSkeletonOverlay ? 'ON' : 'OFF'}
                  </button>

                  <button
                    onClick={() => setShowAngles(!showAngles)}
                    className={`px-2 py-1 rounded-md text-[11px] font-mono border transition-all cursor-pointer ${
                      showAngles
                        ? 'bg-sky-500/20 text-sky-400 border-sky-500/40 font-bold'
                        : 'bg-[#181B1D] text-[#A5A9AD] border-[#303438] hover:text-white'
                    }`}
                    title="Toggle Joint Angle Arcs & Readings"
                  >
                    Angles: {showAngles ? 'ON' : 'OFF'}
                  </button>

                  <button
                    onClick={() => setShowIdealGhost(!showIdealGhost)}
                    className={`px-2 py-1 rounded-md text-[11px] font-mono border transition-all cursor-pointer flex items-center space-x-1 ${
                      showIdealGhost
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 font-bold'
                        : 'bg-[#181B1D] text-[#A5A9AD] border-[#303438] hover:text-white'
                    }`}
                    title="Show Ideal Reference Pose Wireframe Ghost at Impact"
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>Ghost Pose</span>
                  </button>
                </>
              )}
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

              {/* Right: Pre-rendered Annotated Stream */}
              <div className="relative rounded-xl overflow-hidden bg-black border border-navy-800 shadow-xl aspect-video flex items-center justify-center">
                <video
                  ref={syncedVideoRef}
                  src={annotatedVideoUrl || originalVideoUrl}
                  className="w-full h-full object-contain"
                  playsInline
                  muted
                />
                <div className="absolute top-2 left-2 bg-navy-950/80 px-2 py-0.5 rounded text-[10px] font-mono text-amber-300 border border-navy-800 pointer-events-none z-[5]">
                  Pre-rendered Video ({analysis.total_frames} Frames)
                </div>
              </div>
            </div>
          )}

          {/* Interactive Player Controls */}
          <div className="bg-navy-900/90 rounded-xl border border-navy-800 p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => stepFrame(-1)}
                  className="p-2 rounded-lg bg-navy-950 hover:bg-navy-800 text-slate-300 border border-navy-800 transition-colors cursor-pointer"
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
                  className="p-2 rounded-lg bg-navy-950 hover:bg-navy-800 text-slate-300 border border-navy-800 transition-colors cursor-pointer"
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

              {/* Timestamp, Frame Counter & Source Verification Details */}
              <div className="text-center font-mono text-xs flex flex-wrap items-center justify-center gap-2">
                <div>
                  <span className="text-white font-bold">{currentTimeSec.toFixed(2)}s</span>
                  <span className="text-slate-500"> / {analysis.duration_sec.toFixed(2)}s</span>
                  <span className="text-slate-400 ml-2">
                    (Frame: <strong className="text-white">{currentFrame}</strong> / {analysis.analyzed_frames})
                  </span>
                </div>
                <div className="text-[11px] px-2 py-0.5 rounded bg-navy-950 border border-navy-800 text-brand-400">
                  {analysis.fps || 30.0} FPS • Full Length ({analysis.duration_sec.toFixed(2)}s)
                </div>
              </div>

              {/* Playback speed selector: 0.25x, 0.5x, 1.0x (default), 1.5x */}
              <div className="flex items-center space-x-1 bg-navy-950 p-1 rounded-lg border border-navy-800 text-xs font-mono">
                {[0.25, 0.5, 1.0, 1.5].map((speed) => (
                  <button
                    key={speed}
                    onClick={() => handleSpeedChange(speed)}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all cursor-pointer ${
                      playbackSpeed === speed ? 'bg-navy-800 text-brand-400 font-bold' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>

            {/* Frame Scrubber Slider across full video duration */}
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
          plainSummary={analysis.plain_summary}
          issueCards={analysis.issue_cards}
          coachingPaused={analysis.coaching_paused}
          pauseReason={analysis.pause_reason}
          onSelectCandidateShot={handleConfirmShot}
          topCandidates={candidatePills}
          onSeekToFrame={handleSeekFrame}
          onLanguageChange={handleLanguageChange}
          currentLang={currentLang}
          techniqueScore={analysis.overall_technique_score}
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
