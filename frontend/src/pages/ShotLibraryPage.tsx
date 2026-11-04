import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Filter,
  Sparkles,
  Layers,
  Video,
  Upload,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Info,
  ChevronRight,
  BookOpen,
  X,
  Activity,
  ArrowRight,
  Compass,
  Check,
  ShieldAlert,
  Play
} from 'lucide-react';
import { CricketShot, CategorySummary, SessionListItem, NavTab } from '../types/cricket';
import { api } from '../services/api';
import { ShotPreviewModal } from '../components/ShotPreviewModal';

interface ShotLibraryPageProps {
  onSelectTab: (tab: NavTab) => void;
  onSelectShotForAction?: (shotName: string) => void;
  onSelectSession?: (sessionId: string) => void;
}

const CATEGORIES = [
  'All Shots',
  'Drives',
  'Defensive Strokes',
  'Back-foot and Cut Shots',
  'Short-ball Attacking Shots',
  'Leg-side and Wrist-oriented Strokes',
  'Sweep-family Strokes',
  'Power and Innovative Shots'
];

export const ShotLibraryPage: React.FC<ShotLibraryPageProps> = ({
  onSelectTab,
  onSelectShotForAction,
  onSelectSession,
}) => {
  const [shots, setShots] = useState<CricketShot[]>([]);
  const [categories, setCategories] = useState<CategorySummary[]>([]);
  const [availableSessions, setAvailableSessions] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedCategory, setSelectedCategory] = useState<string>('All Shots');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [referenceOnly, setReferenceOnly] = useState<boolean>(false);

  // Active modal shot
  const [activeModalShot, setActiveModalShot] = useState<CricketShot | null>(null);

  useEffect(() => {
    loadShots();
    api.listSessions(50).then((res) => {
      setAvailableSessions(res.sessions || []);
    }).catch(() => {});
  }, []);

  const loadShots = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getShots();
      setShots(res.shots);
      setCategories(res.categories);
    } catch (err: any) {
      setError(err.message || 'Failed to load cricket shot catalogue.');
    } finally {
      setLoading(false);
    }
  };

  // Filtered collection based on client state
  const filteredShots = useMemo(() => {
    return shots.filter((shot) => {
      // Category filter
      if (selectedCategory !== 'All Shots' && shot.category !== selectedCategory) {
        return false;
      }
      // Reference-only filter
      if (referenceOnly && shot.reference_status !== 'available') {
        return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const inName = shot.name.toLowerCase().includes(q);
        const inCategory = shot.category.toLowerCase().includes(q);
        const inDesc = shot.description.toLowerCase().includes(q);
        const inAliases = shot.aliases.some((a) => a.toLowerCase().includes(q));
        const inTags = shot.tags.some((t) => t.toLowerCase().includes(q));
        return inName || inCategory || inDesc || inAliases || inTags;
      }
      return true;
    });
  }, [shots, selectedCategory, referenceOnly, searchQuery]);

  const handleStartPractice = (shot: CricketShot) => {
    if (onSelectShotForAction) {
      onSelectShotForAction(shot.name);
    }
    onSelectTab('live');
  };

  const handleUploadAttempt = (shot: CricketShot) => {
    if (onSelectShotForAction) {
      onSelectShotForAction(shot.name);
    }
    onSelectTab('upload');
  };

  const handleAnalyzeShot = (shot: CricketShot) => {
    if (onSelectShotForAction) {
      onSelectShotForAction(shot.name);
    }
    const sName = shot.name.toLowerCase().trim();
    const match = availableSessions.find((s) => s.shot_type.toLowerCase().trim() === sName);
    if (match && onSelectSession) {
      onSelectSession(match.session_id);
    }
    onSelectTab('workspace');
  };

  const formatFeatureLabel = (featureKey: string) => {
    return featureKey
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="max-w-[1550px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-[#303438]">
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#7FEA35]/10 border border-[#7FEA35]/30 flex items-center justify-center text-[#7FEA35]">
              <BookOpen className="w-4 h-4" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#F5F5F5] tracking-tight">
              Cricket Shot Library
            </h1>
            <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-semibold">
              {shots.length} Shots Available
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#A5A9AD] max-w-3xl">
            Explore batting techniques and analyze the movements behind every shot. Centralized catalogue integrating biomechanical features, benchmark availability, and video analysis.
          </p>
        </div>

        {/* Technical Notice Badge */}
        <div className="p-2.5 rounded-xl bg-[#111315] border border-[#303438] text-[11px] text-[#A5A9AD] flex items-center space-x-2 shrink-0">
          <Info className="w-3.5 h-3.5 text-[#7FEA35] shrink-0" />
          <span>Biomechanical targets calibrated from published coaching literature, not arbitrary standards.</span>
        </div>
      </div>

      {/* Search and Category Filter Toolbar */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Functional Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#A5A9AD] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by shot name, alias, category, or tag (e.g. 'cut', 'sweep')..."
              className="w-full pl-9 pr-9 py-2.5 rounded-xl bg-[#111315] border border-[#303438] text-xs text-[#F5F5F5] placeholder-[#A5A9AD] focus:outline-none focus:border-[#7FEA35] font-sans transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#A5A9AD] hover:text-[#F5F5F5] p-0.5 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Reference Only Filter Toggle */}
          <button
            onClick={() => setReferenceOnly(!referenceOnly)}
            className={`inline-flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
              referenceOnly
                ? 'bg-[#7FEA35]/15 border-[#7FEA35] text-[#7FEA35]'
                : 'bg-[#111315] border-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5]'
            }`}
          >
            <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center ${
              referenceOnly ? 'bg-[#7FEA35] border-[#7FEA35] text-black' : 'border-[#A5A9AD]'
            }`}>
              {referenceOnly && <Check className="w-3 h-3 stroke-[3]" />}
            </div>
            <span>Only Verified Benchmark References</span>
          </button>
        </div>

        {/* Category Filter Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs scrollbar-thin scrollbar-thumb-[#303438]">
          {CATEGORIES.map((cat) => {
            const count = cat === 'All Shots'
              ? shots.length
              : categories.find((c) => c.name === cat)?.count ?? 0;
            const isSelected = selectedCategory === cat;

            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all cursor-pointer flex items-center space-x-1.5 ${
                  isSelected
                    ? 'bg-[#7FEA35] text-[#050505] font-bold shadow-md shadow-[#7FEA35]/20'
                    : 'bg-[#111315] text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D] border border-[#303438]'
                }`}
              >
                <span>{cat}</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  isSelected ? 'bg-[#050505]/20 text-[#050505]' : 'bg-[#181B1D] text-[#A5A9AD]'
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="p-16 text-center space-y-3">
          <Activity className="w-8 h-8 text-[#7FEA35] animate-spin mx-auto" />
          <h3 className="text-sm font-semibold text-[#F5F5F5]">Loading Cricket Shot Library...</h3>
          <p className="text-xs text-[#A5A9AD]">Querying centralized catalogue and benchmark registry</p>
        </div>
      ) : error ? (
        <div className="p-12 rounded-2xl bg-[#111315] border border-rose-900/50 text-center space-y-3 max-w-xl mx-auto">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-sm font-bold text-[#F5F5F5]">Failed to Load Library</h3>
          <p className="text-xs text-rose-300">{error}</p>
          <button
            onClick={loadShots}
            className="px-4 py-2 rounded-lg bg-[#303438] hover:bg-[#42474C] text-[#F5F5F5] text-xs font-semibold cursor-pointer"
          >
            Retry Catalogue
          </button>
        </div>
      ) : filteredShots.length === 0 ? (
        /* Empty State */
        <div className="p-16 rounded-2xl bg-[#111315] border border-[#303438] text-center space-y-3 max-w-lg mx-auto">
          <Compass className="w-10 h-10 text-[#A5A9AD] mx-auto opacity-60" />
          <h3 className="text-base font-bold text-[#F5F5F5]">No Matching Cricket Shots</h3>
          <p className="text-xs text-[#A5A9AD] leading-relaxed">
            No shots matched your current filters
            {searchQuery ? ` matching "${searchQuery}"` : ''}
            {referenceOnly ? ' with verified benchmark references' : ''}.
          </p>
          <button
            onClick={() => {
              setSelectedCategory('All Shots');
              setSearchQuery('');
              setReferenceOnly(false);
            }}
            className="px-4 py-2 rounded-lg bg-[#7FEA35] text-[#050505] font-bold text-xs cursor-pointer hover:bg-[#94EE58] transition-colors"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        /* Responsive Shot Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredShots.map((shot) => {
            const hasBenchmark = shot.reference_status === 'available';

            return (
              <div
                key={shot.id}
                className="group p-5 rounded-2xl bg-[#181B1D] border border-[#303438] hover:border-[#7FEA35]/60 hover:shadow-xl hover:shadow-[#7FEA35]/5 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  {/* Top Badges */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#111315] text-[#7FEA35] border border-[#303438]">
                      {shot.category}
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                      shot.difficulty === 'Foundation'
                        ? 'bg-sky-950/80 text-sky-400 border border-sky-800/80'
                        : shot.difficulty === 'Intermediate'
                        ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/80'
                        : shot.difficulty === 'Advanced'
                        ? 'bg-amber-950/80 text-amber-400 border border-amber-800/80'
                        : 'bg-rose-950/80 text-rose-400 border border-rose-800/80'
                    }`}>
                      {shot.difficulty}
                    </span>
                  </div>

                  {/* Shot Title & Aliases */}
                  <div
                    onClick={() => setActiveModalShot(shot)}
                    className="cursor-pointer"
                    title="Click to preview authentic technique & 7-phase breakdown"
                  >
                    <h3 className="text-base font-bold text-[#F5F5F5] group-hover:text-[#7FEA35] transition-colors flex items-center justify-between">
                      <span>{shot.name}</span>
                      <Play className="w-3.5 h-3.5 text-[#7FEA35] opacity-0 group-hover:opacity-100 transition-opacity fill-[#7FEA35]" />
                    </h3>
                    {shot.aliases.length > 0 && (
                      <p className="text-[11px] text-[#A5A9AD] font-mono mt-0.5 truncate">
                        aka {shot.aliases.slice(0, 2).join(', ')}
                      </p>
                    )}
                  </div>

                  {/* Description */}
                  <p className="text-xs text-[#A5A9AD] leading-relaxed line-clamp-3">
                    {shot.description}
                  </p>

                  {/* Analysis Features Badges */}
                  <div className="space-y-1.5 pt-1">
                    <div className="text-[10px] uppercase font-mono tracking-wider text-[#A5A9AD] font-semibold">
                      Analyzed Kinematics
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {shot.analysis_features.slice(0, 4).map((f) => (
                        <span
                          key={f}
                          className="text-[10px] px-2 py-0.5 rounded bg-[#111315] text-[#F5F5F5] border border-[#303438] font-mono"
                        >
                          {formatFeatureLabel(f)}
                        </span>
                      ))}
                      {shot.analysis_features.length > 4 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#111315] text-[#A5A9AD] border border-[#303438] font-mono">
                          +{shot.analysis_features.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Card Footer: Reference Status & Action Buttons */}
                <div className="space-y-3 pt-3 border-t border-[#303438]">
                  {/* Reference Status Indicator */}
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-[#A5A9AD]">Benchmark DTW:</span>
                    {hasBenchmark ? (
                      <span className="font-semibold text-[#7FEA35] flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#7FEA35]" />
                        <span>Available</span>
                      </span>
                    ) : (
                      <span className="text-[#A5A9AD] flex items-center space-x-1 font-mono text-[10px]" title="Attempt-to-attempt comparison supported without fabricated benchmarks">
                        <span>Session-to-Session</span>
                      </span>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setActiveModalShot(shot)}
                      className="w-full py-2 px-2.5 rounded-lg bg-[#111315] hover:bg-[#303438] text-[#7FEA35] text-xs font-bold border border-[#303438] hover:border-[#7FEA35]/40 transition-colors cursor-pointer text-center flex items-center justify-center space-x-1"
                      title="Inspect Authentic Video, 7 Phases & Technique Breakdown"
                    >
                      <Play className="w-3.5 h-3.5 fill-[#7FEA35]" />
                      <span>Preview & Technique</span>
                    </button>
                    <button
                      onClick={() => handleStartPractice(shot)}
                      className="w-full py-2 px-2.5 rounded-lg bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] text-xs font-bold transition-all cursor-pointer text-center flex items-center justify-center space-x-1"
                      title="Practice Stroke in Live Coach"
                    >
                      <span>Practice</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Authentic Shot Preview & Biomechanical Breakdown Modal */}
      {activeModalShot && (
        <ShotPreviewModal
          shot={activeModalShot}
          onClose={() => setActiveModalShot(null)}
          onStartPractice={handleStartPractice}
          onUploadAttempt={handleUploadAttempt}
        />
      )}
    </div>
  );
};
