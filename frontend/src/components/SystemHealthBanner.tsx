import React, { useEffect, useState, useCallback, useRef } from 'react';
import { AlertTriangle, AlertCircle, RefreshCw, X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export interface ModelHealthInfo {
  name?: string;
  loaded?: boolean;
  loading?: boolean;
  error?: string | null;
  available?: boolean;
}

export interface HealthData {
  status: 'healthy' | 'warming_up' | 'degraded' | 'offline';
  ready?: boolean;
  job_running?: boolean;
  issues?: string[];
  models?: {
    pose?: ModelHealthInfo;
    hand?: ModelHealthInfo;
    phase?: ModelHealthInfo;
    ffmpeg?: ModelHealthInfo;
    pose_estimator?: ModelHealthInfo;
    phase_classifier?: ModelHealthInfo;
    hand_landmarker?: ModelHealthInfo;
  };
  ffmpeg?: { available: boolean; path?: string };
  database?: { connected: boolean; writable: boolean };
}

export const SystemHealthBanner: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [dismissed, setDismissed] = useState<boolean>(false);
  const [checking, setChecking] = useState<boolean>(false);

  const firstFailureTimeRef = useRef<number | null>(null);
  const consecutiveFailuresRef = useRef<number>(0);
  const isCheckingRef = useRef<boolean>(false);
  const pollTimerRef = useRef<any>(null);

  const checkHealth = useCallback(async () => {
    if (isCheckingRef.current) return;
    isCheckingRef.current = true;
    setChecking(true);
    try {
      const data: HealthData = await api.getHealth();
      firstFailureTimeRef.current = null;
      consecutiveFailuresRef.current = 0;
      if (data.job_running) {
        // While an analysis job is running, server is busy but healthy
        setHealth({
          ...data,
          status: 'healthy',
          ready: true,
          issues: [],
        });
      } else {
        setHealth(data);
      }
    } catch {
      consecutiveFailuresRef.current += 1;
      // Do not declare offline or warming up on a single intermittent failure
      if (consecutiveFailuresRef.current < 3) {
        // Keep existing health status
      } else {
        if (firstFailureTimeRef.current === null) {
          firstFailureTimeRef.current = Date.now();
        }
        const elapsedSec = (Date.now() - firstFailureTimeRef.current) / 1000;

        // Allow up to 3.5 minutes (210s) of retry/backoff for free tier server wake up
        if (elapsedSec < 210) {
          setHealth({
            status: 'warming_up',
            ready: false,
            issues: ['Server is waking up (Render free tier cold start takes ~60s)...'],
          });
        } else {
          setHealth({
            status: 'offline',
            ready: false,
            issues: ['Backend server is unreachable after multiple wake-up attempts.'],
          });
        }
      }
    } finally {
      isCheckingRef.current = false;
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    // Poll every 10s if warming up or offline, otherwise 30s
    const pollInterval = health?.status === 'warming_up' || health?.status === 'offline' ? 10000 : 30000;
    pollTimerRef.current = setInterval(checkHealth, pollInterval);
    return () => clearInterval(pollTimerRef.current);
  }, [checkHealth, health?.status]);

  if (!health || (health.status === 'healthy' && health.ready !== false) || dismissed) {
    return null;
  }

  const isWarmingUp = health.status === 'warming_up' || (!health.ready && health.status !== 'offline');
  const isOffline = health.status === 'offline';

  // Format detailed model failure notes
  const modelFailures: string[] = [];
  if (health.models) {
    const pose = health.models.pose || health.models.pose_estimator;
    const phase = health.models.phase || health.models.phase_classifier;
    const hand = health.models.hand || health.models.hand_landmarker;
    const ffmpeg = health.models.ffmpeg || health.ffmpeg;

    if (pose && !pose.loaded && !pose.loading) {
      modelFailures.push(`Pose Model: ${pose.error || 'not loaded'}`);
    }
    if (phase && !phase.loaded) {
      modelFailures.push(`BiLSTM Phase: ${phase.error || 'not loaded'}`);
    }
    if (hand && !hand.loaded && !hand.loading && (hand.error || isOffline)) {
      modelFailures.push(`Hand Model: ${hand.error || 'not loaded'}`);
    }
    if (ffmpeg && !ffmpeg.available) {
      modelFailures.push('FFmpeg: not found in PATH');
    }
  }

  const issues = modelFailures.length > 0
    ? modelFailures
    : health.issues && health.issues.length > 0
    ? health.issues
    : isWarmingUp
    ? ['Server is waking up, this can take a minute...']
    : isOffline
    ? ['Backend server is unreachable. Please verify connection.']
    : ['One or more AI models or dependencies are initializing.'];

  return (
    <div
      role="alert"
      className={`border-b px-4 py-2 text-xs flex items-center justify-between z-30 transition-all duration-200 ${
        isWarmingUp
          ? 'bg-amber-500/15 border-amber-500/40 text-amber-200'
          : isOffline
          ? 'bg-rose-500/15 border-rose-500/40 text-rose-200'
          : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
      }`}
    >
      <div className="flex items-center space-x-2.5 min-w-0">
        {isWarmingUp ? (
          <Loader2 className="w-4 h-4 text-amber-400 animate-spin flex-shrink-0" />
        ) : isOffline ? (
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
        )}
        <div className="truncate">
          <span className={`font-semibold mr-2 ${isWarmingUp ? 'text-amber-300' : isOffline ? 'text-rose-300' : 'text-amber-300'}`}>
            {isWarmingUp
              ? 'Server Initializing:'
              : isOffline
              ? 'Backend AI Offline:'
              : 'System Warning:'}
          </span>
          <span className={isOffline ? 'text-rose-200/90' : 'text-amber-200/90'}>{issues.join(' | ')}</span>
        </div>
      </div>
      <div className="flex items-center space-x-2 flex-shrink-0 ml-3">
        <button
          onClick={() => {
            setDismissed(false);
            checkHealth();
          }}
          disabled={checking}
          className={`p-1 rounded text-[11px] font-mono flex items-center space-x-1 ${
            isOffline
              ? 'hover:bg-rose-500/20 text-rose-300'
              : 'hover:bg-amber-500/20 text-amber-300'
          }`}
          title="Retry Health Check"
        >
          <RefreshCw className={`w-3 h-3 ${checking ? 'animate-spin' : ''}`} />
          <span>{checking ? 'Checking...' : 'Retry'}</span>
        </button>
        <button
          onClick={() => setDismissed(true)}
          className={`p-1 rounded ${isOffline ? 'hover:bg-rose-500/20 text-rose-400' : 'hover:bg-amber-500/20 text-amber-400'}`}
          aria-label="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
