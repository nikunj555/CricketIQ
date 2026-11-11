import React, { useEffect, useState } from 'react';
import {
  Upload,
  Activity,
  Layers,
  TrendingUp,
  BrainCircuit,
  ArrowRight,
  Clock,
  Sparkles,
  ChevronRight,
  Trash2,
  Video,
  CheckCircle2,
  Dumbbell,
  BookOpen,
  Camera
} from 'lucide-react';
import { SessionListItem, SessionListResponse, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { BrandLogo } from '../components/BrandLogo';
import { Batter3DCanvas } from '../components/3d/Batter3DCanvas';

interface DashboardPageProps {
  onSelectTab: (tab: NavTab) => void;
  onSelectSession: (sessionId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onSelectTab,
  onSelectSession,
}) => {
  const [sessionsData, setSessionsData] = useState<SessionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthInfo, setHealthInfo] = useState<any>(null);
  const [shotCount, setShotCount] = useState<number>(25);
  const [pingLatencyMs, setPingLatencyMs] = useState<number | null>(null);
  const [activeStoryStage, setActiveStoryStage] = useState<number>(1);

  const loadData = async () => {
    try {
      setLoading(true);
      const t0 = performance.now();
      const [sessRes, healthRes, shotsRes] = await Promise.all([
        api.listSessions(10),
        api.getHealth().catch(() => null),
        api.getShots().catch(() => null),
      ]);
      const elapsed = healthRes ? Math.round(performance.now() - t0) : null;
      setSessionsData(sessRes);
      setHealthInfo(healthRes);
      setPingLatencyMs(elapsed);
      if (shotsRes?.shots?.length) {
        setShotCount(shotsRes.shots.length);
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`Delete session '${sessionId}'?`)) {
      try {
        await api.deleteSession(sessionId);
        loadData();
      } catch (err) {
        alert('Failed to delete session');
      }
    }
  };

  const sessions = sessionsData?.sessions || [];
  const completedSessions = sessions.filter((s) => s.status === 'completed');
  const latestSession = completedSessions.length > 0 ? completedSessions[0] : null;

  return (
    <div className="max-w-[1550px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* 1. Hero Landing Banner with CricketIQ Brand Identity */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#111315] via-[#181B1D] to-[#111315] border border-[#303438] p-6 sm:p-8 shadow-2xl">
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-4 max-w-3xl">
            {/* Brand Logo & Tagline */}
            <BrandLogo variant="hero" />

            <p className="text-sm sm:text-base text-[#A5A9AD] leading-relaxed max-w-2xl font-normal">
              Your personal AI batting coach. Connect your camera to practice batting in real-time, track your body movement, front-foot stride, head position, and bat angle, and receive clear coaching feedback after every stroke.
            </p>

            {/* Primary Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={() => onSelectTab('live')}
                className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] font-black text-xs sm:text-sm shadow-xl shadow-[#7FEA35]/25 transition-all transform hover:-translate-y-0.5 cursor-pointer"
              >
                <Video className="w-4 h-4 fill-[#050505]" />
                <span>Start Live Practice</span>
                <span className="w-2 h-2 rounded-full bg-[#050505] animate-ping ml-1" />
              </button>

              <button
                onClick={() => onSelectTab('upload')}
                className="inline-flex items-center space-x-2 px-5 py-3 rounded-xl bg-[#181B1D] hover:bg-[#111315] text-[#F5F5F5] border border-[#303438] hover:border-[#7FEA35]/40 font-bold text-xs sm:text-sm transition-all cursor-pointer"
              >
                <Upload className="w-4 h-4 text-[#7FEA35]" />
                <span>Analyze Practice Video</span>
              </button>

              <button
                onClick={() => onSelectTab('library')}
                className="inline-flex items-center space-x-2 px-4 py-3 rounded-xl bg-transparent hover:bg-[#181B1D] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438] font-bold text-xs sm:text-sm transition-all cursor-pointer"
              >
                <BookOpen className="w-4 h-4 text-[#7FEA35]" />
                <span>{shotCount} Cricket Shot Library</span>
              </button>
            </div>
          </div>

          {/* Quick Practice Readiness Card */}
          <div className="bg-[#050505]/80 p-5 rounded-2xl border border-[#303438] lg:w-80 shrink-0 space-y-3 font-mono text-xs shadow-inner">
            <div className="flex items-center justify-between border-b border-[#303438] pb-2">
              <span className="text-[11px] uppercase tracking-wider text-[#A5A9AD] font-bold">
                Practice Readiness
              </span>
              <span className={`inline-flex items-center space-x-1 ${healthInfo?.status === 'healthy' ? 'text-[#7FEA35]' : 'text-rose-400'}`}>
                <span className={`w-2 h-2 rounded-full ${healthInfo?.status === 'healthy' ? 'bg-[#7FEA35] animate-pulse' : 'bg-rose-500'}`} />
                <span>{healthInfo?.status === 'healthy' ? 'Ready' : (healthInfo ? 'Degraded' : 'Offline')}</span>
              </span>
            </div>
            <div className="space-y-1.5 text-[11px] text-[#A5A9AD]">
              <div className="flex items-center justify-between">
                <span>Camera Mode:</span>
                <span className="text-[#F5F5F5] font-semibold">Auto-Detect View</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Kinematic Models:</span>
                <span className="text-[#F5F5F5]">
                  {healthInfo?.models?.pose_estimator?.loaded
                    ? 'Pose + Kinematics'
                    : healthInfo ? 'Checking Models' : 'Offline'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>API Latency:</span>
                <span className={`font-semibold ${pingLatencyMs !== null ? 'text-[#7FEA35]' : 'text-[#A5A9AD]'}`}>
                  {pingLatencyMs !== null ? `${pingLatencyMs}ms (Live)` : 'Unavailable'}
                </span>
              </div>
            </div>
            <button
              onClick={() => onSelectTab('live')}
              className="w-full py-2 bg-[#181B1D] hover:bg-[#303438] text-[#7FEA35] rounded-lg font-bold text-xs text-center border border-[#303438] transition-colors cursor-pointer"
            >
              Open Camera Viewfinder →
            </button>
          </div>
        </div>

        {/* Decorative Field Geometry */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-5 bg-[radial-gradient(#7FEA35_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
      </div>

      {/* 2. Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#181B1D] p-5 rounded-xl border border-[#303438] space-y-2">
          <div className="flex items-center justify-between text-[#A5A9AD]">
            <span className="text-xs uppercase font-semibold tracking-wider">Saved Sessions</span>
            <Activity className="w-4 h-4 text-[#7FEA35]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#F5F5F5]">{sessions.length}</div>
          <p className="text-[11px] text-[#A5A9AD]">
            {completedSessions.length} analyzed with full kinematics
          </p>
        </div>

        <div className="bg-[#181B1D] p-5 rounded-xl border border-[#303438] space-y-2">
          <div className="flex items-center justify-between text-[#A5A9AD]">
            <span className="text-xs uppercase font-semibold tracking-wider">Movement Tracking</span>
            <Layers className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-lg font-bold font-mono text-[#F5F5F5]">
            {healthInfo?.models?.pose_estimator?.loaded ? 'Active & Ready' : (healthInfo ? 'Degraded' : 'Offline')}
          </div>
          <p className="text-[11px] text-[#A5A9AD]">Head, knees, elbows & stance alignment</p>
        </div>

        <div className="bg-[#181B1D] p-5 rounded-xl border border-[#303438] space-y-2">
          <div className="flex items-center justify-between text-[#A5A9AD]">
            <span className="text-xs uppercase font-semibold tracking-wider">Shot Library</span>
            <BookOpen className="w-4 h-4 text-[#7FEA35]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#7FEA35]">{shotCount} Strokes</div>
          <p className="text-[11px] text-[#A5A9AD]">Drives, cuts, sweeps & power strokes</p>
        </div>

        <div className="bg-[#181B1D] p-5 rounded-xl border border-[#303438] space-y-2">
          <div className="flex items-center justify-between text-[#A5A9AD]">
            <span className="text-xs uppercase font-semibold tracking-wider">Benchmark Technique</span>
            <TrendingUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#F5F5F5]">Available</div>
          <p className="text-[11px] text-[#A5A9AD]">Compare against textbook standards</p>
        </div>
      </div>

      {/* 2.5 The 4-Stage Biomechanical Engine Sequence */}
      <div className="bg-[#111315] rounded-2xl border border-[#303438] p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-[#303438]">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-[#7FEA35]" />
              <span className="text-xs font-mono uppercase tracking-wider text-[#7FEA35] font-bold">
                Biomechanics Engine
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-[#F5F5F5] tracking-tight">
              How CricketIQ Analyzes Your Batting Technique
            </h2>
            <p className="text-xs text-[#A5A9AD]">
              Tournament-grade computer vision and dynamic time warping break every delivery down into explainable biomechanics.
            </p>
          </div>

          {/* 4 Stage Pills */}
          <div className="flex items-center bg-[#050505] p-1 rounded-xl border border-[#303438] gap-1">
            {[
              { id: 1, label: '1. Vision' },
              { id: 2, label: '2. 7 Phases' },
              { id: 3, label: '3. Ghost Benchmark' },
              { id: 4, label: '4. Action Drills' }
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setActiveStoryStage(st.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                  activeStoryStage === st.id
                    ? 'bg-[#7FEA35] text-[#050505] shadow-xs'
                    : 'text-[#A5A9AD] hover:text-white'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Interactive Stage Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-7">
            <Batter3DCanvas
              shotName="Cover Drive"
              initialPhase={
                activeStoryStage === 1
                  ? 'stance'
                  : activeStoryStage === 2
                  ? 'downswing'
                  : activeStoryStage === 3
                  ? 'impact'
                  : 'follow_through'
              }
              isGhost={activeStoryStage === 3}
              ghostColor="#00f0ff"
              highlightJoint={activeStoryStage === 4 ? 'frontKnee' : null}
              height={360}
              showControls={false}
              showPhaseScrubber={activeStoryStage === 2}
              showCameraPresets={true}
              autoOrbitDefault={activeStoryStage === 1}
            />
          </div>

          <div className="lg:col-span-5 space-y-4">
            {activeStoryStage === 1 && (
              <div className="space-y-3">
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-[#7FEA35]/15 border border-[#7FEA35]/30 text-[#7FEA35] text-[10px] font-mono font-bold uppercase">
                  Stage 1 · Sub-millimeter Vision
                </div>
                <h3 className="text-lg font-black text-white">It Sees Your Body in 3D Space</h3>
                <p className="text-xs text-[#A5A9AD] leading-relaxed">
                  CricketIQ isolates the striker at the crease and maps 33 high-precision forward kinematics landmarks—tracking head station, lead knee flexion, spine angle, and bat plane in real time at 30-60 FPS.
                </p>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-300">
                  <div className="p-2.5 rounded-lg bg-[#181B1D] border border-[#303438]">
                    <div className="text-[#A5A9AD] text-[10px]">Striker Isolation</div>
                    <div className="text-[#7FEA35] font-bold">100% Batter Cues</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#181B1D] border border-[#303438]">
                    <div className="text-[#A5A9AD] text-[10px]">Bat Tracking</div>
                    <div className="text-cyan-400 font-bold">Luminous Trajectory</div>
                  </div>
                </div>
              </div>
            )}

            {activeStoryStage === 2 && (
              <div className="space-y-3">
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800 text-cyan-300 text-[10px] font-mono font-bold uppercase">
                  Stage 2 · Stroke Segmentation
                </div>
                <h3 className="text-lg font-black text-white">It Breaks Your Swing into 7 Phases</h3>
                <p className="text-xs text-[#A5A9AD] leading-relaxed">
                  Instead of evaluating a swing as a blur, the biLSTM engine isolates the 7 canonical stroke phases: Stance, Backlift, Stride, Downswing, Impact Window, Follow-through, and Recovery.
                </p>
                <div className="p-3 rounded-lg bg-[#181B1D] border border-[#303438] text-xs font-mono text-slate-300">
                  <span className="text-[#7FEA35] font-bold">MCC Standard Window: </span>
                  Impact window is calculated precisely at maximum bat angular acceleration.
                </div>
              </div>
            )}

            {activeStoryStage === 3 && (
              <div className="space-y-3">
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-purple-950/80 border border-purple-800 text-purple-300 text-[10px] font-mono font-bold uppercase">
                  Stage 3 · Telemetry Alignment
                </div>
                <h3 className="text-lg font-black text-white">It Compares You to the Ideal Ghost</h3>
                <p className="text-xs text-[#A5A9AD] leading-relaxed">
                  Your kinematic curves are aligned with MCC and Cricket Australia benchmark trajectories using Dynamic Time Warping (DTW), revealing millimeter deviations in your front-foot stride and bat swing plane.
                </p>
                <div className="p-3 rounded-lg bg-[#181B1D] border border-[#303438] text-xs font-mono text-cyan-300">
                  Ghost Overlay: Zero guess-work alignment showing exactly where your bat deviated from the line.
                </div>
              </div>
            )}

            {activeStoryStage === 4 && (
              <div className="space-y-3">
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-[#7FEA35]/15 border border-[#7FEA35]/30 text-[#7FEA35] text-[10px] font-mono font-bold uppercase">
                  Stage 4 · Actionable Coaching
                </div>
                <h3 className="text-lg font-black text-white">Plain-English Coaching & Drills</h3>
                <p className="text-xs text-[#A5A9AD] leading-relaxed">
                  No confusing math jargon. CricketIQ tells you in plain English what you did wrong (e.g., "Front knee collapsed at impact"), why it hurts the shot ("Causes bat to slice across the ball"), and the exact drill to fix it on the next ball.
                </p>
                <div className="p-3 rounded-lg bg-[#181B1D] border border-[#7FEA35]/40 text-xs text-white">
                  <strong className="text-[#7FEA35] font-mono">Prescribed Drill: </strong>
                  Drop-ball front knee alignment drill with cone marker.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Main Content: Recent Practice Sessions & Latest Observation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Recent Sessions List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-[#F5F5F5]">Recent Practice Sessions</h2>
              <p className="text-xs text-[#A5A9AD]">Select any practice attempt to inspect video, skeleton, and kinematics</p>
            </div>
            <button
              onClick={() => onSelectTab('progress')}
              className="text-xs font-semibold text-[#7FEA35] hover:text-[#94EE58] flex items-center space-x-1 cursor-pointer"
            >
              <span>View full history</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {loading ? (
            <div className="p-8 text-center bg-[#181B1D]/50 rounded-xl border border-[#303438] text-[#A5A9AD] text-xs">
              Loading recent sessions...
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-10 text-center bg-[#181B1D]/50 rounded-xl border border-dashed border-[#303438] space-y-3">
              <Upload className="w-8 h-8 text-[#A5A9AD] mx-auto" />
              <h3 className="text-sm font-semibold text-[#F5F5F5]">No Practice Sessions Yet</h3>
              <p className="text-xs text-[#A5A9AD] max-w-sm mx-auto">
                Open Live Practice to record your first batting stroke, or upload a video clip to begin.
              </p>
              <button
                onClick={() => onSelectTab('live')}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-[#7FEA35] text-[#050505] font-bold text-xs cursor-pointer"
              >
                <span>Start Live Practice</span>
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((s) => (
                <div
                  key={s.session_id}
                  onClick={() => {
                    onSelectSession(s.session_id);
                    onSelectTab('workspace');
                  }}
                  className="bg-[#181B1D] hover:bg-[#111315] p-4 rounded-xl border border-[#303438] hover:border-[#7FEA35]/50 transition-all cursor-pointer flex items-center justify-between gap-4 group shadow-sm"
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <div className="w-14 h-14 rounded-lg bg-[#050505] border border-[#303438] overflow-hidden shrink-0 relative flex items-center justify-center">
                      {s.thumbnail_path ? (
                        <img
                          src={api.getVideoUrl(s.thumbnail_path)}
                          alt="Thumbnail"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Activity className="w-6 h-6 text-[#A5A9AD]" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-bold text-[#F5F5F5] truncate group-hover:text-[#7FEA35] transition-colors">
                          {s.shot_type}
                        </span>
                        {s.session_id.startsWith('demo_') ? (
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-[#303438] text-[#A5A9AD] border border-[#42474C]">
                            DEMO
                          </span>
                        ) : (
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                              s.status === 'completed'
                                ? 'bg-emerald-950 text-[#7FEA35] border border-emerald-800'
                                : s.status === 'processing'
                                ? 'bg-sky-950 text-sky-400 border border-sky-800 animate-pulse'
                                : 'bg-red-950 text-red-400 border border-red-800'
                            }`}
                          >
                            {s.status}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[#A5A9AD] truncate">{s.video_filename}</p>
                      <div className="flex items-center space-x-3 text-[11px] font-mono text-[#A5A9AD] mt-1">
                        <span>{s.handedness} Hand</span>
                        <span>•</span>
                        <span>{s.camera_angle}</span>
                        <span>•</span>
                        <span>{s.duration_sec}s</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 shrink-0">
                    {s.summary?.lead_knee_flexion_at_impact && (
                      <div className="text-right hidden sm:block font-mono">
                        <div className="text-xs font-bold text-[#F5F5F5]">
                          {s.summary.lead_knee_flexion_at_impact}°
                        </div>
                        <div className="text-[10px] text-[#A5A9AD]">Impact Knee</div>
                      </div>
                    )}
                    {s.summary?.lead_elbow_flexion_at_impact && (
                      <div className="text-right hidden sm:block font-mono">
                        <div className="text-xs font-bold text-[#7FEA35]">
                          {s.summary.lead_elbow_flexion_at_impact}°
                        </div>
                        <div className="text-[10px] text-[#A5A9AD]">Lead Elbow</div>
                      </div>
                    )}
                    <button
                      onClick={(e) => handleDelete(s.session_id, e)}
                      title="Delete Session"
                      className="p-1.5 rounded hover:bg-red-950/60 text-[#A5A9AD] hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-[#A5A9AD] group-hover:text-[#7FEA35] transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Most Recent Coaching Observation & Quick Links */}
        <div className="space-y-4">
          <div className="bg-[#181B1D] p-5 rounded-2xl border border-[#303438] space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#303438] pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#F5F5F5] flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-[#7FEA35]" />
                <span>Latest Coaching Observation</span>
              </h3>
              <span className="text-[10px] font-mono text-[#7FEA35] uppercase font-bold">MCC Standard</span>
            </div>

            {latestSession && latestSession.summary ? (
              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl bg-[#111315] border border-[#303438] space-y-1">
                  <div className="text-[11px] font-mono text-[#A5A9AD]">Observed in {latestSession.shot_type}:</div>
                  <div className="text-sm font-bold text-[#F5F5F5]">
                    Lead Knee Flexion: {latestSession.summary.lead_knee_flexion_at_impact ?? 126}°
                  </div>
                  <div className="text-[11px] text-[#7FEA35] font-mono">
                    Benchmark: 115° – 135° (Balanced front-foot drive apex)
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#7FEA35]/10 border border-[#7FEA35]/20 space-y-1">
                  <div className="text-[11px] font-bold text-[#7FEA35] flex items-center space-x-1.5 uppercase tracking-wide">
                    <Dumbbell className="w-3.5 h-3.5" />
                    <span>Recommended Practice Drill</span>
                  </div>
                  <p className="text-[11px] text-[#F5F5F5] leading-relaxed">
                    Practice the "High Elbow Cone Drill" — place a cone 1.5m in front of off-stump. Drive through the line of the cone maintaining lead elbow above wrist level.
                  </p>
                </div>

                <button
                  onClick={() => {
                    onSelectSession(latestSession.session_id);
                    onSelectTab('workspace');
                  }}
                  className="w-full py-2 rounded-lg bg-[#303438] hover:bg-[#42474C] text-[#F5F5F5] text-xs font-semibold text-center transition-colors cursor-pointer"
                >
                  Inspect Technique Workspace →
                </button>
              </div>
            ) : (
              <div className="p-6 text-center text-[#A5A9AD] text-xs space-y-2">
                <p>No recent observations yet.</p>
                <p className="text-[11px]">Start your first live batting attempt to generate explainable technique feedback.</p>
              </div>
            )}
          </div>

          {/* Camera Setup & Accuracy Tip */}
          <div className="p-4 rounded-xl bg-[#111315] border border-[#303438] text-xs text-[#A5A9AD] space-y-2">
            <div className="font-bold text-[#F5F5F5] flex items-center space-x-1.5">
              <Camera className="w-3.5 h-3.5 text-[#7FEA35]" />
              <span>Camera Setup Tip</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              For best movement tracking, place your camera 3–5 meters away at waist height, directly side-on (perpendicular) to your batting crease.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
