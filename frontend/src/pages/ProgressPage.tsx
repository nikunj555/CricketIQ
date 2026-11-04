import React, { useState, useEffect, useMemo } from 'react';
import {
  TrendingUp,
  Download,
  Filter,
  Activity,
  Calendar,
  Layers,
  ChevronRight,
  Trash2,
  BookOpen,
  CheckCircle2,
  ShieldAlert,
  Info,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Dumbbell,
  Sparkles,
  Award
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { SessionListItem, SessionListResponse, CricketShot, NavTab } from '../types/cricket';
import { api } from '../services/api';

interface ProgressPageProps {
  onSelectSession: (sessionId: string) => void;
  onSelectTab: (tab: NavTab) => void;
}

export const ProgressPage: React.FC<ProgressPageProps> = ({
  onSelectSession,
  onSelectTab,
}) => {
  const [sessionsData, setSessionsData] = useState<SessionListResponse | null>(null);
  const [catalogueShots, setCatalogueShots] = useState<CricketShot[]>([]);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('All');
  const [selectedShotFilter, setSelectedShotFilter] = useState<string>('Cover Drive');
  const [loading, setLoading] = useState<boolean>(true);
  const [progressSummary, setProgressSummary] = useState<any>(null);
  const [shotProgress, setShotProgress] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sessRes, shotRes, summaryRes] = await Promise.all([
        api.listSessions(100),
        api.getShots().catch(() => ({ shots: [], categories: [], total_count: 0 })),
        api.getProgressSummary().catch(() => null),
      ]);
      setSessionsData(sessRes);
      setCatalogueShots(shotRes.shots);
      setProgressSummary(summaryRes);

      // Determine default active shot: prefer most practiced or first available
      const defaultShot = summaryRes?.most_practiced_shot || 'Cover Drive';
      setSelectedShotFilter(defaultShot);
      loadShotProgress(defaultShot);
    } catch (err) {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  const loadShotProgress = async (shotType: string) => {
    if (!shotType || shotType === 'All') {
      setShotProgress(null);
      return;
    }
    try {
      const data = await api.getShotProgress(shotType);
      setShotProgress(data);
    } catch (err) {
      setShotProgress(null);
    }
  };

  const handleShotChange = (newShot: string) => {
    setSelectedShotFilter(newShot);
    loadShotProgress(newShot);
  };

  const sessions = sessionsData?.sessions || [];

  // Filter sessions for table
  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      if (selectedCategoryFilter !== 'All' && s.category && s.category !== selectedCategoryFilter) {
        return false;
      }
      if (selectedShotFilter !== 'All' && s.shot_type !== selectedShotFilter) {
        return false;
      }
      return true;
    });
  }, [sessions, selectedCategoryFilter, selectedShotFilter]);

  // Available categories in data or catalogue
  const availableCategories = useMemo(() => {
    const cats = new Set<string>();
    catalogueShots.forEach((s) => cats.add(s.category));
    sessions.forEach((s) => {
      if (s.category && s.category !== 'Other') cats.add(s.category);
    });
    return ['All', ...Array.from(cats)];
  }, [catalogueShots, sessions]);

  // Available shot types filtered by selected category
  const availableShotTypes = useMemo(() => {
    const types = new Set<string>();
    // Add supported calibrated shots
    types.add('Cover Drive');
    types.add('Straight Drive');
    types.add('Pull Shot');
    types.add('Forward Defensive');
    types.add('Sweep');

    sessions.forEach((s) => {
      if (s.shot_type && s.shot_type !== 'Unknown') types.add(s.shot_type);
    });
    return Array.from(types);
  }, [sessions]);

  // Chart data: single score line across chronological attempts for the active shot
  const scoreLineData = useMemo(() => {
    if (shotProgress?.score_trend && shotProgress.score_trend.length > 0) {
      return shotProgress.score_trend.map((pt: any) => ({
        attempt: `Att #${pt.attempt_number}`,
        date: pt.date,
        score: pt.overall_technique_score,
        sessionId: pt.session_id,
      }));
    }
    // Fallback from filtered sessions
    return [...filteredSessions]
      .reverse()
      .filter((s) => s.status === 'completed')
      .map((s, idx) => ({
        attempt: `Att #${idx + 1}`,
        date: s.created_at ? s.created_at.slice(5, 10) : `S${idx + 1}`,
        score: s.overall_technique_score || s.summary?.overall_technique_score || 80,
        sessionId: s.session_id,
      }));
  }, [shotProgress, filteredSessions]);

  const exportCSV = () => {
    if (filteredSessions.length === 0) return;
    const headers = [
      'session_id',
      'video_filename',
      'shot_type',
      'category',
      'technique_score',
      'lead_knee_impact_deg',
      'torso_lean_impact_deg',
      'tracking_success_rate',
      'created_at',
    ];

    const rows = filteredSessions.map((s) => [
      s.session_id,
      s.video_filename,
      s.shot_type,
      s.category || 'Other',
      s.overall_technique_score || s.summary?.overall_technique_score || '',
      s.summary?.lead_knee_flexion_at_impact ?? '',
      s.summary?.torso_lean_at_impact ?? '',
      s.summary?.tracking_success_rate ?? '',
      s.created_at,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `cricketiq_progression_${selectedShotFilter.toLowerCase().replace(/\s+/g, '_')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="max-w-[1550px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#303438]">
        <div>
          <h1 className="text-2xl font-extrabold text-[#F5F5F5] tracking-tight flex items-center space-x-2">
            <span>Biomechanical Practice Progression</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30">
              {filteredSessions.length} Recorded Attempts
            </span>
          </h1>
          <p className="text-xs text-[#A5A9AD] mt-0.5">
            Track your technique score trend, joint angle improvements against ideal MCC benchmarks, and recurring faults.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onSelectTab('library')}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#111315] hover:bg-[#303438] text-[#F5F5F5] text-xs font-medium border border-[#303438] transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5 text-[#7FEA35]" />
            <span>Shot Library</span>
          </button>
          <button
            onClick={exportCSV}
            disabled={filteredSessions.length === 0}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#303438] hover:bg-[#42474C] text-[#F5F5F5] text-xs font-medium border border-[#303438] transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-[#7FEA35]" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Stroke Selector Filter Bar */}
      <div className="bg-[#111315] p-4 rounded-xl border border-[#303438] space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2 overflow-x-auto pb-1 text-xs">
            <span className="text-xs text-[#A5A9AD] font-mono shrink-0">Batting Stroke:</span>
            {availableShotTypes.map((st) => (
              <button
                key={st}
                onClick={() => handleShotChange(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                  selectedShotFilter === st
                    ? 'bg-[#7FEA35] text-[#050505] shadow-sm'
                    : 'bg-[#181B1D] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Progress Summary Narrative Banner */}
      {shotProgress?.summary_sentence && (
        <div className="bg-[#181B1D] border-l-4 border-[#7FEA35] rounded-xl px-5 py-4 flex items-start space-x-3 shadow-md">
          <Sparkles className="w-5 h-5 text-[#7FEA35] shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider font-mono">
              Coach Progress Insight • {selectedShotFilter}
            </h3>
            <p className="text-sm text-[#F5F5F5] mt-1 font-medium leading-relaxed">
              {shotProgress.summary_sentence}
            </p>
          </div>
        </div>
      )}

      {/* Main Single Score Progression Line Chart */}
      <div className="bg-[#181B1D] rounded-2xl border border-[#303438] p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-[#F5F5F5] flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-[#7FEA35]" />
              <span>Overall Technique Score Progression • {selectedShotFilter}</span>
            </h3>
            <p className="text-xs text-[#A5A9AD] mt-0.5">
              Single score curve tracking technique execution (0–100) across chronological attempts for this stroke.
            </p>
          </div>
          <span className="text-xs font-mono text-[#7FEA35] bg-[#111315] px-2.5 py-1 rounded border border-[#303438]">
            {scoreLineData.length} Attempts Evaluated
          </span>
        </div>

        {scoreLineData.length > 0 ? (
          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={scoreLineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#303438" />
                <XAxis dataKey="attempt" stroke="#A5A9AD" fontSize={11} tickLine={false} />
                <YAxis domain={[40, 100]} stroke="#A5A9AD" fontSize={11} tickLine={false} unit="/100" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111315',
                    borderColor: '#303438',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#F5F5F5'
                  }}
                  formatter={(val: any) => [`${val}/100`, 'Technique Score']}
                  labelFormatter={(lbl) => `${lbl}`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#7FEA35"
                  strokeWidth={3}
                  dot={{ r: 5, fill: '#7FEA35' }}
                  activeDot={{ r: 7 }}
                  name="Technique Score"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-[#111315] border border-[#303438] text-center text-xs text-[#A5A9AD]">
            No completed attempts recorded yet for {selectedShotFilter}. Record a swing in Live Coach or upload a video.
          </div>
        )}
      </div>

      {/* Per-Metric Comparison Cards vs Previous 3 Attempts */}
      {shotProgress?.metric_comparisons && shotProgress.metric_comparisons.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider font-mono">
              Key Biomechanical Metrics vs Previous Attempts
            </h3>
            <span className="text-[11px] font-mono text-[#A5A9AD]">
              Evaluated against previous 3 practice sessions
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {shotProgress.metric_comparisons.map((mc: any) => {
              const isImproving = mc.status === 'improving';
              const isNeedsAttention = mc.status === 'needs_attention';

              return (
                <div
                  key={mc.metric_key}
                  className="bg-[#181B1D] rounded-xl border border-[#303438] p-4 space-y-2.5 shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <span className="text-xs font-bold text-[#F5F5F5]">{mc.label}</span>
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border flex items-center space-x-1 ${
                        isImproving
                          ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                          : isNeedsAttention
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : 'bg-sky-500/15 text-sky-400 border-sky-500/30'
                      }`}
                    >
                      {isImproving ? (
                        <>
                          <ArrowUpRight className="w-3 h-3" />
                          <span>Improving</span>
                        </>
                      ) : isNeedsAttention ? (
                        <>
                          <ArrowDownRight className="w-3 h-3" />
                          <span>Needs Attention</span>
                        </>
                      ) : (
                        <>
                          <Minus className="w-3 h-3" />
                          <span>Consistent</span>
                        </>
                      )}
                    </span>
                  </div>

                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-black text-white font-mono">
                      {mc.current_value}
                      {mc.unit}
                    </span>
                    <span className="text-xs text-[#A5A9AD] font-mono">
                      Target: <strong className="text-slate-200">{mc.ideal_range}</strong>
                    </span>
                  </div>

                  {mc.previous_values && mc.previous_values.length > 0 && (
                    <div className="pt-2 border-t border-[#303438] flex items-center justify-between text-[11px] font-mono text-[#A5A9AD]">
                      <span>Previous:</span>
                      <span className="text-slate-300">
                        {mc.previous_values.map((v: number) => `${v}${mc.unit}`).join(' → ')}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Recurring Mistakes Across Sessions */}
      {shotProgress?.recurring_mistakes && shotProgress.recurring_mistakes.length > 0 && (
        <div className="bg-[#181B1D] rounded-2xl border border-[#303438] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider font-mono flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Recurring Technical Faults Across {selectedShotFilter} Attempts</span>
            </h3>
            <span className="text-xs font-mono text-[#A5A9AD]">
              Frequent Faults & Actionable Drills
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shotProgress.recurring_mistakes.map((rm: any, idx: number) => (
              <div
                key={idx}
                className="bg-[#111315] rounded-xl border border-amber-500/20 p-4 space-y-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-xs font-bold text-[#F5F5F5]">{rm.title}</h4>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 shrink-0">
                    {rm.count} of {rm.total_attempts} attempts ({rm.frequency_pct}%)
                  </span>
                </div>
                {rm.why_it_matters && (
                  <p className="text-xs text-[#A5A9AD] leading-relaxed">{rm.why_it_matters}</p>
                )}
                {rm.practical_drill && (
                  <div className="pt-2 border-t border-[#303438] flex items-start space-x-2 text-xs text-[#7FEA35]">
                    <Dumbbell className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-200">Recommended Drill: </strong>
                      <span>{rm.practical_drill}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Session History Table Log */}
      <div className="bg-[#181B1D] rounded-2xl border border-[#303438] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider font-mono">
          Session History Log ({filteredSessions.length})
        </h3>

        {filteredSessions.length === 0 ? (
          <div className="text-center py-10 text-[#A5A9AD] text-xs space-y-2">
            <p>No practice sessions match the selected filter criteria.</p>
            <p className="text-[11px]">Select a different stroke from the filter above.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[#303438] text-xs">
              <thead>
                <tr className="text-[#A5A9AD] font-mono text-[11px]">
                  <th className="py-2.5 px-3 text-left">Session ID</th>
                  <th className="py-2.5 px-3 text-left">Stroke</th>
                  <th className="py-2.5 px-3 text-left">Technique Score</th>
                  <th className="py-2.5 px-3 text-left">Lead Knee @ Impact</th>
                  <th className="py-2.5 px-3 text-left">Torso Lean</th>
                  <th className="py-2.5 px-3 text-left">Date</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#303438]/50">
                {filteredSessions.map((s) => {
                  const score = s.overall_technique_score || s.summary?.overall_technique_score || 80;
                  const knee = s.summary?.lead_knee_flexion_at_impact;
                  const torso = s.summary?.torso_lean_at_impact;

                  return (
                    <tr
                      key={s.session_id}
                      className="hover:bg-[#111315] transition-colors cursor-pointer group"
                      onClick={() => onSelectSession(s.session_id)}
                    >
                      <td className="py-3 px-3 font-mono text-[#7FEA35] font-semibold">
                        {s.session_id}
                      </td>
                      <td className="py-3 px-3 font-medium text-white">{s.shot_type}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] border ${
                            score >= 80
                              ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                              : score >= 65
                              ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                              : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                          }`}
                        >
                          {score}/100
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300">
                        {knee != null ? `${knee}°` : '--'}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300">
                        {torso != null ? `${torso}°` : '--'}
                      </td>
                      <td className="py-3 px-3 text-[#A5A9AD] font-mono text-[11px]">
                        {s.created_at ? s.created_at.slice(0, 10) : '--'}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <span className="inline-flex items-center text-xs text-[#7FEA35] group-hover:underline font-medium">
                          <span>View Report</span>
                          <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
