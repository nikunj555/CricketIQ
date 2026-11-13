import React, { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, AlertCircle, RefreshCw, X } from 'lucide-react';
import { api } from '../services/api';

interface HealthData {
  status: 'healthy' | 'degraded' | 'offline';
  issues?: string[];
  models?: {
    pose_estimator?: { loaded: boolean };
    phase_classifier?: { loaded: boolean };
    hand_landmarker?: { loaded: boolean };
  };
  ffmpeg?: { available: boolean };
  database?: { connected: boolean; writable: boolean };
}

export const SystemHealthBanner: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [dismissed, setDismissed] = useState<boolean>(false);
  const [checking, setChecking] = useState<boolean>(false);

  const checkHealth = useCallback(async () => {
    setChecking(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch {
      setHealth({
        status: 'offline',
        issues: ['Backend server is unreachable or offline.'],
      });
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  if (!health || health.status === 'healthy' || dismissed) {
    return null;
  }

  const issues = health.issues && health.issues.length > 0
    ? health.issues
    : ['One or more AI subsystem models or media utilities are not ready.'];

  return (
    <div
      role="alert"
      className="bg-amber-500/10 border-b border-amber-500/30 text-amber-200 px-4 py-2 text-xs flex items-center justify-between z-30 transition-all duration-200"
    >
      <div className="flex items-center space-x-2.5 min-w-0">
        <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
        <div className="truncate">
          <span className="font-semibold text-amber-300 mr-2">System Degradation Warning:</span>
          <span className="text-amber-200/90">{issues.join(' | ')}</span>
        </div>
      </div>
      <div className="flex items-center space-x-2 flex-shrink-0 ml-3">
        <button
          onClick={() => {
            setDismissed(false);
            checkHealth();
          }}
          disabled={checking}
          className="p-1 hover:bg-amber-500/20 rounded text-amber-300 text-[11px] font-mono flex items-center space-x-1"
          title="Retry Health Check"
        >
          <RefreshCw className={`w-3 h-3 ${checking ? 'animate-spin' : ''}`} />
          <span>Retry</span>
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="p-1 hover:bg-amber-500/20 rounded text-amber-400"
          aria-label="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
