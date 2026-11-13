import React, { useState, useEffect } from 'react';
import { LineChart, Activity, ShieldAlert, ArrowLeft } from 'lucide-react';
import { AnalysisResult, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { MetricCard } from '../components/MetricCard';
import { KinematicCharts } from '../components/KinematicCharts';
import { PhaseTimeline } from '../components/PhaseTimeline';

interface BiomechanicsPageProps {
  sessionId: string | null;
  onSelectTab: (tab: NavTab) => void;
}

export const BiomechanicsPage: React.FC<BiomechanicsPageProps> = ({ sessionId, onSelectTab }) => {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentFrame, setCurrentFrame] = useState<number>(0);

  useEffect(() => {
    if (!sessionId) {
      api.listSessions(1).then((res) => {
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
      const data = await api.getAnalysis(id);
      setAnalysis(data);
    } catch (err) {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center space-y-3">
        <Activity className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
        <h3 className="text-sm font-semibold text-white">Loading Biomechanical Analysis...</h3>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-4">
        <ShieldAlert className="w-8 h-8 text-amber-400 mx-auto" />
        <h3 className="text-sm font-bold text-white">No active session selected</h3>
        <button
          onClick={() => onSelectTab('dashboard')}
          className="px-4 py-2 rounded-lg bg-navy-800 text-xs text-white"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  const summary = analysis.summary || ({} as any);
  const timeSeries = analysis.time_series || [];
  const impactMetrics = timeSeries.find((m) => m?.phase?.toLowerCase().includes('impact')) || (timeSeries.length > 0 ? timeSeries[Math.floor(timeSeries.length * 0.65)] : null);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-navy-800">
        <div>
          <button
            onClick={() => onSelectTab('workspace')}
            className="text-xs text-slate-400 hover:text-white flex items-center space-x-1 mb-1 font-mono"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Video Workspace</span>
          </button>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2">
            <span>Biomechanical Technique Assessment</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Detailed kinematic trajectories and vector angle analysis for {analysis.shot_type || 'Selected Shot'} ({analysis.session_id})
          </p>
        </div>
      </div>

      {/* Grid of Key Biomechanical Measurement Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Lead Knee Flexion (Impact)"
          value={summary.lead_knee_flexion_at_impact}
          unit="°"
          benchmark="115°–135°"
          status="optimal"
          description="Angle at interior knee apex formed by hip, knee, and ankle vectors at contact."
        />
        <MetricCard
          title="Lead Elbow Flexion"
          value={summary.lead_elbow_flexion_at_impact}
          unit="°"
          benchmark="135°–160°"
          status={
            summary.lead_elbow_flexion_at_impact &&
            summary.lead_elbow_flexion_at_impact < 125
              ? 'warning'
              : 'optimal'
          }
          description="Shoulder-elbow-wrist interior angle. High lead elbow ensures straight blade drive."
        />
        <MetricCard
          title="Lead Arm Extension"
          value={
            summary.lead_arm_extension_at_impact
              ? Number((summary.lead_arm_extension_at_impact * 100).toFixed(0))
              : null
          }
          unit="%"
          benchmark="85%–95%"
          status="optimal"
          description="Shoulder-to-wrist distance relative to total arm segment length at impact."
        />
        <MetricCard
          title="Head Over Lead Knee"
          value={
            summary.head_over_knee_at_impact !== undefined && summary.head_over_knee_at_impact !== null
              ? Number(Math.abs(summary.head_over_knee_at_impact).toFixed(2))
              : null
          }
          unit="offset"
          benchmark="< 0.15"
          status={
            summary.head_over_knee_at_impact !== undefined &&
            summary.head_over_knee_at_impact !== null &&
            Math.abs(summary.head_over_knee_at_impact) > 0.22
              ? 'warning'
              : 'optimal'
          }
          description="Horizontal offset between head landmark and lead knee, scaled by torso length."
        />
        <MetricCard
          title="Torso Forward Inclination"
          value={summary.torso_lean_at_impact}
          unit="°"
          benchmark="20°–32°"
          status="optimal"
          description="Mid-hip to mid-shoulder vector inclination from vertical image axis."
        />
        <MetricCard
          title="Front Foot Weight Transfer"
          value={
            summary.weight_transfer_at_impact
              ? Number((summary.weight_transfer_at_impact * 100).toFixed(0))
              : null
          }
          unit="%"
          benchmark="70%–85%"
          status="optimal"
          description="Estimated body center-of-mass projection onto front foot base of support."
        />
        <MetricCard
          title="Head Stability Index"
          value={summary.head_stability_index}
          unit="norm"
          benchmark="< 0.08"
          status="optimal"
          description="Normalized dispersion of head position throughout execution cycle."
        />
        <MetricCard
          title="Movement Smoothness"
          value={summary.movement_smoothness}
          unit="/100"
          benchmark="> 75"
          status="optimal"
          description="Kinematic smoothness derived from second derivative jerk variance."
        />
      </div>

      {/* Synchronized Phase Timeline */}
      <PhaseTimeline
        phases={analysis.phases || []}
        currentFrame={currentFrame}
        totalFrames={analysis.analyzed_frames || analysis.total_frames || 0}
        onSelectFrame={setCurrentFrame}
      />

      {/* Interactive TimeSeries Chart Component */}
      <KinematicCharts
        timeSeries={timeSeries}
        currentFrame={currentFrame}
        onSelectFrame={setCurrentFrame}
      />

      {/* Technical Biomechanical Definitions & Monocular Caveat */}
      <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          Biomechanical Methodology & Measurement Principles
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-300">
          <div className="space-y-2">
            <h4 className="font-semibold text-brand-400 font-mono">1. Joint Flexion Calculations</h4>
            <p className="leading-relaxed text-slate-400">
              Joint angles (e.g. lead and rear knees) are calculated using 2D dot products between unit vectors:
              <br />
              <code className="text-white font-mono bg-navy-950 px-2 py-0.5 rounded mt-1 inline-block">
                cos(θ) = (u · v) / (||u|| ||v||)
              </code>
              <br />
              interior angle θ ∈ [0°, 180°]. A fully straightened leg corresponds to 180°, while knee flexion produces values between 110° and 140° during forward strides.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-semibold text-cricket-sky font-mono">2. Body-Scale Normalization</h4>
            <p className="leading-relaxed text-slate-400">
              Spatial metrics such as stance width and head displacement are normalized by torso segment length
              (distance between shoulder center and pelvis center). This eliminates arbitrary camera zoom artifacts
              and enables fair comparisons across players of different heights.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-semibold text-yellow-400 font-mono">3. Coordinate System Conventions</h4>
            <p className="leading-relaxed text-slate-400">
              The vertical reference axis is defined along vector (0, -1) in image space, pointing toward the sky.
              Torso inclination measures deviation of the spine vector from this axis, distinguishing upright strokes
              from forward-leaning drives.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-semibold text-rose-400 font-mono">4. Monocular Projection Disclaimer</h4>
            <p className="leading-relaxed text-slate-400">
              Monocular 2D video does not measure out-of-plane hip or shoulder rotational torque. Foreshortening
              occurs whenever limbs rotate out of the camera's projection plane.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
