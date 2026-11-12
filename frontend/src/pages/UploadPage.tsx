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
  const [shotType, setShotType] = useState<string>(initialShotType || 'Cover Drive');
  const [handedness, setHandedness] = useState<string>('Right');
  const [cameraAngle, setCameraAngle] = useState<string>('Side View');
  const [availableShots, setAvailableShots] = useState<CricketShot[]>([]);
  const [strikerInspection, setStrikerInspection] = useState<any>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null);
  const [isInspecting, setIsInspecting] = useState<boolean>(false);

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

  const [uploading, setUploading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pollIntervalRef = useRef<any>(null);

  const checkStrikers = async (file: File) => {
    try {
      setIsInspecting(true);
      const fd = new FormData();
      fd.append('file', file);
      const inspection = await api.inspectStrikers(fd);
      if (inspection && inspection.candidates && inspection.candidates.length > 1) {
        setStrikerInspection(inspection);
        setSelectedTrackId(inspection.default_track_id);
      } else {
        setStrikerInspection(null);
        setSelectedTrackId(inspection?.default_track_id ?? null);
      }
    } catch {
      setStrikerInspection(null);
    } finally {
      setIsInspecting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
      checkStrikers(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
      checkStrikers(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const pollStatus = (sessionId: string) => {
    let consecutiveErrors = 0;
    pollIntervalRef.current = setInterval(async () => {
      try {
        const statusData = await api.getProcessingStatus(sessionId);
        consecutiveErrors = 0; // Reset error streak on successful ping
        setProgress(statusData.progress);
        setProcessingStatus(statusData.current_step);

        if (statusData.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          setUploading(false);
          onSessionCreated(sessionId);
          onSelectTab('workspace');
        } else if (statusData.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          setUploading(false);
          setError(statusData.error || statusData.current_step || 'Video analysis failed. Please check video readability.');
        }
      } catch (err) {
        consecutiveErrors += 1;
        // Don't kill the upload on a transient network delay during heavy 80% video transcoding
        if (consecutiveErrors >= 8) {
          clearInterval(pollIntervalRef.current);
          setUploading(false);
          setError('Lost connection while polling processing status. Please check your network and try again.');
        }
      }
    }, 1500);
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
      setProgress(5);
      setProcessingStatus('Uploading video to backend storage...');

      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('shot_type', shotType);
      formData.append('handedness', handedness);
      formData.append('camera_angle', cameraAngle);
      if (selectedTrackId !== null) {
        formData.append('striker_track_id', selectedTrackId.toString());
      }

      const res = await api.uploadVideo(formData);
      setProgress(15);
      setProcessingStatus('Video queued. Beginning pose extraction...');
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

            {strikerInspection && strikerInspection.candidates && strikerInspection.candidates.length > 1 && (
              <div className="bg-[#111315] border border-amber-600/60 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs font-bold text-amber-300">
                    <Camera className="w-4 h-4 text-amber-400" />
                    <span>Multiple Batters Detected ({strikerInspection.candidates.length})</span>
                  </div>
                  <span className="text-[10px] font-mono text-[#A5A9AD]">Select who is batting</span>
                </div>
                <p className="text-xs text-[#A5A9AD]">
                  Tap or click a candidate below to ensure pose tracking remains locked exclusively onto that batter.
                </p>

                {strikerInspection.frame0_thumbnail_base64 && (
                  <div className="relative max-w-sm mx-auto rounded-lg overflow-hidden border border-[#303438]">
                    <img
                      src={`data:image/jpeg;base64,${strikerInspection.frame0_thumbnail_base64}`}
                      alt="Candidate batters"
                      className="w-full object-cover"
                    />
                    {strikerInspection.candidates.map((c: any) => {
                      const [bx1, by1, bx2, by2] = c.bbox;
                      const isSelected = selectedTrackId === c.track_id;
                      return (
                        <div
                          key={c.track_id}
                          onClick={() => setSelectedTrackId(c.track_id)}
                          style={{
                            left: `${bx1 * 100}%`,
                            top: `${by1 * 100}%`,
                            width: `${(bx2 - bx1) * 100}%`,
                            height: `${(by2 - by1) * 100}%`,
                          }}
                          className={`absolute border-2 cursor-pointer transition-all flex items-start justify-start p-1 ${
                            isSelected
                              ? 'border-[#7FEA35] bg-[#7FEA35]/25 shadow-lg'
                              : 'border-white/60 bg-black/20 hover:border-amber-400'
                          }`}
                        >
                          <span className={`text-[10px] font-mono px-1 py-0.5 rounded font-bold ${
                            isSelected ? 'bg-[#7FEA35] text-black' : 'bg-black/75 text-white'
                          }`}>
                            {c.is_suggested_striker ? '★ Striker' : `Person ${c.track_id}`}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 pt-1">
                  {strikerInspection.candidates.map((c: any) => (
                    <button
                      key={c.track_id}
                      type="button"
                      onClick={() => setSelectedTrackId(c.track_id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition-all cursor-pointer ${
                        selectedTrackId === c.track_id
                          ? 'bg-[#7FEA35] text-black border-[#7FEA35]'
                          : 'bg-[#181B1D] text-[#F5F5F5] border-[#303438] hover:border-[#7FEA35]'
                      }`}
                    >
                      {c.is_suggested_striker ? '★ ' : ''}Person {c.track_id} (Motion: {c.wrist_motion_score})
                    </button>
                  ))}
                </div>
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

            {/* Error Message */}
            {error && (
              <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300 flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold">Upload Error: </strong>
                  <span>{error}</span>
                </div>
              </div>
            )}

            {/* Processing State Progress Bar */}
            {uploading && (
              <div className="bg-navy-900/90 border border-navy-800 p-5 rounded-2xl space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-white flex items-center space-x-2">
                    <Loader2 className="w-4 h-4 text-brand-400 animate-spin" />
                    <span>{processingStatus || 'Processing video...'}</span>
                  </span>
                  <span className="font-mono text-brand-400 font-bold">{progress.toFixed(0)}%</span>
                </div>
                <div className="w-full h-2.5 bg-navy-950 rounded-full overflow-hidden border border-navy-800">
                  <div
                    className="h-full bg-gradient-to-r from-brand-500 to-cricket-sky transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400">
                  Tracking body movement, measuring joint angles, and breaking down stroke phases...
                </p>
              </div>
            )}

            {/* Submit CTA */}
            <button
              type="submit"
              disabled={!selectedFile || uploading}
              className={`w-full py-3.5 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center space-x-2 transition-all shadow-lg ${
                !selectedFile || uploading
                  ? 'bg-navy-800 text-slate-500 cursor-not-allowed border border-navy-700'
                  : 'bg-brand-500 hover:bg-brand-600 text-navy-950 shadow-brand-500/20 transform hover:-translate-y-0.5'
              }`}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing Batting Technique...</span>
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
