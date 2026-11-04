import {
  AnalysisResult,
  ComparisonResult,
  ModelEvaluationReport,
  ReferenceShotMeta,
  SessionListResponse,
  VideoProcessingStatus,
  LiveFrameRequest,
  LivePoseState,
  LiveAttemptPayload,
  LiveAttemptFeedback,
  CricketShot,
  ShotListResponse,
} from '../types/cricket';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api';

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async uploadVideo(formData: FormData) {
    const res = await fetch(`${API_BASE}/video/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async inspectStrikers(formData: FormData) {
    const res = await fetch(`${API_BASE}/video/inspect-strikers`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Striker inspection failed' }));
      throw new Error(err.detail || 'Striker inspection failed');
    }
    return res.json();
  },

  async getProcessingStatus(sessionId: string): Promise<VideoProcessingStatus> {
    const res = await fetch(`${API_BASE}/video/status/${sessionId}`);
    if (!res.ok) throw new Error('Failed to fetch processing status');
    return res.json();
  },

  async getAnalysis(sessionId: string): Promise<AnalysisResult> {
    const res = await fetch(`${API_BASE}/analysis/${sessionId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Analysis not found' }));
      throw new Error(err.detail || 'Failed to fetch analysis');
    }
    return res.json();
  },

  async listSessions(limit = 50, shotType?: string, category?: string): Promise<SessionListResponse> {
    const params = new URLSearchParams();
    params.set('limit', limit.toString());
    if (shotType && shotType !== 'All') params.set('shot_type', shotType);
    if (category && category !== 'All') params.set('category', category);
    const res = await fetch(`${API_BASE}/sessions?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch session list');
    return res.json();
  },

  /* =========================================================================
     Shot Library Endpoints
     ========================================================================= */

  async getShots(category?: string, search?: string, referenceOnly = false): Promise<ShotListResponse> {
    const params = new URLSearchParams();
    if (category && category !== 'All' && category !== 'All Shots') {
      params.set('category', category);
    }
    if (search && search.trim()) {
      params.set('search', search.trim());
    }
    if (referenceOnly) {
      params.set('reference_only', 'true');
    }
    const queryString = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/shots${queryString}`);
    if (!res.ok) throw new Error('Failed to fetch shot library');
    return res.json();
  },

  async getShot(idOrSlug: string): Promise<CricketShot> {
    const res = await fetch(`${API_BASE}/shots/${encodeURIComponent(idOrSlug)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Shot not found' }));
      throw new Error(err.detail || 'Failed to fetch shot details');
    }
    return res.json();
  },

  async getShotReference(idOrSlug: string) {
    const res = await fetch(`${API_BASE}/reference/shots/${encodeURIComponent(idOrSlug)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Reference not found' }));
      throw new Error(err.detail || 'Failed to fetch shot reference');
    }
    return res.json();
  },

  async uploadCustomReference(formData: FormData) {
    const res = await fetch(`${API_BASE}/reference/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Failed to upload reference video');
    }
    return res.json();
  },

  async confirmShotType(sessionId: string, confirmedShotType: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/confirm-shot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmed_shot_type: confirmedShotType }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to confirm shot' }));
      throw new Error(err.detail || 'Failed to confirm shot');
    }
    return res.json();
  },

  async deleteSession(sessionId: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete session');
    return res.json();
  },

  async listReferences(): Promise<ReferenceShotMeta[]> {
    const res = await fetch(`${API_BASE}/comparison/references`);
    if (!res.ok) throw new Error('Failed to fetch reference benchmarks');
    return res.json();
  },

  async compare(
    sessionId: string,
    referenceId?: string,
    targetSessionId?: string
  ): Promise<ComparisonResult> {
    const res = await fetch(`${API_BASE}/comparison/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        reference_id: referenceId,
        target_session_id: targetSessionId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Comparison failed' }));
      throw new Error(err.detail || 'Failed to compare sessions');
    }
    return res.json();
  },

  async getEvaluationReport(): Promise<ModelEvaluationReport> {
    const res = await fetch(`${API_BASE}/evaluation/report`);
    if (!res.ok) throw new Error('Failed to fetch model evaluation report');
    return res.json();
  },

  /* =========================================================================
     Live Batting Coach Endpoints
     ========================================================================= */

  async processLiveFrame(payload: LiveFrameRequest): Promise<LivePoseState> {
    const res = await fetch(`${API_BASE}/live/process-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Live frame processing failed');
    return res.json();
  },

  async analyzeLiveAttempt(payload: LiveAttemptPayload): Promise<LiveAttemptFeedback> {
    const res = await fetch(`${API_BASE}/live/analyze-attempt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Live attempt analysis failed');
    return res.json();
  },

  async getLiveSessionAttempts(sessionId: string): Promise<LiveAttemptFeedback[]> {
    const res = await fetch(`${API_BASE}/live/session/${sessionId}/attempts`);
    if (!res.ok) throw new Error('Failed to fetch live session attempts');
    return res.json();
  },

  /* =========================================================================
     Biomechanical Progress Tracking Endpoints
     ========================================================================= */

  async getProgressSummary(limit = 200) {
    const res = await fetch(`${API_BASE}/progress/summary?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch progress summary');
    return res.json();
  },

  async getProgressShots(): Promise<string[]> {
    const res = await fetch(`${API_BASE}/progress/shots`);
    if (!res.ok) throw new Error('Failed to fetch available progress shots');
    return res.json();
  },

  async getShotProgress(shotType: string, limit = 50) {
    const res = await fetch(`${API_BASE}/progress/shots/${encodeURIComponent(shotType)}?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to fetch progress trend for ${shotType}`);
    return res.json();
  },

  getWebSocketUrl(sessionId: string): string {
    const httpBase = API_BASE.replace('/api', '');
    const wsBase = httpBase.replace('http://', 'ws://').replace('https://', 'wss://');
    return `${wsBase}/api/live/ws/${sessionId}`;
  },

  getVideoUrl(path: string | null | undefined): string {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const base = API_BASE.replace('/api', '');
    return `${base}${path.startsWith('/') ? '' : '/'}${path}`;
  },
};
