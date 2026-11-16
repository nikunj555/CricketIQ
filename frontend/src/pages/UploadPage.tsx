import React, { useState, useRef, useEffect } from 'react';
import {
  Upload,
  Video,
  CheckCircle2,
  AlertCircle,
  Camera,
  Layers,
  ArrowRight,
  Loader2,
  FileVideo
} from 'lucide-react';
import { api } from '../services/api';
import { CricketShot, NavTab } from '../types/cricket';

interface UploadPageProps {
  onSessionCreated: (sessionId: string) => void;
  onSelectTab: (tab: NavTab) => void;
  initialShotType?: string;
}

export const UploadPage: React.FC<UploadPageProps> = ({
  onSessionCreated,
  onSelectTab,
  initialShotType,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [shotType, setShotType] = useState<string>(initialShotType || 'Auto-Detect');
  const [handedness, setHandedness] = useState<string>('Right');
  const [cameraAngle, setCameraAngle] = useState<string>('Side View');
  const [availableShots, setAvailableShots] = useState<CricketShot[]>([]);
  const [strikerInspection, setStrikerInspection] = useState<any>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null);
  const [manualBox, setManualBox] = useState<[number, number, number, number] | null>(null);
  const [isDrawingBox, setIsDrawingBox] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [currentDrag, setCurrentDrag] = useState<{ x: number; y: number } | null>(null);
  const [scrubIndex, setScrubIndex] = useState<number>(0);
  const [isInspecting, setIsInspecting] = useState<boolean>(false);
  const [serverReady, setServerReady] = useState<boolean>(true);
  const [isServerWarmingUp, setIsServerWarmingUp] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    const checkServer = async () => {
      try {
        const h = await api.getHealth();
        if (!mounted) return;
        const ready = h.ready !== false && h.status !== 'warming_up' && h.status !== 'offline';
        setServerReady(ready);
        setIsServerWarmingUp(h.status === 'warming_up' || (!ready && h.status !== 'offline'));
      } catch {
        if (!mounted) return;
        setServerReady(false);
        setIsServerWarmingUp(true);
      }
    };
    checkServer();
    const interval = setInterval(checkServer, 8000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (initialShotType) {
      setShotType(initialShotType);
    }
  }, [initialShotType]);

  useEffect(() => {
    api.getShots().then((res) => {
      setAvailableShots(res.shots);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const [uploading, setUploading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pollIntervalRef = useRef<any>(null);

  const checkStrikers = async (file: File) => {
    try {
      setIsInspecting(true);
      setManualBox(null);
      setScrubIndex(0);
      const fd = new FormData();
      fd.append('file', file);
      const inspection = await api.inspectStrikers(fd);
      if (inspection) {
        setStrikerInspection(inspection);
        setSelectedTrackId(inspection.default_track_id);
      } else {
        setStrikerInspection(null);
        setSelectedTrackId(null);
      }
    } catch {
      setStrikerInspection(null);
    } finally {
      setIsInspecting(false);
    }
  };

  const validateAndSetFile = (file: File): boolean => {
    const validExtensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v'];
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    if (!validExtensions.includes(ext)) {
      setError(`Unsupported video format "${ext}". Please upload a .mp4 or .mov video file (also accepts .webm, .avi, .mkv).`);
      setSelectedFile(null);
      setPreviewUrl(null);
      return false;
    }
    const maxSizeBytes = 150 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds the 150MB limit. Please upload a shorter clip.`);
      setSelectedFile(null);
      setPreviewUrl(null);
      return false;
    }
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
    setStrikerInspection(null);
    setSelectedTrackId(null);
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const pollStatus = (sessionId: string) => {
    let consecutiveErrors = 0;
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const statusData = await api.getProcessingStatus(sessionId);
        consecutiveErrors = 0; // Reset error streak on successful ping

        // Map backend progress (0-100%) smoothly onto overall UI progress (25% -> 99%)
        const backendPct = Math.max(0, Math.min(100, statusData.progress || 0));
        const mappedPct = Math.min(99, Math.round(25 + (backendPct * 0.74)));
        setProgress((prev) => Math.max(prev, mappedPct));
        if (statusData.current_step) {
          setProcessingStatus(statusData.current_step);
        }

        if (statusData.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          setProgress(100);
          setProcessingStatus('Biomechanical analysis complete! Redirecting to workspace...');
          setTimeout(() => {
            setUploading(false);
            onSessionCreated(sessionId);
            onSelectTab('workspace');
          }, 350);
        } else if (statusData.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          setUploading(false);
          setError(statusData.error || statusData.current_step || 'Video analysis failed. Please check video readability.');
        }
      } catch (err: any) {
        consecutiveErrors += 1;
        if (consecutiveErrors > 2) {
          setProcessingStatus(`Connecting to analysis server (reconnecting attempt ${consecutiveErrors}/45)...`);
        }
        // Allow up to 45 consecutive retries (~60s window) for cloud cold-starts or transcoding pauses
        if (consecutiveErrors >= 45) {
          clearInterval(pollIntervalRef.current);
          setUploading(false);
          setError(
            'Lost connection while polling processing status. The server may be restarting or experienced high memory load. Please retry with a shorter clip.'
          );
        }
      }
    }, 1400);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a cricket video file to upload.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setProgress(3);
      setProcessingStatus('Connecting and streaming video to server...');

      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('shot_type', shotType);
      formData.append('handedness', handedness);
      formData.append('camera_angle', cameraAngle);
      if (manualBox) {
        formData.append('manual_crop_box', JSON.stringify(manualBox));
      } else if (selectedTrackId !== null && selectedTrackId !== undefined && !isNaN(Number(selectedTrackId))) {
        formData.append('striker_track_id', selectedTrackId.toString());
      }

      // Stream upload with live byte-level progress reporting and 1x auto-retry on network error
      const onProgress = (percent: number, loaded: number, total: number) => {
        const mbLoaded = (loaded / (1024 * 1024)).toFixed(1);
        const mbTotal = (total / (1024 * 1024)).toFixed(1);
        const uploadProgress = Math.min(25, Math.max(3, Math.round((percent / 100) * 25)));
        setProgress(uploadProgress);
        setProcessingStatus(`Uploading video: ${percent}% (${mbLoaded} MB / ${mbTotal} MB)...`);
      };

      let res;
      try {
        res = await api.uploadVideo(formData, onProgress);
      } catch (firstErr: any) {
        // Auto-retry once on network failure
        setProcessingStatus('Network hiccup during upload. Retrying upload (attempt 2/2)...');
        await new Promise((resolve) => setTimeout(resolve, 2000));
        res = await api.uploadVideo(formData, onProgress);
      }

      setProgress(26);
      setProcessingStatus('Video uploaded. Beginning multi-cue striker isolation & pose extraction...');
      pollStatus(res.session_id);
    } catch (err: any) {
      setUploading(false);
      setError(err.message || 'Failed to upload video');
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center space-x-2">
          <span>Upload & Set Up Batting Video</span>
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Upload a phone camera or net recording to analyze your body movement, front-foot stride, and stroke timing.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Upload & Options */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleUpload} className="space-y-6">
            {/* Drag & Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => !uploading && fileInputRef.current?.click()}
              className={`p-8 border-2 border-dashed rounded-2xl text-center transition-all cursor-pointer ${
                selectedFile
                  ? 'border-brand-500/50 bg-brand-500/5'
                  : 'border-navy-750 bg-navy-900/60 hover:bg-navy-850 hover:border-slate-500'
              } ${uploading ? 'pointer-events-none opacity-80' : ''}`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/quicktime,video/x-msvideo,video/webm"
                className="hidden"
                onChange={handleFileChange}
              />

              {previewUrl ? (
                <div className="space-y-4">
                  <div className="max-w-md mx-auto aspect-video rounded-xl overflow-hidden bg-black border border-navy-800 shadow-md">
                    <video src={previewUrl} controls className="w-full h-full object-contain" />
                  </div>
                  <div className="flex items-center justify-center space-x-2 text-xs font-mono text-brand-400">
                    <FileVideo className="w-4 h-4" />
                    <span className="font-semibold">{selectedFile?.name}</span>
                    <span className="text-slate-500">
                      ({((selectedFile?.size || 0) / (1024 * 1024)).toFixed(1)} MB)
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">Click or drag a different file to replace</p>
                  <div className="flex items-center justify-center space-x-3 pt-1">
                    <button
                      type="button"
                      disabled={isInspecting || uploading}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (selectedFile) checkStrikers(selectedFile);
                      }}
                      className="px-3 py-1.5 text-xs rounded-lg bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white border border-navy-700 flex items-center space-x-1.5 transition-all shadow-sm"
                    >
                      <Camera className="w-3.5 h-3.5 text-brand-400" />
                      <span>{isInspecting ? 'Scanning initial frames...' : 'Verify Batter Identification (Optional)'}</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 py-4">
                  <div className="w-14 h-14 rounded-full bg-navy-800 text-brand-400 flex items-center justify-center mx-auto shadow-inner">
                    <Upload className="w-7 h-7" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-white">
                      Drop cricket video here, or <span className="text-brand-400 underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-400">
                      Supports MP4, MOV, AVI, WEBM (Max 150 MB, up to 300 frames processed)
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Multiple Striker Detection Banner & Candidate Selector */}
            {isInspecting && (
              <div className="flex items-center space-x-2 text-xs text-[#A5A9AD] p-3 rounded-xl bg-[#111315] border border-[#303438]">
                <Loader2 className="w-4 h-4 text-[#7FEA35] animate-spin" />
                <span>Scanning initial frames for batters...</span>
              </div>
            )}

            {strikerInspection && (
              <div className={`bg-[#111315] border rounded-xl p-4 space-y-3.5 ${strikerInspection.needs_confirmation ? 'border-amber-500/80 shadow-lg shadow-amber-950/30' : 'border-[#303438]'}`}>
                {/* Header with Title & Detector Path Badge */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2 text-xs font-bold text-white">
                    <Camera className="w-4 h-4 text-[#7FEA35]" />
                    <span>
                      {strikerInspection.needs_confirmation
                        ? 'Confirm Batting Striker'
                        : `Striker Locked (${strikerInspection.candidates?.length || 0} People Detected)`}
                    </span>
                  </div>

                  {/* Which Path Ran: Roboflow or Fallback */}
                  <div className="flex items-center space-x-2">
                    {strikerInspection.detection_source === 'roboflow' ? (
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[10px] font-mono">
                        ✓ Roboflow RF-DETR Active ({strikerInspection.roboflow_calls_used || 1} API calls)
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-mono">
                        {strikerInspection.detector_status || 'degraded: detector unavailable'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Honest Message & Reason */}
                <p className="text-xs text-[#A5A9AD]">
                  {strikerInspection.confirmation_message ||
                    (strikerInspection.needs_confirmation
                      ? 'Striker confidence is low or multiple people are near the crease. Tap a candidate box or drag a custom box around the batter.'
                      : 'Pose tracking is locked onto the highlighted striker. You can also drag a custom box anywhere on the frame.')}
                </p>

                {/* Camera Perspective Warning (e.g. Behind Bowler) */}
                {strikerInspection.camera_warning && (
                  <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-200 flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <span>{strikerInspection.camera_warning}</span>
                  </div>
                )}

                {/* Frame Scrubber (Frame 0, 5, 10, 15, 20) */}
                {strikerInspection.scrub_frames && strikerInspection.scrub_frames.length > 1 && (
                  <div className="flex items-center space-x-2 pt-1 pb-1">
                    <span className="text-[10px] font-mono uppercase text-[#A5A9AD]">Scrub Frame:</span>
                    <div className="flex space-x-1.5">
                      {strikerInspection.scrub_frames.map((sf: any, idx: number) => (
                        <button
                          key={sf.frame_idx}
                          type="button"
                          onClick={() => setScrubIndex(idx)}
                          className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                            scrubIndex === idx
                              ? 'bg-[#7FEA35] text-black font-bold'
                              : 'bg-[#181B1D] text-[#A5A9AD] hover:text-white border border-[#303438]'
                          }`}
                        >
                          F{sf.frame_idx}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Interactive Frame Canvas with Click/Drag Box Selection */}
                {(() => {
                  const activeImgUrl =
                    (strikerInspection.scrub_frames && strikerInspection.scrub_frames[scrubIndex]?.data_url) ||
                    strikerInspection.frame_0_data_url ||
                    (strikerInspection.frame0_thumbnail_base64 && `data:image/jpeg;base64,${strikerInspection.frame0_thumbnail_base64}`);

                  if (!activeImgUrl) return null;

                  return (
                    <div className="flex flex-col sm:flex-row gap-4 items-start">
                      <div
                        className="relative max-w-sm w-full mx-auto sm:mx-0 rounded-lg overflow-hidden border border-[#303438] cursor-crosshair select-none bg-black"
                        onMouseDown={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                          const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
                          setDragStart({ x, y });
                          setCurrentDrag({ x, y });
                          setIsDrawingBox(true);
                        }}
                        onMouseMove={(e) => {
                          if (!isDrawingBox) return;
                          const rect = e.currentTarget.getBoundingClientRect();
                          const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                          const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
                          setCurrentDrag({ x, y });
                        }}
                        onMouseUp={() => {
                          if (!dragStart || !currentDrag) {
                            setIsDrawingBox(false);
                            return;
                          }
                          const dx = Math.abs(currentDrag.x - dragStart.x);
                          const dy = Math.abs(currentDrag.y - dragStart.y);
                          if (dx > 0.02 && dy > 0.02) {
                            const x1 = Math.min(dragStart.x, currentDrag.x);
                            const y1 = Math.min(dragStart.y, currentDrag.y);
                            const x2 = Math.max(dragStart.x, currentDrag.x);
                            const y2 = Math.max(dragStart.y, currentDrag.y);
                            setManualBox([x1, y1, x2, y2]);
                            setSelectedTrackId(null);
                          } else {
                            // Clicked a single point: create default batter box centered at point
                            const cx = dragStart.x;
                            const cy = dragStart.y;
                            setManualBox([
                              Math.max(0, cx - 0.075),
                              Math.max(0, cy - 0.175),
                              Math.min(1, cx + 0.075),
                              Math.min(1, cy + 0.175),
                            ]);
                            setSelectedTrackId(null);
                          }
                          setIsDrawingBox(false);
                          setDragStart(null);
                          setCurrentDrag(null);
                        }}
                      >
                        <img
                          src={activeImgUrl}
                          alt="Video frame"
                          className="w-full object-contain pointer-events-none"
                        />

                        {/* Detector / Pose Candidates */}
                        {(!manualBox) && strikerInspection.candidates?.map((c: any) => {
                          const [bx1, by1, bx2, by2] = c.bbox;
                          const isSelected = selectedTrackId === c.track_id;
                          return (
                            <div
                              key={c.track_id}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedTrackId(c.track_id);
                                setManualBox(null);
                              }}
                              style={{
                                left: `${bx1 * 100}%`,
                                top: `${by1 * 100}%`,
                                width: `${(bx2 - bx1) * 100}%`,
                                height: `${(by2 - by1) * 100}%`,
                              }}
                              className={`absolute border-2 cursor-pointer transition-all flex items-start justify-start p-0.5 ${
                                isSelected
                                  ? 'border-[#7FEA35] bg-[#7FEA35]/25 shadow-lg'
                                  : 'border-white/50 bg-black/20 hover:border-amber-400'
                              }`}
                            >
                              <span className={`text-[9px] font-mono px-1 py-0.2 rounded font-bold ${
                                isSelected ? 'bg-[#7FEA35] text-black' : 'bg-black/75 text-white'
                              }`}>
                                {c.is_default ? '★ Striker' : (c.class_name || `P${c.track_id}`)}
                              </span>
                            </div>
                          );
                        })}

                        {/* Live Drawing Box */}
                        {isDrawingBox && dragStart && currentDrag && (
                          <div
                            style={{
                              left: `${Math.min(dragStart.x, currentDrag.x) * 100}%`,
                              top: `${Math.min(dragStart.y, currentDrag.y) * 100}%`,
                              width: `${Math.abs(currentDrag.x - dragStart.x) * 100}%`,
                              height: `${Math.abs(currentDrag.y - dragStart.y) * 100}%`,
                            }}
                            className="absolute border-2 border-dashed border-[#7FEA35] bg-[#7FEA35]/20 pointer-events-none"
                          />
                        )}

                        {/* Confirmed Manual Box */}
                        {manualBox && (
                          <div
                            style={{
                              left: `${manualBox[0] * 100}%`,
                              top: `${manualBox[1] * 100}%`,
                              width: `${(manualBox[2] - manualBox[0]) * 100}%`,
                              height: `${(manualBox[3] - manualBox[1]) * 100}%`,
                            }}
                            className="absolute border-2 border-[#7FEA35] bg-[#7FEA35]/30 shadow-lg flex items-start justify-between p-1"
                          >
                            <span className="text-[9px] font-mono px-1 py-0.5 rounded font-bold bg-[#7FEA35] text-black">
                              ★ Custom Batter
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Zoomed Crop Preview */}
                      {manualBox && (
                        <div className="bg-[#181B1D] border border-[#303438] rounded-xl p-3 space-y-2 flex flex-col items-center shrink-0">
                          <span className="text-[10px] font-mono text-[#A5A9AD] uppercase font-bold">
                            Zoomed Batter Crop
                          </span>
                          <div className="w-28 h-36 rounded-lg overflow-hidden border border-[#7FEA35]/60 bg-black relative">
                            <img
                              src={activeImgUrl}
                              alt="Crop preview"
                              style={{
                                position: 'absolute',
                                left: `-${(manualBox[0] / Math.max(0.01, manualBox[2] - manualBox[0])) * 100}%`,
                                top: `-${(manualBox[1] / Math.max(0.01, manualBox[3] - manualBox[1])) * 100}%`,
                                width: `${(1 / Math.max(0.01, manualBox[2] - manualBox[0])) * 100}%`,
                                height: `${(1 / Math.max(0.01, manualBox[3] - manualBox[1])) * 100}%`,
                                maxWidth: 'none',
                              }}
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setManualBox(null);
                              setSelectedTrackId(strikerInspection.default_track_id);
                            }}
                            className="text-[10px] font-mono text-rose-400 hover:text-rose-300 underline"
                          >
                            Reset to automatic
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Candidate Selection Pills */}
                {strikerInspection.candidates && strikerInspection.candidates.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {strikerInspection.candidates.map((c: any) => {
                      const isSel = (!manualBox && selectedTrackId === c.track_id);
                      return (
                        <button
                          key={c.track_id}
                          type="button"
                          onClick={() => {
                            setSelectedTrackId(c.track_id);
                            setManualBox(null);
                          }}
                          className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition-all cursor-pointer ${
                            isSel
                              ? 'bg-[#7FEA35] text-black border-[#7FEA35]'
                              : 'bg-[#181B1D] text-[#F5F5F5] border-[#303438] hover:border-[#7FEA35]'
                          }`}
                        >
                          {isSel ? '★ ' : ''}
                          {c.class_name ? c.class_name.replace('_', ' ').toUpperCase() : `PERSON ${c.track_id}`}
                          {c.striker_score != null && ` (${Math.round(c.striker_score * 100)}%)`}
                          {c.is_small_target && ' [Distant]'}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            <div className="bg-navy-900/80 p-6 rounded-2xl border border-navy-800 space-y-5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Shot Metadata & Stance Options
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Shot Type */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-300">Batting Stroke</label>
                    <span className="text-[10px] text-brand-400 font-mono">25 Shots Supported</span>
                  </div>
                  <select
                    value={shotType}
                    onChange={(e) => setShotType(e.target.value)}
                    disabled={uploading}
                    className="w-full bg-navy-950 border border-navy-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-sans"
                  >
                    <option value="Auto-Detect" className="bg-[#111315] text-[#7FEA35] font-bold">
                      ✨ Auto-Detect via AI Kinematics
                    </option>
                    {availableShots.length > 0 ? (
                      Array.from(new Set(availableShots.map((s) => s.category))).map((cat) => (
                        <optgroup key={cat} label={cat} className="bg-navy-900 text-brand-400 font-bold">
                          {availableShots
                            .filter((s) => s.category === cat)
                            .map((s) => (
                              <option key={s.id} value={s.name} className="bg-navy-950 text-white font-normal">
                                {s.name} {s.reference_status === 'available' ? '★' : ''}
                              </option>
                            ))}
                        </optgroup>
                      ))
                    ) : (
                      <>
                        <option value="Cover Drive">Cover Drive ★</option>
                        <option value="Straight Drive">Straight Drive ★</option>
                        <option value="Pull Shot">Pull Shot ★</option>
                        <option value="Forward Defensive">Forward Defensive ★</option>
                        <option value="Square Cut">Square Cut</option>
                        <option value="Sweep">Sweep</option>
                      </>
                    )}
                  </select>
                  <p className="text-[10px] text-slate-400">
                    CricketIQ verifies pose kinematics and allows confirming or overriding the detected shot.
                  </p>
                </div>

                {/* Handedness */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300">Batsman Handedness</label>
                  <div className="grid grid-cols-2 gap-1 bg-navy-950 p-1 rounded-lg border border-navy-800">
                    <button
                      type="button"
                      disabled={uploading}
                      onClick={() => setHandedness('Right')}
                      className={`py-1.5 text-xs rounded font-medium transition-all ${
                        handedness === 'Right'
                          ? 'bg-brand-500 text-navy-950 font-bold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Right-Hand
                    </button>
                    <button
                      type="button"
                      disabled={uploading}
                      onClick={() => setHandedness('Left')}
                      className={`py-1.5 text-xs rounded font-medium transition-all ${
                        handedness === 'Left'
                          ? 'bg-brand-500 text-navy-950 font-bold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Left-Hand
                    </button>
                  </div>
                </div>

                {/* Camera Angle */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300">Camera Angle</label>
                  <select
                    value={cameraAngle}
                    onChange={(e) => setCameraAngle(e.target.value)}
                    disabled={uploading}
                    className="w-full bg-navy-950 border border-navy-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                  >
                    <option value="Side View">Side View (Recommended)</option>
                    <option value="Oblique View">Oblique (45° Angle)</option>
                    <option value="Front View">Front-On (Bowler's End)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Server Waking Up Banner */}
            {!serverReady && (
              <div className="p-3.5 rounded-xl bg-amber-500/15 border border-amber-500/40 text-xs text-amber-200 flex items-center space-x-2.5">
                <Loader2 className="w-4 h-4 text-amber-400 animate-spin shrink-0" />
                <div>
                  <strong className="font-semibold">Waking up the server, this can take a minute. </strong>
                  <span className="text-amber-200/90">The upload button will enable automatically as soon as the AI models are ready.</span>
                </div>
              </div>
            )}

            {/* Error Message with Retry */}
            {error && (
              <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300 flex items-start justify-between space-x-2.5">
                <div className="flex items-start space-x-2.5 min-w-0">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold">Upload Error: </strong>
                    <span className="break-words">{error}</span>
                  </div>
                </div>
                {selectedFile && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      handleUpload(e);
                    }}
                    className="ml-4 px-3 py-1 bg-rose-800 hover:bg-rose-700 text-white rounded font-medium text-xs whitespace-nowrap shrink-0 transition-colors cursor-pointer"
                  >
                    Retry Analysis
                  </button>
                )}
              </div>
            )}

            {/* Processing State Progress Bar */}
            {uploading && (
              <div className="bg-navy-900/90 border border-navy-800 p-5 rounded-2xl space-y-4 shadow-xl">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-white flex items-center space-x-2 truncate pr-2">
                    <Loader2 className="w-4 h-4 text-brand-400 animate-spin shrink-0" />
                    <span className="truncate">{processingStatus || 'Processing video...'}</span>
                  </span>
                  <span className="font-mono text-brand-400 font-bold shrink-0">{progress.toFixed(0)}%</span>
                </div>
                
                <div className="w-full h-3 bg-navy-950 rounded-full overflow-hidden border border-navy-800/80 p-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-brand-500 via-emerald-400 to-cyan-400 rounded-full transition-all duration-500 ease-out shadow-sm"
                    style={{ width: `${Math.max(2, progress)}%` }}
                  />
                </div>

                {/* Processing Phase Step Pills */}
                <div className="grid grid-cols-4 gap-2 text-[10px] text-center font-mono pt-1">
                  <div className={`px-1.5 py-1 rounded transition-colors ${progress >= 3 && progress <= 25 ? 'bg-brand-500/20 text-brand-300 font-bold border border-brand-500/40' : progress > 25 ? 'text-slate-400' : 'text-slate-600'}`}>
                    1. Upload
                  </div>
                  <div className={`px-1.5 py-1 rounded transition-colors ${progress > 25 && progress <= 50 ? 'bg-brand-500/20 text-brand-300 font-bold border border-brand-500/40' : progress > 50 ? 'text-slate-400' : 'text-slate-600'}`}>
                    2. Striker Lock
                  </div>
                  <div className={`px-1.5 py-1 rounded transition-colors ${progress > 50 && progress <= 78 ? 'bg-brand-500/20 text-brand-300 font-bold border border-brand-500/40' : progress > 78 ? 'text-slate-400' : 'text-slate-600'}`}>
                    3. Kinematics
                  </div>
                  <div className={`px-1.5 py-1 rounded transition-colors ${progress > 78 ? 'bg-brand-500/20 text-brand-300 font-bold border border-brand-500/40' : 'text-slate-600'}`}>
                    4. Render Video
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Real-time pipeline tracking: isolating the batsman, extracting 33 kinematic landmarks, recognizing stroke phases, and rendering annotated video.
                </p>
              </div>
            )}

            {/* Submit CTA */}
            <button
              type="submit"
              disabled={!selectedFile || uploading || !serverReady}
              className={`w-full py-3.5 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center space-x-2 transition-all shadow-lg ${
                !selectedFile || uploading || !serverReady
                  ? 'bg-navy-800 text-slate-500 cursor-not-allowed border border-navy-700'
                  : 'bg-brand-500 hover:bg-brand-600 text-navy-950 shadow-brand-500/20 transform hover:-translate-y-0.5'
              }`}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing Batting Technique...</span>
                </>
              ) : !serverReady ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                  <span>{isServerWarmingUp ? 'Waking up the server, this can take a minute...' : 'Waiting for AI engine initialization...'}</span>
                </>
              ) : (
                <>
                  <Video className="w-4 h-4" />
                  <span>Start Biomechanical Analysis</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Camera & Best Practice Guidance */}
        <div className="space-y-5">
          <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Camera className="w-4 h-4 text-brand-400" />
              <span>Camera Setup Guidance</span>
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              To maximize landmark detection confidence and ensure biomechanical validity:
            </p>

            <ul className="space-y-3 text-xs text-slate-300">
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Full Body Visibility: </strong>Ensure helmet, torso, legs, and feet are visible throughout the entire stroke.
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Side-On Perspective: </strong>Position phone at crease level (~90° to pitch) for optimal knee flexion and spine angle calculation.
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Stable Mounting: </strong>Keep the tripod or phone holder stable to avoid misleading camera shake in head displacement tracking.
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Lighting & Contrast: </strong>Avoid heavy backlighting directly behind the batsman to prevent limb silhouette occlusion.
                </span>
              </li>
            </ul>

            <div className="p-3 rounded-xl bg-navy-950 border border-navy-800 text-[11px] text-slate-400 space-y-1">
              <strong className="text-slate-300 font-semibold">Important Methodology Note:</strong>
              <p>
                A single camera angle captures 2D image projections. Measurements reflect projected sagittal or frontal planes and do not constitute 3D motion-capture clinical telemetry.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
