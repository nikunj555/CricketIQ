import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  LayoutDashboard,
  Video,
  Upload,
  Layers,
  GitCompare,
  Sliders,
  BookOpen,
  TrendingUp,
  BrainCircuit,
  Info,
  ChevronLeft,
  ChevronRight,
  Copy,
  Check,
  X,
  Radio,
  Sparkles,
} from 'lucide-react';
import { BrandLogo } from './BrandLogo';
import { api } from '../services/api';
import { NavTab } from '../types/cricket';

export type { NavTab };

interface NavItemConfig {
  id: NavTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroupConfig {
  title: string;
  items: NavItemConfig[];
}

const NAV_GROUPS: NavGroupConfig[] = [
  {
    title: 'Train',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'live', label: 'Live Practice', icon: Video },
      { id: 'upload', label: 'Upload Video', icon: Upload },
    ],
  },
  {
    title: 'Analyse',
    items: [
      { id: 'workspace', label: 'Technique Analysis', icon: Layers },
      { id: 'comparison', label: 'Compare to Benchmark', icon: GitCompare },
      { id: 'phases', label: 'Phase Breakdown', icon: Sliders },
    ],
  },
  {
    title: 'Learn',
    items: [
      { id: 'library', label: 'Shot Library', icon: BookOpen },
    ],
  },
  {
    title: 'Track',
    items: [
      { id: 'progress', label: 'My Progress', icon: TrendingUp },
      { id: 'evaluation', label: 'Model Evaluation', icon: BrainCircuit },
    ],
  },
];

export interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  activeSessionId: string | null;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  activeSessionId,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  const [copiedSession, setCopiedSession] = useState(false);
  const [healthStatus, setHealthStatus] = useState<'healthy' | 'degraded' | 'offline' | 'checking'>('checking');
  const [healthIssues, setHealthIssues] = useState<string[]>([]);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  // Poll /api/health every 15s with debounce and grace counter to prevent flickering "AI Offline"
  const consecutiveFailuresRef = useRef<number>(0);

  const checkHealth = useCallback(async () => {
    const t0 = performance.now();
    try {
      const data = await api.getHealth();
      const elapsed = Math.round(performance.now() - t0);
      consecutiveFailuresRef.current = 0;
      setHealthStatus(data.status === 'degraded' ? 'degraded' : 'healthy');
      setHealthIssues(data.issues || []);
      setLatencyMs(elapsed);
    } catch {
      consecutiveFailuresRef.current += 1;
      // Require 2 consecutive failed health checks before marking AI offline
      // This absorbs single network hiccups, latency spikes, or temporary 502 spin-up cycles
      if (consecutiveFailuresRef.current >= 2) {
        setHealthStatus('offline');
        setHealthIssues(['Backend server is unreachable']);
        setLatencyMs(null);
      }
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Handle Session Copy
  const handleCopySession = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeSessionId) return;
    navigator.clipboard.writeText(activeSessionId);
    setCopiedSession(true);
    setTimeout(() => setCopiedSession(false), 2000);
  };

  const handleNavClick = (tab: NavTab) => {
    onSelectTab(tab);
    onCloseMobile();
  };

  const displaySessionId = activeSessionId
    ? `${activeSessionId.slice(0, 8)}...`
    : 'No active session';

  // Shared content inside desktop & mobile drawer
  const renderSidebarContent = (collapsed: boolean) => (
    <div className="flex flex-col h-full select-none">
      {/* 1. Header: Logo & Branding */}
      <div
        className={`flex items-center h-16 border-b border-[#303438] shrink-0 transition-all duration-200 ${
          collapsed ? 'justify-center px-2' : 'justify-between px-4'
        }`}
      >
        {collapsed ? (
          <BrandLogo
            variant="mark"
            onClick={() => handleNavClick('dashboard')}
            className="hover:scale-105 transition-transform"
          />
        ) : (
          <BrandLogo
            variant="navbar"
            onClick={() => handleNavClick('dashboard')}
            className="hover:opacity-90 transition-opacity"
          />
        )}

        {/* Mobile close button inside drawer */}
        <button
          onClick={onCloseMobile}
          className="md:hidden p-1.5 rounded-lg text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D]"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* 2. Primary Action Button: "Start Practice" */}
      <div className={`pt-4 pb-2 shrink-0 ${collapsed ? 'px-2' : 'px-3'}`}>
        {collapsed ? (
          <div className="relative group flex justify-center">
            <button
              onClick={() => handleNavClick('live')}
              className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all shadow-md ${
                currentTab === 'live'
                  ? 'bg-[#7FEA35] text-[#050505] ring-2 ring-[#7FEA35]/50'
                  : 'bg-[#7FEA35] text-[#050505] hover:bg-[#94EE58]'
              }`}
              title="Start Practice"
              aria-label="Start Practice"
            >
              <Video className="w-5 h-5" />
            </button>
            <div className="absolute left-full ml-3 px-2.5 py-1 rounded bg-[#181B1D] text-[#F5F5F5] text-xs font-semibold border border-[#303438] whitespace-nowrap shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50">
              Start Practice
            </div>
          </div>
        ) : (
          <button
            onClick={() => handleNavClick('live')}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] font-bold text-sm transition-all shadow-md shadow-[#7FEA35]/15 cursor-pointer group"
          >
            <Video className="w-4 h-4 text-[#050505] group-hover:scale-110 transition-transform" />
            <span>Start Practice</span>
          </button>
        )}
      </div>

      {/* 3. Navigation Groups */}
      <nav
        aria-label="Main"
        className="flex-1 overflow-y-auto overflow-x-hidden py-2 space-y-4 px-2 scrollbar-thin scrollbar-thumb-[#303438]"
      >
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="space-y-1">
            {!collapsed && (
              <div className="px-2 text-[10px] font-mono uppercase tracking-widest text-[#A5A9AD] font-bold">
                {group.title}
              </div>
            )}
            {collapsed && (
              <div className="h-px bg-[#303438]/50 my-2 mx-1" />
            )}
            <ul className="space-y-1">
              {group.items.map((item) => {
                const IconComponent = item.icon;
                const isActive = currentTab === item.id;

                return (
                  <li key={item.id} className="relative group">
                    <button
                      onClick={() => handleNavClick(item.id)}
                      className={`w-full flex items-center rounded-lg transition-all duration-150 cursor-pointer ${
                        collapsed
                          ? 'justify-center h-10 w-10 mx-auto'
                          : 'px-2.5 py-2 space-x-2.5'
                      } ${
                        isActive
                          ? 'bg-[#181B1D] text-[#7FEA35] font-semibold border border-[#7FEA35]/30 shadow-sm'
                          : 'text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D]/60'
                      }`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <IconComponent
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          isActive ? 'text-[#7FEA35]' : 'group-hover:text-[#F5F5F5]'
                        }`}
                      />
                      {!collapsed && (
                        <span className="text-xs truncate tracking-tight text-left">
                          {item.label}
                        </span>
                      )}
                    </button>

                    {/* Collapsed Tooltip */}
                    {collapsed && (
                      <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded bg-[#181B1D] text-[#F5F5F5] text-xs font-medium border border-[#303438] whitespace-nowrap shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50">
                        <span className="text-[10px] text-[#A5A9AD] block uppercase font-mono">
                          {group.title}
                        </span>
                        {item.label}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* 4. Bottom Utilities Section */}
      <div className="shrink-0 border-t border-[#303438] p-2 space-y-2 bg-[#08090A]">
        {/* About CricketIQ */}
        <div className="relative group">
          <button
            onClick={() => handleNavClick('about')}
            className={`w-full flex items-center rounded-lg transition-all duration-150 cursor-pointer ${
              collapsed
                ? 'justify-center h-10 w-10 mx-auto'
                : 'px-2.5 py-2 space-x-2.5'
            } ${
              currentTab === 'about'
                ? 'bg-[#181B1D] text-[#7FEA35] font-semibold border border-[#7FEA35]/30'
                : 'text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D]/60'
            }`}
          >
            <Info className="w-4 h-4 shrink-0" />
            {!collapsed && <span className="text-xs truncate">About</span>}
          </button>
          {collapsed && (
            <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded bg-[#181B1D] text-[#F5F5F5] text-xs font-medium border border-[#303438] whitespace-nowrap shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50">
              About
            </div>
          )}
        </div>

        {/* AI Online/Degraded/Offline Status Indicator */}
        <div className="relative group">
          <div
            title={healthIssues.length > 0 ? healthIssues.join(' | ') : healthStatus === 'healthy' ? `AI Engine Healthy (${latencyMs ?? 0}ms)` : 'Checking health...'}
            className={`flex items-center rounded-lg bg-[#111315] border border-[#303438] ${
              collapsed
                ? 'justify-center h-9 w-9 mx-auto'
                : 'px-2.5 py-1.5 justify-between'
            }`}
          >
            <div className="flex items-center space-x-2">
              <span className="relative flex h-2 w-2 shrink-0">
                {healthStatus === 'healthy' ? (
                  <>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#7FEA35] opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#7FEA35]" />
                  </>
                ) : healthStatus === 'degraded' ? (
                  <>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
                  </>
                ) : healthStatus === 'offline' ? (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
                ) : (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-500 animate-pulse" />
                )}
              </span>
              {!collapsed && (
                <span className="text-[11px] font-mono text-[#F5F5F5]">
                  {healthStatus === 'checking'
                    ? 'Checking AI...'
                    : healthStatus === 'healthy'
                    ? 'AI Online'
                    : healthStatus === 'degraded'
                    ? 'AI Degraded'
                    : 'AI Offline'}
                </span>
              )}
            </div>
            {!collapsed && latencyMs !== null && (
              <span className={`text-[10px] font-mono font-medium ${
                healthStatus === 'healthy' ? 'text-[#7FEA35]' : healthStatus === 'degraded' ? 'text-amber-400' : 'text-rose-400'
              }`}>
                {latencyMs}ms
              </span>
            )}
          </div>
          {/* Tooltip for issues or collapsed view */}
          <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 px-2.5 py-1.5 rounded-lg bg-[#181B1D] text-[#F5F5F5] text-xs font-medium border border-[#303438] whitespace-nowrap shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 space-y-1">
            <div className="font-bold flex items-center space-x-1.5">
              <span className={`w-2 h-2 rounded-full ${healthStatus === 'healthy' ? 'bg-[#7FEA35]' : healthStatus === 'degraded' ? 'bg-amber-400' : 'bg-rose-500'}`} />
              <span>
                {healthStatus === 'healthy'
                  ? `AI Engine Online (${latencyMs ?? 0}ms)`
                  : healthStatus === 'degraded'
                  ? 'AI Subsystem Degraded'
                  : 'AI Backend Offline'}
              </span>
            </div>
            {healthIssues.length > 0 && (
              <div className="text-[10px] font-mono text-[#A5A9AD] max-w-xs whitespace-normal">
                {healthIssues.join(' • ')}
              </div>
            )}
          </div>
        </div>

        {/* Active Session Chip */}
        <div className="relative group">
          <div
            onClick={activeSessionId ? handleCopySession : undefined}
            title={activeSessionId ? `Session ID: ${activeSessionId} (Click to copy)` : 'No active session'}
            className={`flex items-center rounded-lg bg-[#111315] border border-[#303438] font-mono text-xs transition-colors ${
              activeSessionId ? 'cursor-pointer hover:border-[#7FEA35]/50' : 'cursor-default opacity-60'
            } ${
              collapsed
                ? 'justify-center h-9 w-9 mx-auto text-[#A5A9AD]'
                : 'px-2.5 py-1.5 justify-between'
            }`}
          >
            {collapsed ? (
              copiedSession ? (
                <Check className="w-3.5 h-3.5 text-[#7FEA35]" />
              ) : (
                <Radio className="w-3.5 h-3.5 text-[#A5A9AD]" />
              )
            ) : (
              <>
                <div className="flex items-center space-x-1.5 min-w-0">
                  <span className="text-[10px] uppercase tracking-wider text-[#A5A9AD]">SID:</span>
                  <span className="text-[11px] text-[#F5F5F5] truncate">
                    {displaySessionId}
                  </span>
                </div>
                {activeSessionId && (
                  <button
                    className="p-1 text-[#A5A9AD] hover:text-[#7FEA35] transition-colors"
                    aria-label="Copy session ID"
                  >
                    {copiedSession ? (
                      <Check className="w-3 h-3 text-[#7FEA35]" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                )}
              </>
            )}
          </div>

          {/* Full Session ID tooltip / Copied badge */}
          {collapsed && (
            <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded bg-[#181B1D] text-[#F5F5F5] text-xs font-mono border border-[#303438] whitespace-nowrap shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50">
              {copiedSession
                ? 'Copied to clipboard!'
                : activeSessionId
                ? `SID: ${activeSessionId}`
                : 'No active session'}
            </div>
          )}
          {!collapsed && copiedSession && (
            <div className="text-[10px] text-[#7FEA35] font-mono text-center">
              Copied to clipboard!
            </div>
          )}
        </div>

        {/* Collapse Toggle Button (Desktop only) */}
        <div className="hidden md:block pt-1">
          <button
            onClick={onToggleCollapse}
            className={`w-full flex items-center rounded-lg p-2 text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D] transition-colors text-xs font-mono ${
              collapsed ? 'justify-center' : 'justify-between'
            }`}
            title={collapsed ? 'Expand sidebar [' : 'Collapse sidebar ['}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <span className="text-[11px] text-[#A5A9AD]">Collapse</span>
                <div className="flex items-center space-x-1">
                  <span className="px-1.5 py-0.5 rounded bg-[#181B1D] border border-[#303438] text-[10px] text-[#A5A9AD]">
                    [
                  </span>
                  <ChevronLeft className="w-4 h-4" />
                </div>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Fixed/Sticky Sidebar */}
      <aside
        className={`hidden md:flex flex-col sticky top-0 h-screen shrink-0 bg-[#0A0C0E] border-r border-[#303438] z-30 transition-all duration-200 ease-in-out ${
          isCollapsed ? 'w-[72px]' : 'w-[260px]'
        }`}
      >
        {renderSidebarContent(isCollapsed)}
      </aside>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="md:hidden fixed inset-0 bg-black/70 backdrop-blur-sm z-40 transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Mobile Off-Canvas Drawer */}
      <aside
        className={`md:hidden fixed inset-y-0 left-0 w-[260px] bg-[#0A0C0E] border-r border-[#303438] z-50 transform transition-transform duration-200 ease-in-out ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Mobile Navigation"
      >
        {renderSidebarContent(false)}
      </aside>
    </>
  );
};

