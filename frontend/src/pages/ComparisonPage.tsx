import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  Activity,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  CheckCircle2,
  Info,
  Scale
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { ComparisonResult, ReferenceShotMeta, SessionListItem, NavTab } from '../types/cricket';
import { api } from '../services/api';

interface ComparisonPageProps {
  sessionId: string | null;
  onSelectTab: (tab: NavTab) => void;
  onSelectSession?: (sessionId: string) => void;
}

export const ComparisonPage: React.FC<ComparisonPageProps> = ({ sessionId, onSelectTab, onSelectSession }) => {
  const [references, setReferences] = useState<ReferenceShotMeta[]>([]);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>(sessionId || '');
  const [selectedRefId, setSelectedRefId] = useState<string>('ref_cover_drive_01');
  const [selectedTargetSessionId, setSelectedTargetSessionId] = useState<string>('');
  const [comparisonMode, setComparisonMode] = useState<'reference' | 'attempt'>('reference');

  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [chartMetric, setChartMetric] = useState<'knee' | 'torso' | 'head'>('knee');

  useEffect(() => {
    if (sessionId) {
      setCurrentSessionId(sessionId);
    }
    loadPrerequisites();
  }, [sessionId]);

  const loadPrerequisites = async () => {
    try {
      setLoading(true);
      const [refList, sessRes] = await Promise.all([
        api.listReferences(),
        api.listSessions(30),
      ]);
      setReferences(refList);
      setSessions(sessRes.sessions);

      // Determine active session ID
      const activeId = sessionId || (sessRes.sessions.length > 0 ? sessRes.sessions[0].session_id : null);
      if (activeId) {
        setCurrentSessionId(activeId);
        await executeComparison(activeId, selectedRefId);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load comparison data');
    } finally {
      setLoading(false);
    }
  };

  const handleActiveSessionChange = (newSessId: string) => {
    setCurrentSessionId(newSessId);
    if (onSelectSession) {
      onSelectSession(newSessId);
    }
    if (comparisonMode === 'reference') {
      executeComparison(newSessId, selectedRefId);
    } else {
      executeComparison(newSessId, undefined, selectedTargetSessionId);
    }
  };

  const executeComparison = async (qSessionId: string, refId?: string, targetSessId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.compare(
        qSessionId,
        comparisonMode === 'reference' ? refId : undefined,
        comparisonMode === 'attempt' ? targetSessId : undefined
      );
      setComparison(res);
    } catch (err: any) {
      setError(err.message || 'Comparison failed');
      setComparison(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRefChange = (refId: string) => {
    setSelectedRefId(refId);
    if (sessionId) {
      executeComparison(sessionId, refId);
    }
  };

  const handleTargetSessionChange = (tSessId: string) => {
    setSelectedTargetSessionId(tSessId);
    if (sessionId && tSessId) {
      executeComparison(sessionId, undefined, tSessId);
    }
  };

  if (loading && !comparison) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center space-y-3">
        <Activity className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
        <h3 className="text-sm font-semibold text-white">Tempo-Matching Practice Strokes...</h3>
      </div>
    );
  }

  // Build chart dataset from aligned_time_series
  const alignedChartData = comparison?.aligned_time_series.map((pair, idx) => ({
    step: idx,
    queryTime: pair.query_time_sec,
    refTime: pair.reference_time_sec,
    queryKnee: pair.query_knee_angle ?? null,
    refKnee: pair.ref_knee_angle ?? null,
    queryTorso: pair.query_torso_lean ?? null,
    refTorso: pair.ref_torso_lean ?? null,
    queryHead: pair.query_head_y ? Number((pair.query_head_y * 100).toFixed(1)) : null,
    refHead: pair.ref_head_y ? Number((pair.ref_head_y * 100).toFixed(1)) : null,
  })) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-navy-800">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2">
            <span>Reference Shot & Attempt Comparison</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cricket-sky/10 text-cricket-sky border border-cricket-sky/20">
              Tempo Matched
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Compare your movement against a benchmark or previous practice attempt, aligned across different execution speeds.
          </p>
        </div>

        {/* Query Session / Real Shot Selector */}
        <div className="flex items-center space-x-2 bg-[#111315] border border-[#303438] px-3 py-1.5 rounded-xl">
          <span className="text-xs font-mono uppercase text-[#A5A9AD] font-bold">Shot Attempt:</span>
          <select
            value={currentSessionId}
            onChange={(e) => handleActiveSessionChange(e.target.value)}
            className="bg-transparent text-xs font-bold text-[#7FEA35] focus:outline-none cursor-pointer max-w-[280px]"
            title="Select Shot Attempt to Compare"
          >
            {sessions.map((s) => (
              <option key={s.session_id} value={s.session_id} className="bg-[#181B1D] text-[#F5F5F5]">
                {s.shot_type} — {s.video_filename}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Comparison Selector Controls */}
      <div className="bg-navy-900/80 p-5 rounded-2xl border border-navy-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                setComparisonMode('reference');
                if (sessionId) executeComparison(sessionId, selectedRefId);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                comparisonMode === 'reference'
                  ? 'bg-brand-500 text-navy-950 shadow-md'
                  : 'bg-navy-950 text-slate-400 hover:text-white border border-navy-800'
              }`}
            >
              Compare vs Textbook Benchmark
            </button>
            <button
              onClick={() => {
                setComparisonMode('attempt');
                const other = sessions.find((s) => s.session_id !== sessionId)?.session_id;
                if (other && sessionId) {
                  setSelectedTargetSessionId(other);
                  executeComparison(sessionId, undefined, other);
                }
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                comparisonMode === 'attempt'
                  ? 'bg-brand-500 text-navy-950 shadow-md'
                  : 'bg-navy-950 text-slate-400 hover:text-white border border-navy-800'
              }`}
            >
              Compare vs Previous Practice Attempt
            </button>
          </div>

          {/* Reference / Target Dropdown */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400">Comparing with:</span>
            {comparisonMode === 'reference' ? (
              <select
                value={selectedRefId}
                onChange={(e) => handleRefChange(e.target.value)}
                className="bg-navy-950 border border-navy-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
              >
                {references.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title}
                  </option>
                ))}
              </select>
            ) : (
              <select
                value={selectedTargetSessionId}
                onChange={(e) => handleTargetSessionChange(e.target.value)}
                className="bg-navy-950 border border-navy-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
              >
                {sessions
                  .filter((s) => s.session_id !== sessionId)
                  .map((s) => (
                    <option key={s.session_id} value={s.session_id}>
                      {s.shot_type} ({s.video_filename})
                    </option>
                  ))}
              </select>
            )}
          </div>
        </div>

        {/* Compatibility Warning if Comparing Incompatible Shots */}
        {comparison?.compatibility_warning && (
          <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/80 text-xs text-amber-300 flex items-start space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Compatibility Notice: </strong>
              <span>{comparison.compatibility_warning}</span>
            </div>
          </div>
        )}
      </div>

      {comparison && comparison.warping_path_length === 0 ? (
        <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-8 text-center space-y-4 max-w-2xl mx-auto">
          <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
          <h3 className="text-base font-bold text-white">
            No Verified Benchmark Available for {comparison.shot_type}
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            CricketIQ strictly adheres to research and biomechanical integrity: we do not fabricate synthetic benchmark curves or compare against unrelated strokes.
          </p>
          <div className="p-4 rounded-xl bg-navy-950 border border-navy-800 text-xs text-slate-300">
            <strong>Recommended Action:</strong> Switch comparison mode to <em>"Compare vs Previous Practice Attempt"</em> above to compare this attempt against another recording of your {comparison.shot_type}.
          </div>
          <button
            onClick={() => onSelectTab('library')}
            className="px-4 py-2 rounded-lg bg-navy-800 hover:bg-navy-700 text-xs font-semibold text-white border border-navy-700 transition-colors cursor-pointer"
          >
            Browse Cricket Shot Library
          </button>
        </div>
      ) : comparison && (
        <div className="space-y-6">
          {/* Top Score Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-navy-900/80 p-5 rounded-2xl border border-navy-800 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span>Similarity to a Pro's Timing</span>
                <Scale className="w-4 h-4 text-brand-400" />
              </span>
              <div className="text-3xl font-extrabold font-mono text-white">
                {comparison.normalized_similarity_score}%
              </div>
              <p className="text-[11px] text-slate-400">
                Timing curve alignment via Dynamic Time Warping (DTW) — measures tempo synchronization, separate from your 0–100 Technique Score.
              </p>
            </div>

            <div className="bg-navy-900/80 p-5 rounded-2xl border border-navy-800 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Movement Difference Index
              </span>
              <div className="text-3xl font-extrabold font-mono text-cricket-sky">
                {comparison.raw_dtw_distance}
              </div>
              <p className="text-[11px] text-slate-400">
                Calculated across {comparison.warping_path_length} tempo-aligned movement points
              </p>
            </div>

            <div className="bg-navy-900/80 p-5 rounded-2xl border border-navy-800 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Benchmark Model
              </span>
              <div className="text-sm font-bold text-white truncate">
                {comparison.reference_title}
              </div>
              <p className="text-[11px] text-slate-400">
                Target Shot: <strong className="text-slate-300">{comparison.shot_type}</strong>
              </p>
            </div>
          </div>

          {/* Overlaid Aligned Comparison Chart */}
          <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <span>Synchronized Stroke Movement Curves</span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
                    Synchronized
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Overlaid comparison of your attempt (Solid Green) against the reference standard (Dashed White)
                </p>
              </div>

              {/* Metric switcher */}
              <div className="flex items-center space-x-1 bg-navy-950 p-1 rounded-lg border border-navy-800 text-xs">
                <button
                  onClick={() => setChartMetric('knee')}
                  className={`px-3 py-1 rounded font-medium transition-all ${
                    chartMetric === 'knee' ? 'bg-brand-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Lead Knee Angle (°)
                </button>
                <button
                  onClick={() => setChartMetric('torso')}
                  className={`px-3 py-1 rounded font-medium transition-all ${
                    chartMetric === 'torso' ? 'bg-sky-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Torso Lean (°)
                </button>
                <button
                  onClick={() => setChartMetric('head')}
                  className={`px-3 py-1 rounded font-medium transition-all ${
                    chartMetric === 'head' ? 'bg-yellow-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Head Height (norm)
                </button>
              </div>
            </div>

            <div className="h-72 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={alignedChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="step"
                    stroke="#64748b"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(v) => `P${v}`}
                  />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0b1120',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey={
                      chartMetric === 'knee'
                        ? 'queryKnee'
                        : chartMetric === 'torso'
                        ? 'queryTorso'
                        : 'queryHead'
                    }
                    stroke="#22c55e"
                    strokeWidth={2.5}
                    name="Your Attempt"
                    dot={false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey={
                      chartMetric === 'knee'
                        ? 'refKnee'
                        : chartMetric === 'torso'
                        ? 'refTorso'
                        : 'refHead'
                    }
                    stroke="#f8fafc"
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    name="Reference Model"
                    dot={false}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Key Moment Differences Table */}
          <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Measurable Key Moment Divergences
            </h3>
            <p className="text-xs text-slate-400">
              Biomechanical differences detected at critical execution moments (e.g. forward stride, impact):
            </p>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-navy-800 text-xs">
                <thead>
                  <tr className="text-slate-400 font-mono text-[11px]">
                    <th className="py-2.5 px-3 text-left">Key Moment</th>
                    <th className="py-2.5 px-3 text-left">Phase</th>
                    <th className="py-2.5 px-3 text-left">Your Measurement</th>
                    <th className="py-2.5 px-3 text-left">Reference</th>
                    <th className="py-2.5 px-3 text-left">Delta</th>
                    <th className="py-2.5 px-3 text-left">Actionable Interpretation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-800/60 font-sans">
                  {comparison.key_differences.map((diff, idx) => (
                    <tr key={idx} className="hover:bg-navy-850/60">
                      <td className="py-3 px-3 font-semibold text-white whitespace-nowrap">
                        {diff.moment_name}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400 whitespace-nowrap">
                        {diff.phase}
                      </td>
                      <td className="py-3 px-3 font-mono text-white font-bold whitespace-nowrap">
                        {diff.query_value} {diff.unit}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400 whitespace-nowrap">
                        {diff.ref_value} {diff.unit}
                      </td>
                      <td className="py-3 px-3 font-mono whitespace-nowrap">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                            Math.abs(diff.difference) >= 10
                              ? 'bg-amber-950 text-amber-400 border border-amber-800'
                              : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          }`}
                        >
                          {diff.difference > 0 ? `+${diff.difference}` : diff.difference} {diff.unit}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-300 max-w-md">
                        {diff.interpretation}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Methodology Note */}
          <div className="bg-navy-950 rounded-xl p-4 border border-navy-800 text-xs text-slate-400 space-y-1">
            <strong className="text-slate-300 font-semibold">Comparison Methodology:</strong>
            <p className="text-[11px] leading-relaxed">{comparison.methodology_note}</p>
          </div>
        </div>
      )}
    </div>
  );
};
