import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Radio,
  BookOpen,
  LayoutDashboard,
  Upload,
  PlayCircle,
  Activity,
  Layers,
  Columns,
  TrendingUp,
  BarChart3,
  Info,
  ArrowRight,
  Sparkles,
  Command
} from 'lucide-react';
import { NavTab } from '../types/cricket';
import { SHOT_ANIMATIONS } from '../data/shotAnimations';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTab: (tab: NavTab) => void;
  onSelectShot?: (shotName: string) => void;
}

interface NavItem {
  id: NavTab;
  title: string;
  category: 'Navigation';
  icon: React.ReactNode;
  hint: string;
}

interface ShotItem {
  id: string;
  title: string;
  category: string;
  swingPlane: string;
  hint: string;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectTab,
  onSelectShot,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const navigationItems: NavItem[] = [
    { id: 'live', title: 'Live Practice Coach', category: 'Navigation', icon: <Radio className="w-4 h-4 text-[#7FEA35]" />, hint: 'Real-time camera batting practice' },
    { id: 'library', title: '3D Shot Library', category: 'Navigation', icon: <BookOpen className="w-4 h-4 text-[#00f0ff]" />, hint: 'Explore 25 authored shot kinematics' },
    { id: 'workspace', title: 'Analysis Theatre', category: 'Navigation', icon: <PlayCircle className="w-4 h-4 text-[#7FEA35]" />, hint: 'Video player & plain-English coaching' },
    { id: 'dashboard', title: 'Dashboard & Telemetry', category: 'Navigation', icon: <LayoutDashboard className="w-4 h-4 text-slate-300" />, hint: 'Performance summary & stats' },
    { id: 'upload', title: 'Upload Practice Video', category: 'Navigation', icon: <Upload className="w-4 h-4 text-slate-300" />, hint: 'Run 5-stage inference pipeline' },
    { id: 'comparison', title: 'Compare to Benchmark', category: 'Navigation', icon: <Columns className="w-4 h-4 text-[#00f0ff]" />, hint: 'You vs ideal benchmark kinematics' },
    { id: 'progress', title: 'My Progress', category: 'Navigation', icon: <TrendingUp className="w-4 h-4 text-[#7FEA35]" />, hint: 'Shot-wise trend & recurring mistakes' },
    { id: 'biomechanics', title: 'Kinematic Telemetry', category: 'Navigation', icon: <Activity className="w-4 h-4 text-[#00f0ff]" />, hint: 'Joint angle derivatives & velocity' },
    { id: 'phases', title: '7 Stroke Phases', category: 'Navigation', icon: <Layers className="w-4 h-4 text-slate-300" />, hint: 'Phase segmentation & evidence' },
    { id: 'evaluation', title: 'Model Evaluation', category: 'Navigation', icon: <BarChart3 className="w-4 h-4 text-slate-300" />, hint: 'Confusion matrix & calibration' },
    { id: 'about', title: 'About Biomechanical Framework', category: 'Navigation', icon: <Info className="w-4 h-4 text-slate-400" />, hint: 'MCC & Cricket Australia standards' },
  ];

  const shotItems: ShotItem[] = Object.values(SHOT_ANIMATIONS).map((shot) => ({
    id: shot.id,
    title: shot.name,
    category: shot.category,
    swingPlane: shot.swingPlane,
    hint: `${shot.category} · ${shot.swingPlane} swing plane`,
  }));

  const filteredNav = navigationItems.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.hint.toLowerCase().includes(query.toLowerCase())
  );

  const filteredShots = shotItems.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase()) ||
      item.swingPlane.toLowerCase().includes(query.toLowerCase())
  );

  const totalResults = [...filteredNav, ...filteredShots];

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keyboard navigation inside the palette
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, totalResults.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + totalResults.length) % Math.max(1, totalResults.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (totalResults.length > 0) {
        selectItem(totalResults[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  const selectItem = (item: NavItem | ShotItem) => {
    if ('icon' in item) {
      onSelectTab(item.id);
    } else {
      onSelectShot?.(item.title);
      onSelectTab('library');
    }
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/75 backdrop-blur-md"
          />

          {/* Palette Window */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-full max-w-2xl bg-[#0B0C0E]/95 border border-[#303438] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]"
          >
            {/* Search Input Bar */}
            <div className="flex items-center px-4 py-3.5 border-b border-[#303438] gap-3">
              <Search className="w-5 h-5 text-[#7FEA35] shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search views, 25 cricket shots, biomechanical telemetry..."
                className="w-full bg-transparent text-sm text-[#F5F5F5] placeholder-[#A5A9AD] focus:outline-none"
              />
              <span className="hidden sm:inline-flex items-center text-[10px] font-mono px-2 py-0.5 rounded bg-[#181B1D] border border-[#303438] text-[#A5A9AD]">
                ESC to close
              </span>
            </div>

            {/* Results List */}
            <div className="overflow-y-auto p-2 space-y-4 flex-1">
              {filteredNav.length > 0 && (
                <div className="space-y-1">
                  <div className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider text-[#A5A9AD] font-bold">
                    Screens & Workspace
                  </div>
                  {filteredNav.map((item, idx) => {
                    const isSelected = selectedIndex === idx;
                    return (
                      <div
                        key={item.id}
                        onClick={() => selectItem(item)}
                        className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-[#181B1D] text-white border border-[#7FEA35]/40 shadow-xs'
                            : 'text-[#A5A9AD] hover:bg-[#111315] hover:text-white'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="p-1.5 rounded-lg bg-[#050505] border border-[#303438]">
                            {item.icon}
                          </div>
                          <div>
                            <div className="font-semibold text-white">{item.title}</div>
                            <div className="text-[11px] text-[#A5A9AD]">{item.hint}</div>
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-[#7FEA35] opacity-0 group-hover:opacity-100" />
                      </div>
                    );
                  })}
                </div>
              )}

              {filteredShots.length > 0 && (
                <div className="space-y-1">
                  <div className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider text-[#00f0ff] font-bold flex items-center space-x-1">
                    <Sparkles className="w-3 h-3 text-[#00f0ff]" />
                    <span>3D Shot Library ({filteredShots.length} shots)</span>
                  </div>
                  {filteredShots.map((shot, idx) => {
                    const globalIdx = filteredNav.length + idx;
                    const isSelected = selectedIndex === globalIdx;
                    return (
                      <div
                        key={shot.id}
                        onClick={() => selectItem(shot)}
                        className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-[#181B1D] text-white border border-[#00f0ff]/40 shadow-xs'
                            : 'text-[#A5A9AD] hover:bg-[#111315] hover:text-white'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="px-2 py-1 rounded bg-[#050505] border border-[#303438] text-[10px] font-mono text-[#00f0ff] font-bold">
                            3D
                          </div>
                          <div>
                            <div className="font-semibold text-white">{shot.title}</div>
                            <div className="text-[11px] text-[#A5A9AD]">{shot.hint}</div>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#111315] border border-[#303438] text-slate-400">
                          {shot.category}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {totalResults.length === 0 && (
                <div className="py-12 text-center text-xs text-[#A5A9AD]">
                  No matches found for <strong className="text-white">"{query}"</strong>.
                </div>
              )}
            </div>

            {/* Footer Hints */}
            <div className="px-4 py-2.5 bg-[#050505] border-t border-[#303438] text-[11px] font-mono text-[#A5A9AD] flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span>↑↓ Navigate</span>
                <span>↵ Open</span>
              </div>
              <div className="flex items-center space-x-1 text-[#7FEA35]">
                <Command className="w-3 h-3" />
                <span>CricketIQ Telemetry</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

