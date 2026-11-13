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

const isVercelHost =
  typeof window !== 'undefined' && window.location.hostname.includes('vercel.app');

const rawBase =
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_URL ||
  (isVercelHost
    ? 'https://cricketiq-1-ekqx.onrender.com/api'
    : (typeof window !== 'undefined'
        ? `${window.location.origin}/api`
        : 'http://127.0.0.1:8000/api'));

const API_BASE = rawBase.replace(/\/+$/, '');

async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const isHealthCheck = typeof input === 'string' && input.includes('/health');
  const isUpload =
    typeof input === 'string' &&
    (input.includes('/video/upload') || input.includes('/inspect-strikers'));
  const timeoutMs = isHealthCheck ? 8000 : (isUpload ? 180000 : 45000);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const fetchInit: RequestInit = {
      ...init,
      signal: init?.signal || controller.signal,
    };
    return await fetch(input, fetchInit);
  } catch (err: unknown) {
    const errorObj = err as { name?: string; message?: string };
    if (
      errorObj?.name === 'AbortError' ||
      errorObj?.name === 'TypeError' ||
      errorObj?.message?.includes('Failed to fetch') ||
      errorObj?.message?.includes('NetworkError') ||
      errorObj?.message?.includes('aborted')
    ) {
      throw new Error(
        'Backend server unreachable or timing out. Please check server connectivity.'
      );
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  async getHealth() {
    const res = await apiFetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async uploadVideo(
    formData: FormData,
    onProgress?: (percent: number, loaded: number, total: number) => void
  ): Promise<{ session_id: string; message: string; original_filename: string; processing_status: string }> {
    if (typeof XMLHttpRequest !== 'undefined') {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE}/video/upload`);
        xhr.timeout = 180000;

        if (xhr.upload && onProgress) {
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable && event.total > 0) {
              const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
              onProgress(percent, event.loaded, event.total);
            }
          };
        }

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const json = JSON.parse(xhr.responseText);
              resolve(json);
            } catch {
              resolve({
                session_id: '',
                message: 'Video uploaded successfully',
                original_filename: '',
                processing_status: 'queued',
              });
            }
          } else {
            let errorMsg = '';
            try {
              const err = JSON.parse(xhr.responseText);
              if (typeof err.detail === 'string') {
                errorMsg = err.detail;
              } else if (Array.isArray(err.detail)) {
                errorMsg = err.detail.map((d: any) => d.msg || d.type || JSON.stringify(d)).join('; ');
              } else if (err.message) {
                errorMsg = err.message;
              } else if (err.error) {
                errorMsg = err.error;
              }
            } catch {
              if (xhr.status === 413) {
                errorMsg = 'Video file exceeds upload size limit (max 150MB). Please select a shorter or compressed clip.';
              } else if (xhr.status === 502 || xhr.status === 503) {
                errorMsg = 'Backend AI service is starting up on the server. Please wait 15-30 seconds and retry.';
              } else if (xhr.status === 504) {
                errorMsg = 'Gateway timeout: video upload took too long or network connection was interrupted.';
              }
            }
            reject(new Error(errorMsg || `Upload failed with status ${xhr.status} (${xhr.statusText || 'Error'})`));
          }
        };

        xhr.onerror = () => {
          reject(new Error('Backend server unreachable or timing out. Please check server connectivity.'));
        };

        xhr.ontimeout = () => {
          reject(new Error('Video upload timed out. Please check your network connection and retry.'));
        };

        xhr.send(formData);
      });
    }

    const res = await apiFetch(`${API_BASE}/video/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      let errorMsg = '';
      try {
        const err = await res.json();
        if (typeof err.detail === 'string') {
          errorMsg = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMsg = err.detail.map((d: any) => d.msg || d.type || JSON.stringify(d)).join('; ');
        } else if (err.message) {
          errorMsg = err.message;
        } else if (err.error) {
          errorMsg = err.error;
        }
      } catch {
        const text = await res.text().catch(() => '');
        if (text && text.length < 200 && !text.includes('<!DOCTYPE')) {
          errorMsg = text;
        } else if (res.status === 413) {
          errorMsg = 'Video file exceeds upload size limit (max 150MB). Please select a shorter or compressed clip.';
        } else if (res.status === 502 || res.status === 503) {
          errorMsg = 'Backend AI service is starting up on the server. Please wait 15-30 seconds and retry.';
        } else if (res.status === 504) {
          errorMsg = 'Gateway timeout: video upload took too long or network connection was interrupted.';
        }
      }
      throw new Error(errorMsg || `Upload failed with status ${res.status} (${res.statusText || 'Error'})`);
    }
    return res.json();
  },

  async inspectStrikers(formData: FormData) {
    const res = await apiFetch(`${API_BASE}/video/inspect-strikers`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      let errorMsg = '';
      try {
        const err = await res.json();
        if (typeof err.detail === 'string') {
          errorMsg = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMsg = err.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        }
      } catch {}
      throw new Error(errorMsg || `Striker inspection failed (${res.status})`);
    }
    return res.json();
  },

  async getProcessingStatus(sessionId: string): Promise<VideoProcessingStatus> {
    const res = await apiFetch(`${API_BASE}/video/status/${sessionId}`);
    if (!res.ok) throw new Error('Failed to fetch processing status');
    return res.json();
  },

  async selectStriker(sessionId: string, trackId: number) {
    const res = await apiFetch(`${API_BASE}/video/session/${sessionId}/select-striker?track_id=${trackId}`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to select striker' }));
      throw new Error(err.detail || 'Failed to select striker');
    }
    return res.json();
  },

  async getAnalysis(sessionId: string): Promise<AnalysisResult> {
    const res = await apiFetch(`${API_BASE}/analysis/${sessionId}`);
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
    const res = await apiFetch(`${API_BASE}/sessions?${params.toString()}`);
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
    const res = await apiFetch(`${API_BASE}/shots${queryString}`);
    if (!res.ok) throw new Error('Failed to fetch shot library');
    return res.json();
  },

  async getShot(idOrSlug: string): Promise<CricketShot> {
    const res = await apiFetch(`${API_BASE}/shots/${encodeURIComponent(idOrSlug)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Shot not found' }));
      throw new Error(err.detail || 'Failed to fetch shot details');
    }
    return res.json();
  },

  async getShotReference(idOrSlug: string) {
    const res = await apiFetch(`${API_BASE}/reference/shots/${encodeURIComponent(idOrSlug)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Reference not found' }));
      throw new Error(err.detail || 'Failed to fetch shot reference');
    }
    return res.json();
  },

  async uploadCustomReference(formData: FormData) {
    const res = await apiFetch(`${API_BASE}/reference/upload`, {
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
    const res = await apiFetch(`${API_BASE}/sessions/${sessionId}/confirm-shot`, {
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

  async reanalyzeShot(sessionId: string, shotType: string, lang = 'en'): Promise<AnalysisResult> {
    const res = await apiFetch(`${API_BASE}/analysis/${sessionId}/reanalyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shot_type: shotType, lang }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to re-analyse shot' }));
      throw new Error(err.detail || 'Failed to re-analyse shot');
    }
    return res.json();
  },

  async deleteSession(sessionId: string) {
    const res = await apiFetch(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete session');
    return res.json();
  },

  async listReferences(): Promise<ReferenceShotMeta[]> {
    const res = await apiFetch(`${API_BASE}/comparison/references`);
    if (!res.ok) throw new Error('Failed to fetch reference benchmarks');
    return res.json();
  },

  async compare(
    sessionId: string,
    referenceId?: string,
    targetSessionId?: string
  ): Promise<ComparisonResult> {
    const res = await apiFetch(`${API_BASE}/comparison/compare`, {
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
    const res = await apiFetch(`${API_BASE}/evaluation/report`);
    if (!res.ok) throw new Error('Failed to fetch model evaluation report');
    return res.json();
  },

  /* =========================================================================
     Live Batting Coach Endpoints
     ========================================================================= */

  async processLiveFrame(payload: LiveFrameRequest): Promise<LivePoseState> {
    const res = await apiFetch(`${API_BASE}/live/process-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Live frame processing failed');
    return res.json();
  },

  async analyzeLiveAttempt(payload: LiveAttemptPayload): Promise<LiveAttemptFeedback> {
    const res = await apiFetch(`${API_BASE}/live/analyze-attempt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Live attempt analysis failed');
    return res.json();
  },

  async getLiveSessionAttempts(sessionId: string): Promise<LiveAttemptFeedback[]> {
    const res = await apiFetch(`${API_BASE}/live/session/${sessionId}/attempts`);
    if (!res.ok) throw new Error('Failed to fetch live session attempts');
    return res.json();
  },

  /* =========================================================================
     Biomechanical Progress Tracking Endpoints
     ========================================================================= */

  async getProgressSummary(limit = 200) {
    const res = await apiFetch(`${API_BASE}/progress/summary?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch progress summary');
    return res.json();
  },

  async getProgressShots(): Promise<string[]> {
    const res = await apiFetch(`${API_BASE}/progress/shots`);
    if (!res.ok) throw new Error('Failed to fetch available progress shots');
    return res.json();
  },

  async getShotProgress(shotType: string, limit = 50) {
    const res = await apiFetch(`${API_BASE}/progress/shots/${encodeURIComponent(shotType)}?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to fetch progress trend for ${shotType}`);
    return res.json();
  },

  getWebSocketUrl(sessionId: string): string {
    if (typeof window !== 'undefined') {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = API_BASE.startsWith('http')
        ? new URL(API_BASE).host
        : window.location.host;
      return `${wsProtocol}//${host}/api/live/ws/${sessionId}`;
    }
    return `ws://127.0.0.1:8000/api/live/ws/${sessionId}`;
  },

  getVideoUrl(path: string | null | undefined): string {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    if (typeof window !== 'undefined') {
      const host = API_BASE.startsWith('http') ? new URL(API_BASE).origin : window.location.origin;
      return `${host}${cleanPath}`;
    }
    return `http://127.0.0.1:8000${cleanPath}`;
  },
};
