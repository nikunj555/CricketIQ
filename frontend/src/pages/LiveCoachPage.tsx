import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  Video,
  Play,
  Pause,
  Square,
  RefreshCw,
  ArrowRight,
  Sparkles,
  Activity,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Dumbbell,
  Clock,
  Layers,
  ChevronRight,
  RotateCcw,
  Sliders,
  Scale,
  Eye,
  Check,
  X,
  UploadCloud,
  Film
} from 'lucide-react';
import { api } from '../services/api';
import { LivePoseState, LiveAttemptFeedback, CricketShot, AnalysisResult, NavTab } from '../types/cricket';
import { Batter3DCanvas } from '../components/3d/Batter3DCanvas';
import { getShotTechnique } from '../data/shotTechnique';

interface LiveCoachPageProps {
  onSelectTab: (tab: NavTab) => void;
  onSelectSession: (sessionId: string) => void;
  initialTargetShot?: string;
}

export const LiveCoachPage: React.FC<LiveCoachPageProps> = ({
  onSelectTab,
  onSelectSession,
  initialTargetShot,
}) => {
  // Session State
  const [practiceSessionId] = useState<string>(() => `live_sess_${Date.now().toString().slice(-6)}`);
  const [attemptCount, setAttemptCount] = useState<number>(0);
  const [recentAttempts, setRecentAttempts] = useState<LiveAttemptFeedback[]>([]);
  const [currentFeedback, setCurrentFeedback] = useState<LiveAttemptFeedback | null>(null);

  // Camera & Stream State
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [cameraConnecting, setCameraConnecting] = useState<boolean>(false);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('user');
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [isSimulation, setIsSimulation] = useState<boolean>(false);
  const [handedness, setHandedness] = useState<string>('Right');
  const [targetShot, setTargetShot] = useState<string>(initialTargetShot || 'Cover Drive');
  const [availableShots, setAvailableShots] = useState<CricketShot[]>([]);
  const [showReferenceCoach, setShowReferenceCoach] = useState<boolean>(true);

  // Recording State Machine (Idle -> Countdown -> Recording -> Reviewing -> Analyzing)
  const [recordingState, setRecordingState] = useState<'idle' | 'countdown' | 'recording' | 'reviewing' | 'analyzing'>('idle');
  const [countdownNum, setCountdownNum] = useState<number>(3);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedVideoUrl, setRecordedVideoUrl] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<{ step: string; percent: number } | null>(null);

  // Real-time Pose & State Machine
  const [poseState, setPoseState] = useState<LivePoseState | null>(null);
  const [fps, setFps] = useState<number>(0);
  const [liveLatency, setLiveLatency] = useState<number>(0);
  const [backendStatus, setBackendStatus] = useState<'connected' | 'checking' | 'error'>('checking');

  // Refs
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const reviewVideoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameIntervalRef = useRef<any>(null);
  const lastFrameTimeRef = useRef<number>(Date.now());
  const isProcessingRef = useRef<boolean>(false);
  const attemptFramesBufferRef = useRef<any[]>([]);

  // MediaRecorder Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<any>(null);
  const countdownTimerRef = useRef<any>(null);

  useEffect(() => {
    if (initialTargetShot) {
      setTargetShot(initialTargetShot);
    }
  }, [initialTargetShot]);

  useEffect(() => {
    api.getShots().then((res) => {
      setAvailableShots(res.shots);
    }).catch(() => {});
  }, []);

  // Enumerate video devices
  const updateDeviceList = async () => {
    try {
      if (navigator.mediaDevices?.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevs = devices.filter((d) => d.kind === 'videoinput');
        setAvailableDevices(videoDevs);
      }
    } catch (err) {
      console.warn('Unable to enumerate video devices:', err);
    }
  };

  // Start Camera with resilient 3-tier constraint fallback
  const startCamera = async (deviceIdToUse?: string) => {
    setIsSimulation(false);
    setCameraConnecting(true);
    setCameraError(null);

    // Stop previous stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraConnecting(false);
      setCameraActive(false);
      setCameraError(
        'Camera API is not supported in this browser context. Please use Chrome, Edge, Safari, or Firefox on HTTPS or http://localhost:5173.'
      );
      return;
    }

    const devId = deviceIdToUse || selectedDeviceId;
    let stream: MediaStream | null = null;

    try {
      const constraints: MediaStreamConstraints = {
        video: devId
          ? { deviceId: { exact: devId }, width: { ideal: 640 }, height: { ideal: 480 } }
          : { facingMode: facingMode, width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      };
      stream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (tier1Err: any) {
      console.warn('Tier 1 camera constraints failed, attempting fallback...', tier1Err);
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        });
      } catch (tier2Err: any) {
        console.warn('Tier 2 camera constraints failed, attempting basic fallback...', tier2Err);
        try {
          stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        } catch (tier3Err: any) {
          console.error('All camera constraint tiers failed:', tier3Err);
          setCameraConnecting(false);
          setCameraActive(false);
          let msg = tier3Err.message || 'Unable to connect to camera device';
          if (tier3Err.name === 'NotAllowedError' || tier3Err.name === 'PermissionDeniedError') {
            msg = 'Camera permission denied. Please allow camera permissions in your browser address bar.';
          } else if (tier3Err.name === 'NotReadableError' || tier3Err.name === 'TrackStartError') {
            msg = 'Camera is currently in use by another app (e.g. Zoom, Teams, OBS, or another tab). Please close other apps and retry.';
          } else if (tier3Err.name === 'NotFoundError' || tier3Err.name === 'DevicesNotFoundError') {
            msg = 'No camera found on this device. You can click "Simulate Practice Feed" below to test the AI coach.';
          }
          setCameraError(msg);
          return;
        }
      }
    }

    if (!stream) {
      setCameraConnecting(false);
      setCameraActive(false);
      setCameraError('No video stream received from camera.');
      return;
    }

    streamRef.current = stream;

    if (videoRef.current) {
      const video = videoRef.current;
      video.srcObject = stream;
      video.setAttribute('playsinline', 'true');
      video.setAttribute('autoplay', 'true');
      video.setAttribute('muted', 'true');
      video.defaultMuted = true;
      video.muted = true;
      try {
        await video.play();
      } catch (playErr) {
        console.warn('Autoplay error:', playErr);
      }
    }

    setCameraActive(true);
    setCameraConnecting(false);
    setCameraError(null);
    updateDeviceList();
  };

  // Start Simulated Practice Feed (fallback if user has no webcam)
  const startSimulation = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraError(null);
    setIsSimulation(true);
    if (videoRef.current) {
      const video = videoRef.current;
      video.srcObject = null;
      const shotFileMap: Record<string, string> = {
        'Cover Drive': 'real_cricketer_cover_drive.mp4',
        'Straight Drive': 'sample_straight_drive.mp4',
        'On Drive': 'sample_on_drive.mp4',
        'Off Drive': 'sample_off_drive.mp4',
        'Lofted Drive': 'sample_lofted_drive.mp4',
        'Forward Defensive': 'real_cricketer_forward_defensive.mp4',
        'Back-foot Defensive': 'sample_back_foot_defensive.mp4',
        'Back-foot Punch': 'sample_back_foot_punch.mp4',
        'Square Cut': 'sample_square_cut.mp4',
        'Late Cut': 'sample_late_cut.mp4',
        'Upper Cut': 'sample_upper_cut.mp4',
        'Pull Shot': 'real_gilchrist_pull.mp4',
        'Hook Shot': 'sample_hook_shot.mp4',
        'Flick Shot': 'sample_flick_shot.mp4',
        'Leg Glance': 'sample_leg_glance.mp4',
        'Clip Shot': 'sample_clip_shot.mp4',
        'Sweep': 'sample_sweep.mp4',
        'Slog Sweep': 'sample_slog_sweep.mp4',
        'Reverse Sweep': 'sample_reverse_sweep.mp4',
        'Paddle Sweep': 'sample_paddle_sweep.mp4',
        'Slog': 'sample_slog.mp4',
        'Switch Hit': 'sample_switch_hit.mp4',
        'Scoop Shot': 'sample_scoop_shot.mp4',
        'Ramp Shot': 'sample_ramp_shot.mp4',
        'Helicopter Shot': 'sample_helicopter_shot.mp4',
      };
      const filename = shotFileMap[targetShot] || 'real_cricketer_cover_drive.mp4';
      video.src = api.getVideoUrl(`/api/video/original/${filename}`);
      video.loop = true;
      video.setAttribute('playsinline', 'true');
      video.setAttribute('autoplay', 'true');
      video.setAttribute('muted', 'true');
      video.defaultMuted = true;
      video.muted = true;
      video.play().catch((e) => console.warn('Simulation play failed:', e));
    }
    setCameraActive(true);
    setCameraConnecting(false);
  };

  // Stop Camera / Feed
  const stopCamera = () => {
    if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.src = '';
    }
    setCameraActive(false);
    setIsSimulation(false);
    setPoseState(null);
  };

  useEffect(() => {
    updateDeviceList();
    startCamera();
    return () => {
      stopCamera();
    };
  }, [facingMode]);

  // Frame Capture & Processing Loop (Sampled at ~12 FPS for ultra-responsive local CPU inference)
  const processFrame = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !cameraActive || isProcessingRef.current) {
      return;
    }

    const video = videoRef.current;
    if (video.readyState < 2) return;

    isProcessingRef.current = true;
    const now = Date.now();
    const delta = now - lastFrameTimeRef.current;
    if (delta > 0) setFps(Math.round(1000 / delta));
    lastFrameTimeRef.current = now;

    try {
      if (!captureCanvasRef.current) {
        captureCanvasRef.current = document.createElement('canvas');
        captureCanvasRef.current.width = 320;
        captureCanvasRef.current.height = 240;
      }
      const c = captureCanvasRef.current;
      const ctx = c.getContext('2d');
      if (!ctx) {
        isProcessingRef.current = false;
        return;
      }

      ctx.drawImage(video, 0, 0, c.width, c.height);
      const b64 = c.toDataURL('image/jpeg', 0.65);

      // Call backend live frame processing
      const stateRes = await api.processLiveFrame({
        image_base64: b64,
        timestamp_ms: now,
        session_id: practiceSessionId,
        handedness: handedness,
        shot_hint: targetShot,
        manual_trigger: recordingState === 'recording' ? 'start' : null,
      });

      setBackendStatus('connected');
      setPoseState(stateRes);
      setLiveLatency(stateRes.latency_ms);

      // Render skeleton on the overlay canvas
      renderSkeletonOverlay(stateRes);

      // Accumulate attempt telemetry
      if (stateRes.state === 'shot_in_progress') {
        attemptFramesBufferRef.current.push({
          frame_index: attemptFramesBufferRef.current.length,
          timestamp_sec: Number(((now % 100000) / 1000).toFixed(2)),
          pose_detected: true,
          confidence: stateRes.presence.confidence,
          lead_knee_angle: stateRes.current_lead_knee,
          rear_knee_angle: stateRes.current_rear_knee,
          torso_inclination: stateRes.current_torso_lean,
          head_displacement: stateRes.current_head_disp,
          stance_width_norm: 1.4,
          phase: 'Downswing / Execution',
        });
      }

      // If in recording mode and shot is detected as completed, automatically stop recording!
      if (recordingState === 'recording' && stateRes.state === 'shot_completed') {
        setTimeout(() => {
          stopRecording();
        }, 800);
      }
    } catch (err) {
      setBackendStatus('error');
    } finally {
      isProcessingRef.current = false;
    }
  }, [cameraActive, practiceSessionId, handedness, targetShot, recordingState]);

  // Frame processing timer (~10-12 FPS)
  useEffect(() => {
    if (cameraActive && (recordingState === 'idle' || recordingState === 'recording')) {
      frameIntervalRef.current = setInterval(processFrame, 85);
    } else {
      if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    }
    return () => {
      if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    };
  }, [cameraActive, recordingState, processFrame]);

  // Render Skeleton Overlay on Live Canvas
  const renderSkeletonOverlay = (state: LivePoseState) => {
    const canvas = canvasRef.current;
    if (!canvas || !videoRef.current) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const lms = state.landmarks_normalized;
    if (!lms || lms.length < 33 || !state.presence.detected) {
      return;
    }

    const w = canvas.width;
    const h = canvas.height;

    // Draw Skeleton Connections
    const connections = [
      [11, 12], [11, 23], [12, 24], [23, 24], // Torso
      [11, 13], [13, 15], [12, 14], [14, 16], // Arms
      [23, 25], [25, 27], [24, 26], [26, 28]  // Legs
    ];

    ctx.lineWidth = 3;
    connections.forEach(([i, j]) => {
      const p1 = lms[i];
      const p2 = lms[j];
      if (p1 && p2 && p1.v > 0.4 && p2.v > 0.4) {
        ctx.beginPath();
        ctx.moveTo(p1.x * w, p1.y * h);
        ctx.lineTo(p2.x * w, p2.y * h);
        if (i === 23 || i === 25) {
          ctx.strokeStyle = '#22c55e'; // Lead leg green
        } else if (i === 24 || i === 26) {
          ctx.strokeStyle = '#eab308'; // Rear leg yellow
        } else {
          ctx.strokeStyle = '#38bdf8'; // Blue torso/arms
        }
        ctx.stroke();
      }
    });

    // Draw Joint Dots
    [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28].forEach((idx) => {
      const p = lms[idx];
      if (p && p.v > 0.4) {
        ctx.beginPath();
        ctx.arc(p.x * w, p.y * h, 4, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.strokeStyle = '#0f172a';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });

    // Bat line overlay if bat is detected in live feed
    const batAngle = state.current_bat_angle ?? (state as any).bat_angle_deg;
    if ((state.bat_tracking_active || (state as any).bat_detected || batAngle !== null) && batAngle !== null && batAngle !== undefined) {
      const wristIdx = handedness === 'Left' ? 16 : 15;
      const wrist = lms[wristIdx];
      if (wrist && wrist.v > 0.35) {
        const rad = (batAngle * Math.PI) / 180;
        const batLen = h * 0.28;
        const bx = wrist.x * w + Math.sin(rad) * batLen;
        const by = wrist.y * h + Math.cos(rad) * batLen;
        ctx.beginPath();
        ctx.moveTo(wrist.x * w, wrist.y * h);
        ctx.lineTo(bx, by);
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 5;
        ctx.lineCap = 'round';
        ctx.stroke();
      }
    }
  };

  /* =========================================================================
     TRUE BROWSER MEDIARECORDER RECORDING PIPELINE
     ========================================================================= */

  const initiateRecordingWithCountdown = () => {
    if (!cameraActive) {
      startCamera();
      return;
    }
    setRecordingState('countdown');
    setCountdownNum(3);

    let count = 3;
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    countdownTimerRef.current = setInterval(() => {
      count -= 1;
      if (count > 0) {
        setCountdownNum(count);
      } else {
        clearInterval(countdownTimerRef.current);
        startActualRecording();
      }
    }, 1000);
  };

  const startActualRecording = () => {
    attemptFramesBufferRef.current = [];
    recordedChunksRef.current = [];
    setRecordingSeconds(0);
    setRecordingState('recording');

    // Get stream from video element or streamRef
    let recordStream: MediaStream | null = streamRef.current;
    if (!recordStream && videoRef.current && (videoRef.current as any).captureStream) {
      try {
        recordStream = (videoRef.current as any).captureStream();
      } catch (e) {
        console.warn('captureStream not available:', e);
      }
    }

    if (!recordStream) {
      console.warn('No stream available for MediaRecorder; using direct simulation buffer');
      startSimulatedRecordingTimer();
      return;
    }

    const supportedMime = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm',
      'video/mp4'
    ].find((type) => {
      try {
        return typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type);
      } catch {
        return false;
      }
    }) || '';

    try {
      const options = supportedMime ? { mimeType: supportedMime } : undefined;
      const mediaRecorder = new MediaRecorder(recordStream, options);

      mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mime = supportedMime || 'video/webm';
        const blob = new Blob(recordedChunksRef.current, { type: mime });
        setRecordedBlob(blob);
        const url = URL.createObjectURL(blob);
        setRecordedVideoUrl(url);
        setRecordingState('reviewing');
      };

      mediaRecorder.start(250); // Slice every 250ms
      mediaRecorderRef.current = mediaRecorder;

      // Start elapsed timer
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 12) { // Auto-stop at 12s cap
            stopRecording();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      console.error('MediaRecorder initialization failed:', err);
      startSimulatedRecordingTimer();
    }
  };

  const startSimulatedRecordingTimer = () => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    recordingTimerRef.current = setInterval(() => {
      setRecordingSeconds((prev) => {
        if (prev >= 6) {
          stopRecording();
          return prev;
        }
        return prev + 1;
      });
    }, 1000);
  };

  const stopRecording = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        console.warn('Error stopping MediaRecorder:', e);
      }
    } else {
      // Fallback if no media recorder was created
      setRecordingState('reviewing');
    }
  };

  const handleRetakeAttempt = () => {
    if (recordedVideoUrl) {
      URL.revokeObjectURL(recordedVideoUrl);
    }
    setRecordedBlob(null);
    setRecordedVideoUrl(null);
    setRecordingSeconds(0);
    setRecordingState('idle');
  };

  /* =========================================================================
     END-TO-END AI PRACTICE COACH PIPELINE
     ========================================================================= */

  const submitAttemptForAnalysis = async () => {
    setRecordingState('analyzing');
    setAnalysisProgress({ step: 'Uploading practice recording to AI Engine...', percent: 15 });

    try {
      let uploadFile: Blob | File;
      if (recordedBlob && recordedBlob.size > 1000) {
        uploadFile = new File([recordedBlob], `practice_attempt_${Date.now()}.webm`, {
          type: recordedBlob.type || 'video/webm',
        });
      } else {
        // Fallback for simulation feed or when MediaRecorder is unavailable
        setAnalysisProgress({ step: 'Processing kinematic movement trajectory...', percent: 30 });
        const frames = attemptFramesBufferRef.current.length > 5
          ? attemptFramesBufferRef.current
          : [
              {
                frame_index: 0,
                timestamp_sec: 0.0,
                pose_detected: true,
                confidence: 0.95,
                lead_knee_angle: poseState?.current_lead_knee || 128.0,
                rear_knee_angle: 160.0,
                torso_inclination: poseState?.current_torso_lean || 24.0,
                head_displacement: 0.18,
                stance_width_norm: 1.45,
                phase: 'Impact / Contact Window',
              },
            ];

        const feedback = await api.analyzeLiveAttempt({
          session_id: practiceSessionId,
          attempt_index: attemptCount + 1,
          shot_type: targetShot,
          handedness: handedness,
          camera_angle: 'Side View',
          frames: frames,
        });

        finishAnalysis(feedback);
        return;
      }

      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('shot_type', targetShot);
      formData.append('handedness', handedness);
      formData.append('camera_angle', 'Side View');

      const uploadRes = await api.uploadVideo(formData);
      const newSessionId = uploadRes.session_id;

      // Poll processing status
      let pollCount = 0;
      const pollInterval = setInterval(async () => {
        pollCount += 1;
        try {
          const statusRes = await api.getProcessingStatus(newSessionId);
          setAnalysisProgress({
            step: statusRes.current_step || 'Extracting biomechanical features & DTW alignment...',
            percent: Math.max(30, Math.min(95, statusRes.progress)),
          });

          if (statusRes.status === 'completed' || pollCount > 35) {
            clearInterval(pollInterval);
            const fullAnalysis = await api.getAnalysis(newSessionId);

            // Synthesize grounded attempt feedback from full analysis
            const topObs = fullAnalysis.coaching_feedback?.[0];
            const conf = fullAnalysis.shot_classification?.confidence ?? fullAnalysis.prediction_confidence ?? 0.9;
            const knee = fullAnalysis.summary?.lead_knee_flexion_at_impact ?? 130;
            const elbow = fullAnalysis.summary?.lead_elbow_flexion_at_impact ?? 145;
            const torso = fullAnalysis.summary?.torso_lean_at_impact ?? 25;

            const synthFeedback: LiveAttemptFeedback = {
              attempt_id: `att_${Date.now().toString().slice(-4)}`,
              session_id: practiceSessionId,
              full_session_id: newSessionId,
              shot_type: fullAnalysis.shot_type,
              shot_confidence: conf,
              confidence_score: conf,
              processing_latency_ms: 120,
              main_observation: topObs ? topObs.measurement : `${fullAnalysis.shot_type} executed with solid balance.`,
              observed_metric_name: topObs ? topObs.category : 'Lead Knee Flex',
              observed_value: topObs ? topObs.observed_value : `${knee}°`,
              benchmark_value: topObs ? (topObs.reference_benchmark ?? '120°-135°') : '120°-135°',
              evidence: topObs ? `Measured ${topObs.observed_value} vs benchmark ${topObs.reference_benchmark || 'standard'}` : 'Grounded biomechanical capture',
              why_it_matters: topObs ? topObs.why_it_matters : 'Optimal joint kinematics generate consistent timing.',
              next_action_drill: topObs ? topObs.practical_drill : 'Maintain balance throughout follow-through.',
              impact_lead_knee: knee,
              impact_lead_elbow: elbow,
              impact_torso_lean: torso,
              bat_angle_impact: null,
              previous_attempt_comparison: recentAttempts.length > 0
                ? `Lead knee flex comparison: ${knee}° (current) vs ${recentAttempts[0].impact_lead_knee ?? 130}° (previous).`
                : 'Initial benchmark attempt established for this practice session.',
              created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            };

            finishAnalysis(synthFeedback);
          } else if (statusRes.status === 'failed') {
            clearInterval(pollInterval);
            throw new Error(statusRes.error || 'Video analysis pipeline failed');
          }
        } catch (pollErr) {
          console.warn('Status poll exception:', pollErr);
        }
      }, 750);
    } catch (err: any) {
      console.error('Failed to submit practice attempt:', err);
      // Fallback to instant live attempt analysis
      try {
        const feedback = await api.analyzeLiveAttempt({
          session_id: practiceSessionId,
          attempt_index: attemptCount + 1,
          shot_type: targetShot,
          handedness: handedness,
          camera_angle: 'Side View',
          frames: attemptFramesBufferRef.current.length > 0 ? attemptFramesBufferRef.current : [
            {
              frame_index: 0,
              timestamp_sec: 0.0,
              pose_detected: true,
              confidence: 0.95,
              lead_knee_angle: poseState?.current_lead_knee || 128.0,
              rear_knee_angle: 160.0,
              torso_inclination: poseState?.current_torso_lean || 24.0,
              head_displacement: 0.18,
              stance_width_norm: 1.45,
              phase: 'Impact / Contact Window',
            }
          ],
        });
        finishAnalysis(feedback);
      } catch (fallbackErr) {
        setRecordingState('idle');
      }
    }
  };

  const finishAnalysis = (feedback: LiveAttemptFeedback) => {
    setAttemptCount((prev) => prev + 1);
    setCurrentFeedback(feedback);
    setRecentAttempts((prev) => [feedback, ...prev.slice(0, 4)]);
    setRecordingState('idle');
    setAnalysisProgress(null);
  };

  const handleNextShot = () => {
    setCurrentFeedback(null);
    setRecordedBlob(null);
    if (recordedVideoUrl) URL.revokeObjectURL(recordedVideoUrl);
    setRecordedVideoUrl(null);
    setRecordingSeconds(0);
    setRecordingState('idle');
    attemptFramesBufferRef.current = [];
  };

  // Keyboard shortcut: Spacebar triggers recording or next shot
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        e.preventDefault();
        if (currentFeedback) {
          handleNextShot();
        } else if (recordingState === 'idle') {
          initiateRecordingWithCountdown();
        } else if (recordingState === 'recording') {
          stopRecording();
        } else if (recordingState === 'reviewing') {
          submitAttemptForAnalysis();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentFeedback, recordingState]);

  // Readiness Checklist Indicators
  const isCameraLive = cameraActive && (!!streamRef.current || isSimulation);
  const isFullBodyInFrame = !!(poseState?.presence?.detected && poseState?.presence?.confidence > 0.55);
  const isStanceReady = poseState?.state === 'ready_for_shot';

  const stateTheme = {
    waiting_for_player: {
      color: 'text-amber-400',
      bg: 'bg-[#181B1D] border-amber-500/40',
      pill: 'bg-amber-400',
      title: 'Step Into Frame',
    },
    ready_for_shot: {
      color: 'text-[#7FEA35]',
      bg: 'bg-[#181B1D] border-[#7FEA35]/40',
      pill: 'bg-[#7FEA35] animate-pulse',
      title: 'Ready In Stance — Press Record Or Swing',
    },
    shot_in_progress: {
      color: 'text-rose-400',
      bg: 'bg-[#181B1D] border-rose-500/40',
      pill: 'bg-rose-500 animate-ping',
      title: 'Stroke In Progress — Tracking Kinematics...',
    },
    shot_completed: {
      color: 'text-sky-400',
      bg: 'bg-[#181B1D] border-sky-500/40',
      pill: 'bg-sky-400',
      title: 'Stroke Completed — Ready to Review',
    },
    cooldown: {
      color: 'text-[#7FEA35]',
      bg: 'bg-[#181B1D] border-[#7FEA35]/40',
      pill: 'bg-[#7FEA35]',
      title: 'Technique Feedback Ready',
    },
  }[poseState?.state || 'waiting_for_player'] || {
    color: 'text-[#A5A9AD]',
    bg: 'bg-[#181B1D] border-[#303438]',
    pill: 'bg-slate-400',
    title: 'Camera Initializing...',
  };

  return (
    <div className="max-w-[1550px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
      {/* Top Banner: Mode Indicator & Quick Settings */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-[#303438]">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#7FEA35] animate-pulse shadow-md shadow-[#7FEA35]/50" />
            <h1 className="text-xl sm:text-2xl font-black text-[#F5F5F5] tracking-tight uppercase">
              Live AI Batting Practice Coach
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-bold">
              True Video Mode
            </span>
          </div>
          <p className="text-xs text-[#A5A9AD] mt-0.5">
            Position camera side-on (2.5 - 3.5m). Record your real batting attempt and receive explainable biomechanical feedback.
          </p>
        </div>

        {/* Practice Controls */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {/* Handedness Switcher */}
          <div className="flex items-center space-x-1 bg-[#111315] border border-[#303438] p-1 rounded-lg text-xs font-mono">
            <button
              onClick={() => setHandedness('Right')}
              className={`px-2 py-1 rounded transition-all cursor-pointer ${
                handedness === 'Right' ? 'bg-[#7FEA35] text-[#050505] font-bold' : 'text-[#A5A9AD]'
              }`}
            >
              Right-Hand
            </button>
            <button
              onClick={() => setHandedness('Left')}
              className={`px-2 py-1 rounded transition-all cursor-pointer ${
                handedness === 'Left' ? 'bg-[#7FEA35] text-[#050505] font-bold' : 'text-[#A5A9AD]'
              }`}
            >
              Left-Hand
            </button>
          </div>

          {/* Shot Target Selector */}
          <select
            value={targetShot}
            onChange={(e) => setTargetShot(e.target.value)}
            className="bg-[#111315] border border-[#303438] rounded-lg px-2.5 py-1.5 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#7FEA35] font-medium max-w-[200px]"
            title="Target Batting Shot"
          >
            {availableShots.length > 0 ? (
              Array.from(new Set(availableShots.map((s) => s.category))).map((cat) => (
                <optgroup key={cat} label={cat} className="bg-[#111315] text-[#7FEA35] font-bold">
                  {availableShots
                    .filter((s) => s.category === cat)
                    .map((s) => (
                      <option key={s.id} value={s.name} className="bg-[#181B1D] text-[#F5F5F5] font-normal">
                        Target: {s.name} {s.reference_status === 'available' ? '★' : ''}
                      </option>
                    ))}
                </optgroup>
              ))
            ) : (
              <>
                <option value="Cover Drive">Target: Cover Drive ★</option>
                <option value="Straight Drive">Target: Straight Drive ★</option>
                <option value="Pull Shot">Target: Pull Shot ★</option>
                <option value="Forward Defensive">Target: Forward Defensive ★</option>
                <option value="Square Cut">Target: Square Cut</option>
                <option value="Sweep">Target: Sweep</option>
              </>
            )}
          </select>

          {/* Reference Coach Avatar Toggle */}
          <button
            onClick={() => setShowReferenceCoach((prev) => !prev)}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer ${
              showReferenceCoach
                ? 'bg-[#7FEA35]/15 border-[#7FEA35] text-[#7FEA35]'
                : 'bg-[#111315] hover:bg-[#181B1D] text-[#A5A9AD] border-[#303438]'
            }`}
            title="Toggle Realistic Reference Avatar Split-Screen"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>{showReferenceCoach ? 'Reference Coach: On' : 'Reference Coach: Off'}</span>
          </button>

          {/* Camera Selector Dropdown */}
          {availableDevices.length > 1 && (
            <select
              value={selectedDeviceId}
              onChange={(e) => {
                setSelectedDeviceId(e.target.value);
                startCamera(e.target.value);
              }}
              className="bg-[#111315] border border-[#303438] rounded-lg px-2 py-1.5 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#7FEA35] font-medium max-w-[140px] truncate"
              title="Select Camera Device"
            >
              {availableDevices.map((d, i) => (
                <option key={d.deviceId || i} value={d.deviceId}>
                  {d.label || `Camera ${i + 1}`}
                </option>
              ))}
            </select>
          )}

          {/* Camera Flip */}
          <button
            onClick={() => setFacingMode((m) => (m === 'user' ? 'environment' : 'user'))}
            className="p-1.5 rounded-lg bg-[#111315] hover:bg-[#181B1D] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438] text-xs transition-colors cursor-pointer"
            title="Switch Front / Rear Camera"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Camera Toggle Button */}
          <button
            onClick={() => (cameraActive ? stopCamera() : startCamera())}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer ${
              cameraActive
                ? 'bg-rose-950/70 border-rose-800 text-rose-300 hover:bg-rose-900'
                : 'bg-emerald-950/70 border-emerald-800 text-emerald-300 hover:bg-emerald-900'
            }`}
            title={cameraActive ? 'Turn Off Camera Feed' : 'Turn On Camera Feed'}
          >
            {cameraActive ? <CameraOff className="w-3.5 h-3.5" /> : <Camera className="w-3.5 h-3.5" />}
            <span>{cameraActive ? (isSimulation ? 'Stop Sim' : 'Stop Cam') : 'Start Cam'}</span>
          </button>

          {/* Practice Simulation Mode Toggle */}
          <button
            onClick={isSimulation ? stopCamera : startSimulation}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
              isSimulation
                ? 'bg-[#7FEA35] text-[#050505] font-bold border-[#7FEA35]'
                : 'bg-[#111315] hover:bg-[#181B1D] text-[#A5A9AD] border-[#303438]'
            }`}
            title="Simulate Practice Feed using real cricketer footage"
          >
            {isSimulation ? 'Simulating' : 'Simulate'}
          </button>
        </div>
      </div>

      {/* Camera Guidance & Readiness Checklist */}
      <div className="bg-[#111315] border border-[#303438] rounded-2xl p-3.5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#F5F5F5]">
              Practice Readiness Checklist
            </span>
            <span className="text-[11px] text-[#A5A9AD]">
              (Optimal setup ensures tournament-grade biomechanical accuracy)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
            {/* Checklist Item 1: Camera Connected */}
            <div className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border ${
              isCameraLive ? 'bg-emerald-950/50 border-emerald-800/80 text-emerald-400' : 'bg-[#181B1D] border-[#303438] text-[#A5A9AD]'
            }`}>
              {isCameraLive ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5 text-rose-400" />}
              <span>Camera Active</span>
            </div>

            {/* Checklist Item 2: Full Body in Frame */}
            <div className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border ${
              isFullBodyInFrame ? 'bg-emerald-950/50 border-emerald-800/80 text-emerald-400' : 'bg-[#181B1D] border-[#303438] text-[#A5A9AD]'
            }`}>
              {isFullBodyInFrame ? <Check className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5 text-amber-400" />}
              <span>Full Body Visible</span>
            </div>

            {/* Checklist Item 3: Stance Detected */}
            <div className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border ${
              isStanceReady ? 'bg-emerald-950/50 border-emerald-800/80 text-emerald-400' : 'bg-[#181B1D] border-[#303438] text-[#A5A9AD]'
            }`}>
              {isStanceReady ? <Check className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5 text-amber-400" />}
              <span>Stance Balanced</span>
            </div>

            {/* Checklist Item 4: Angle & Distance */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-[#181B1D] border border-[#303438] text-[#A5A9AD]">
              <span>Angle: Side-On (~90°) • 2.5-3.5m</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main View: Viewfinder / Review Player Split with Reference Avatar */}
      <div className={`grid grid-cols-1 ${showReferenceCoach ? 'xl:grid-cols-12' : 'lg:grid-cols-3'} gap-6`}>
        {/* Left Section: Live Camera or Recorded Video Player */}
        <div className={`${showReferenceCoach ? 'xl:col-span-8' : 'lg:col-span-2'} space-y-3`}>
          <div className="relative rounded-2xl overflow-hidden bg-black border-2 border-[#303438] aspect-[4/3] sm:aspect-video shadow-2xl flex items-center justify-center group">
            {/* If in Review State: Display Real Recorded Video Playback */}
            {recordingState === 'reviewing' && recordedVideoUrl ? (
              <div className="relative w-full h-full bg-black flex items-center justify-center">
                <video
                  ref={reviewVideoRef}
                  src={recordedVideoUrl}
                  controls
                  autoPlay
                  loop
                  playsInline
                  className="w-full h-full object-contain"
                />
                <div className="absolute top-4 left-4 bg-navy-950/90 border border-brand-500/50 px-3 py-1.5 rounded-full text-xs font-mono text-brand-400 flex items-center space-x-2">
                  <Film className="w-3.5 h-3.5" />
                  <span>Reviewing Recorded Attempt ({recordingSeconds}s)</span>
                </div>
              </div>
            ) : (
              /* Otherwise: Live Webcam Feed & Canvas Overlay */
              <>
                <video
                  ref={videoRef}
                  playsInline
                  muted
                  className={`w-full h-full object-contain ${facingMode === 'user' && !isSimulation ? 'transform -scale-x-100' : ''}`}
                />

                <canvas
                  ref={canvasRef}
                  className={`absolute inset-0 w-full h-full pointer-events-none object-contain ${facingMode === 'user' && !isSimulation ? 'transform -scale-x-100' : ''}`}
                />

                {/* Viewfinder Broadcast HUD Corner Brackets */}
                <div className="absolute top-3 left-3 w-5 h-5 border-t-2 border-l-2 border-[#7FEA35]/70 pointer-events-none" />
                <div className="absolute top-3 right-3 w-5 h-5 border-t-2 border-r-2 border-[#7FEA35]/70 pointer-events-none" />
                <div className="absolute bottom-3 left-3 w-5 h-5 border-b-2 border-l-2 border-[#7FEA35]/70 pointer-events-none" />
                <div className="absolute bottom-3 right-3 w-5 h-5 border-b-2 border-r-2 border-[#7FEA35]/70 pointer-events-none" />
              </>
            )}

            {/* Countdown Overlay (3 -> 2 -> 1) */}
            {recordingState === 'countdown' && (
              <div className="absolute inset-0 bg-black/75 backdrop-blur-md flex flex-col items-center justify-center z-30 space-y-4">
                <div className="relative flex items-center justify-center">
                  <div className="w-28 h-28 rounded-full border-2 border-[#7FEA35]/40 animate-ping absolute" />
                  <div className="w-24 h-24 rounded-full bg-[#111315] border-2 border-[#7FEA35] flex items-center justify-center shadow-[0_0_30px_rgba(127,234,53,0.3)]">
                    <span className="text-6xl font-black text-[#7FEA35] font-mono leading-none">
                      {countdownNum}
                    </span>
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <p className="text-xs font-mono font-bold text-white uppercase tracking-widest">
                    Set Batting Stance
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Target: {targetShot}
                  </p>
                </div>
              </div>
            )}

            {/* Recording Active Indicator Banner */}
            {recordingState === 'recording' && (
              <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-30 pointer-events-none">
                <div className="flex items-center space-x-2.5 px-4 py-2 rounded-full bg-rose-950/90 border border-rose-500 text-rose-300 font-mono text-xs font-bold shadow-lg animate-pulse">
                  <span className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
                  <span>RECORDING ATTEMPT: 00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds}</span>
                </div>

                <div className="bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-full text-xs font-mono text-white border border-[#303438]">
                  Target: <strong className="text-[#7FEA35]">{targetShot}</strong>
                </div>
              </div>
            )}

            {/* Analyzing Progress Overlay */}
            {recordingState === 'analyzing' && (
              <div className="absolute inset-0 bg-[#050505]/90 backdrop-blur-md flex flex-col items-center justify-center z-40 p-8 space-y-4 text-center">
                <RefreshCw className="w-10 h-10 text-[#7FEA35] animate-spin" />
                <div className="space-y-1">
                  <h3 className="text-lg font-black text-white">Analyzing Batting Biomechanics</h3>
                  <p className="text-xs text-[#A5A9AD] max-w-sm">
                    {analysisProgress?.step || 'Running MediaPipe pose estimation & reference DTW comparison...'}
                  </p>
                </div>
                <div className="w-full max-w-xs bg-[#181B1D] rounded-full h-2.5 border border-[#303438] overflow-hidden">
                  <div
                    className="bg-[#7FEA35] h-full transition-all duration-300"
                    style={{ width: `${analysisProgress?.percent || 50}%` }}
                  />
                </div>
              </div>
            )}

            {/* Connecting State */}
            {cameraConnecting && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-navy-950/90 z-20 space-y-3 p-6 text-center">
                <RefreshCw className="w-8 h-8 text-[#7FEA35] animate-spin" />
                <h3 className="text-sm font-bold text-white">Connecting to Batting Camera...</h3>
                <p className="text-xs text-slate-400 max-w-xs">
                  Please click "Allow" in your browser address bar if prompted for camera access.
                </p>
              </div>
            )}

            {/* Disconnected / Error State Overlay */}
            {!cameraActive && !cameraConnecting && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#050505]/95 z-20 space-y-4 p-6 text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#111315] border border-[#303438] flex items-center justify-center text-[#A5A9AD] shadow-inner">
                  <CameraOff className="w-7 h-7 text-[#7FEA35]" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-white">
                    {cameraError ? 'Camera Connection Failed' : 'Batting Camera Disconnected'}
                  </h3>
                  <p className="text-xs text-[#A5A9AD] max-w-sm">
                    {cameraError || 'Connect your webcam to start real-time batting practice, or test using simulated cricketer footage.'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                  <button
                    onClick={() => startCamera()}
                    className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-[#7FEA35] hover:bg-[#6ed32c] text-[#050505] font-bold text-xs shadow-lg shadow-[#7FEA35]/20 transition-all cursor-pointer"
                  >
                    <Camera className="w-4 h-4" />
                    <span>{cameraError ? 'Retry Camera Connection' : 'Connect Camera'}</span>
                  </button>

                  <button
                    onClick={startSimulation}
                    className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-[#181B1D] hover:bg-[#202428] text-[#F5F5F5] font-semibold text-xs border border-[#303438] transition-all cursor-pointer"
                    title="Run practice simulation using sample cricket video"
                  >
                    <Play className="w-3.5 h-3.5 text-[#7FEA35] fill-[#7FEA35]" />
                    <span>Simulate Practice Feed</span>
                  </button>
                </div>
              </div>
            )}

            {/* Camera Positioning Silhouette Guide */}
            {!poseState?.presence.detected && cameraActive && recordingState === 'idle' && (
              <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center bg-black/30 backdrop-blur-[1px] p-6 text-center">
                <div className="w-48 sm:w-64 h-72 sm:h-80 border-2 border-dashed border-[#7FEA35]/60 rounded-3xl flex flex-col items-center justify-between p-4 bg-[#7FEA35]/5">
                  <span className="text-[11px] font-mono text-[#7FEA35] bg-[#050505]/80 px-2 py-0.5 rounded border border-[#7FEA35]/30">
                    Position Batter Inside Box
                  </span>
                  <div className="w-16 h-16 rounded-full border border-[#7FEA35]/40 border-dashed" />
                  <span className="text-[10px] font-mono text-slate-400 bg-[#050505]/80 px-2 py-0.5 rounded">
                    Side-On Perspective (~90°)
                  </span>
                </div>
              </div>
            )}

            {/* Top HUD: Real-time State Machine Pill */}
            {recordingState !== 'recording' && recordingState !== 'analyzing' && (
              <div className="absolute top-4 left-4 right-4 flex items-center justify-between pointer-events-none">
                <div
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border shadow-lg backdrop-blur-md ${stateTheme.bg}`}
                >
                  <span className={`w-2.5 h-2.5 rounded-full ${stateTheme.pill}`} />
                  <span className={`text-xs font-bold font-sans ${stateTheme.color}`}>
                    {stateTheme.title}
                  </span>
                </div>

                {/* Live Telemetry Pill */}
                <div className="flex items-center space-x-2 bg-[#050505]/85 backdrop-blur-md border border-[#303438] px-3 py-1.5 rounded-full text-[11px] font-mono text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-[#7FEA35] animate-pulse" />
                  <span>Motion: <strong className="text-white">{fps} FPS</strong></span>
                  <span>•</span>
                  <span>Latency: <strong className="text-[#7FEA35]">{liveLatency}ms</strong></span>
                </div>
              </div>
            )}

            {/* Bottom HUD: Live Kinematics Readout */}
            {poseState?.presence.detected && recordingState !== 'reviewing' && (
              <div className="absolute bottom-4 left-4 right-4 flex flex-wrap items-center justify-between gap-2 bg-[#050505]/85 backdrop-blur-md border border-[#303438] p-2.5 rounded-xl text-xs font-mono text-slate-300 pointer-events-none">
                <div className="flex flex-wrap items-center gap-4">
                  <div>
                    <span className="text-slate-400 text-[10px]">Lead Knee: </span>
                    <strong className="text-emerald-400 text-sm">
                      {poseState.current_lead_knee ? `${poseState.current_lead_knee}°` : '--'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px]">Lead Elbow: </span>
                    <strong className="text-teal-400 text-sm">
                      {poseState.current_lead_elbow ? `${poseState.current_lead_elbow}°` : '--'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px]">Torso Lean: </span>
                    <strong className="text-sky-400 text-sm">
                      {poseState.current_torso_lean ? `${poseState.current_torso_lean}°` : '--'}
                    </strong>
                  </div>
                  {poseState.bat_detected && (
                    <div className="text-amber-400">
                      <span className="text-[10px] text-amber-500/80">Bat: </span>
                      <strong className="text-sm">
                        {poseState.bat_angle_deg ? `${poseState.bat_angle_deg}°` : 'Tracking'}
                      </strong>
                    </div>
                  )}
                </div>

                <div className="text-[11px] text-slate-400">
                  {handedness} Hand • {targetShot}
                </div>
              </div>
            )}
          </div>

          {/* Practice Action Trigger Toolbar */}
          <div className="bg-[#111315] p-3.5 rounded-xl border border-[#303438] flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              {recordingState === 'idle' && (
                <button
                  onClick={initiateRecordingWithCountdown}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/30 transition-all cursor-pointer"
                  title="Record Batting Attempt (or Press Space)"
                >
                  <Play className="w-4 h-4 fill-white" />
                  <span>Record Practice Attempt (Space)</span>
                </button>
              )}

              {recordingState === 'recording' && (
                <button
                  onClick={stopRecording}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-lg transition-all animate-pulse cursor-pointer"
                  title="Stop Recording"
                >
                  <Square className="w-4 h-4 fill-white" />
                  <span>Stop Recording (00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds})</span>
                </button>
              )}

              {recordingState === 'reviewing' && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleRetakeAttempt}
                    className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-[#181B1D] hover:bg-[#202428] text-[#F5F5F5] font-semibold text-xs border border-[#303438] cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Retake Attempt</span>
                  </button>

                  <button
                    onClick={submitAttemptForAnalysis}
                    className="inline-flex items-center space-x-2 px-5 py-2 rounded-xl bg-[#7FEA35] hover:bg-[#6ed32c] text-[#050505] font-bold text-xs shadow-lg shadow-[#7FEA35]/20 cursor-pointer"
                  >
                    <UploadCloud className="w-4 h-4" />
                    <span>Submit for AI Coaching (Space)</span>
                  </button>
                </div>
              )}

              <span className="text-[11px] text-[#A5A9AD] hidden sm:inline">
                Auto-detection active: stroke acceleration automatically stops recording.
              </span>
            </div>

            <div className="text-right text-xs font-mono text-[#A5A9AD]">
              Session: <strong className="text-white">{practiceSessionId}</strong>
            </div>
          </div>
        </div>

        {/* Right Section / Split View: Reference Coach Avatar & Technique Feedback */}
        <div className={`${showReferenceCoach ? 'xl:col-span-4' : 'lg:col-span-1'} space-y-4`}>
          {/* Reference Coach Avatar Widget */}
          {showReferenceCoach && (
            <div className="rounded-2xl overflow-hidden border border-[#303438] bg-[#0A0C0E] shadow-xl">
              <div className="px-4 py-2.5 bg-[#111315] border-b border-[#303438] flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#7FEA35] shadow-sm shadow-[#7FEA35]/50" />
                  <span className="text-xs font-bold uppercase tracking-wider text-[#F5F5F5]">
                    Reference Form: {targetShot}
                  </span>
                </div>
              </div>
              {/* Technique Coaching Intent */}
              {(() => {
                const tech = getShotTechnique(targetShot);
                return tech?.intent ? (
                  <div className="px-3 py-1.5 bg-[#181B1D] border-b border-[#303438] text-[11px] text-[#7FEA35] flex items-center gap-1.5">
                    <span className="font-bold uppercase tracking-wider text-[9px] bg-[#7FEA35]/15 px-1.5 py-0.5 rounded text-[#7FEA35]">Intent</span>
                    <span className="text-[#F5F5F5] truncate">{tech.intent}</span>
                  </div>
                ) : null;
              })()}
              <Batter3DCanvas
                shotName={targetShot}
                height={320}
                showTrail={true}
                showControls={true}
                showPhaseScrubber={false}
                showCameraPresets={true}
                autoOrbitDefault={false}
              />
            </div>
          )}

          {/* Post-Shot Feedback Card */}
          {currentFeedback ? (
            <div className="bg-[#111315] border-2 border-[#7FEA35]/60 rounded-2xl p-5 space-y-4 shadow-xl relative overflow-hidden animate-in fade-in zoom-in-95 duration-200">
              {/* Card Header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#7FEA35]/10 text-[#7FEA35] font-bold border border-[#7FEA35]/20">
                      Shot Detected
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">
                      {currentFeedback.created_at}
                    </span>
                  </div>
                  <h3 className="text-lg font-black text-white tracking-tight mt-1">
                    {currentFeedback.shot_type}
                  </h3>
                </div>

                <div className="text-right font-mono">
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                    {(currentFeedback.confidence_score * 100).toFixed(0)}% Conf
                  </span>
                </div>
              </div>

              {/* Key Kinematic Readings Grid */}
              <div className="grid grid-cols-3 gap-2 bg-[#050505]/80 p-2.5 rounded-xl border border-[#303438] text-center font-mono">
                <div className="p-1">
                  <div className="text-[10px] text-slate-400">Lead Knee</div>
                  <div className="text-xs font-bold text-emerald-400">
                    {currentFeedback.impact_lead_knee ? `${currentFeedback.impact_lead_knee}°` : '--'}
                  </div>
                </div>
                <div className="p-1 border-x border-[#303438]">
                  <div className="text-[10px] text-slate-400">Lead Elbow</div>
                  <div className="text-xs font-bold text-teal-400">
                    {currentFeedback.impact_lead_elbow ? `${currentFeedback.impact_lead_elbow}°` : '--'}
                  </div>
                </div>
                <div className="p-1">
                  <div className="text-[10px] text-slate-400">Bat Angle</div>
                  <div className="text-xs font-bold text-amber-400">
                    {currentFeedback.bat_angle_impact ? `${currentFeedback.bat_angle_impact}°` : 'Vertical'}
                  </div>
                </div>
              </div>

              {/* Main Technique Observation */}
              <div className="space-y-1">
                <div className="text-xs font-bold text-[#7FEA35] uppercase tracking-wider flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#7FEA35]" />
                  <span>Coaching Observation</span>
                </div>
                <div className="text-sm font-bold text-white leading-snug">
                  {currentFeedback.main_observation}
                </div>
              </div>

              {/* Evidence Box */}
              <div className="bg-[#050505]/90 rounded-xl p-3 border border-[#303438] text-xs font-mono space-y-1">
                <div className="flex items-center justify-between text-slate-300">
                  <span className="text-slate-400">Measured Evidence:</span>
                  <strong className="text-white">{currentFeedback.observed_value}</strong>
                </div>
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Benchmark Tolerance:</span>
                  <span className="text-emerald-400">{currentFeedback.benchmark_value}</span>
                </div>
              </div>

              {/* Why It Matters */}
              <div className="text-xs text-slate-300 leading-relaxed">
                <strong className="text-[#7FEA35]">Why it matters: </strong>
                {currentFeedback.why_it_matters}
              </div>

              {/* Practical Drill for Next Shot */}
              <div className="p-3 rounded-xl bg-[#7FEA35]/10 border border-[#7FEA35]/20 text-xs text-slate-200 space-y-1">
                <div className="font-bold text-[#7FEA35] flex items-center space-x-1.5 text-[11px] uppercase tracking-wide">
                  <Dumbbell className="w-3.5 h-3.5" />
                  <span>Next Rep Focus Cue</span>
                </div>
                <p className="leading-relaxed font-sans">{currentFeedback.next_action_drill}</p>
              </div>

              {/* Comparison with Previous Attempt */}
              {currentFeedback.previous_attempt_comparison && (
                <div className="p-2.5 rounded-lg bg-[#050505] border border-[#303438] text-xs text-[#7FEA35] flex items-start space-x-2">
                  <Scale className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <p className="text-[11px]">{currentFeedback.previous_attempt_comparison}</p>
                </div>
              )}

              {/* Primary Action Buttons */}
              <div className="space-y-2 pt-2">
                <button
                  onClick={handleNextShot}
                  className="w-full py-3 rounded-xl bg-[#7FEA35] hover:bg-[#6ed32c] text-[#050505] font-bold text-xs sm:text-sm shadow-lg shadow-[#7FEA35]/20 flex items-center justify-center space-x-2 transition-all transform hover:-translate-y-0.5 cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Practice Next Shot (Space)</span>
                </button>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      onSelectSession(currentFeedback.full_session_id);
                      onSelectTab('workspace');
                    }}
                    className="py-2 px-3 rounded-lg bg-[#181B1D] hover:bg-[#202428] text-slate-200 text-xs font-semibold border border-[#303438] transition-colors cursor-pointer"
                  >
                    View in Workspace
                  </button>

                  <button
                    onClick={() => {
                      onSelectSession(currentFeedback.full_session_id);
                      onSelectTab('comparison');
                    }}
                    className="py-2 px-3 rounded-lg bg-[#181B1D] hover:bg-[#202428] text-slate-200 text-xs font-semibold border border-[#303438] transition-colors cursor-pointer"
                  >
                    Compare DTW
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Standby Card when waiting for a shot */
            <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-[#050505] border border-[#303438] flex items-center justify-center mx-auto text-[#7FEA35]">
                <Sparkles className="w-6 h-6 animate-pulse" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-white">Live AI Coach Ready</h3>
                <p className="text-xs text-[#A5A9AD] max-w-xs mx-auto">
                  Take your stance in front of the camera. Click Record or press Spacebar — review your attempt and receive grounded biomechanical analysis.
                </p>
              </div>

              <div className="p-3 bg-[#050505] rounded-xl border border-[#303438] text-[11px] text-[#A5A9AD] space-y-1 text-left font-mono">
                <div className="font-semibold text-white">Coaching Execution Cycle:</div>
                <p>1. Check stance & posture with reference avatar</p>
                <p>2. Record attempt with 3s countdown</p>
                <p>3. Review video & submit for full AI analysis</p>
              </div>
            </div>
          )}

          {/* Practice Session Summary Bar */}
          <div className="bg-[#111315] rounded-2xl border border-[#303438] p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                <Activity className="w-3.5 h-3.5 text-[#7FEA35]" />
                <span>Session Reps History</span>
              </h4>
              <span className="text-xs font-mono font-bold text-white">
                {attemptCount} Shot{attemptCount === 1 ? '' : 's'}
              </span>
            </div>

            {recentAttempts.length > 0 ? (
              <div className="space-y-2">
                <div className="text-[11px] text-[#A5A9AD]">Recent Attempt Trajectories:</div>
                <div className="space-y-1.5">
                  {recentAttempts.map((att, i) => (
                    <div
                      key={att.attempt_id}
                      onClick={() => {
                        onSelectSession(att.full_session_id);
                        onSelectTab('workspace');
                      }}
                      className="p-2.5 rounded-lg bg-[#050505] border border-[#303438] hover:border-[#7FEA35]/50 transition-all cursor-pointer flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[#7FEA35] font-bold">#{attemptCount - i}</span>
                        <span className="text-white font-medium">{att.shot_type}</span>
                      </div>
                      <div className="font-mono text-[11px] text-slate-300">
                        Knee: <strong className="text-emerald-400">{att.impact_lead_knee}°</strong>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-slate-500 text-center py-2">
                No attempts recorded yet in this practice session.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
