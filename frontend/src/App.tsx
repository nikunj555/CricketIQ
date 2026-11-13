import React, { useState, useEffect, Suspense, lazy } from 'react';
import { Sidebar } from './components/Sidebar';
import { NavTab } from './types/cricket';
import { BrandLogo } from './components/BrandLogo';
import { Menu, Sparkles, Command } from 'lucide-react';
import { api } from './services/api';
import { MotionProvider } from './context/MotionContext';
import { CommandPalette } from './components/CommandPalette';
import { SystemHealthBanner } from './components/SystemHealthBanner';

// Code-split pages for cinematic load times & chunk isolation
const LiveCoachPage = lazy(() => import('./pages/LiveCoachPage').then(m => ({ default: m.LiveCoachPage })));
const ShotLibraryPage = lazy(() => import('./pages/ShotLibraryPage').then(m => ({ default: m.ShotLibraryPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then(m => ({ default: m.UploadPage })));
const WorkspacePage = lazy(() => import('./pages/WorkspacePage').then(m => ({ default: m.WorkspacePage })));
const BiomechanicsPage = lazy(() => import('./pages/BiomechanicsPage').then(m => ({ default: m.BiomechanicsPage })));
const PhasesPage = lazy(() => import('./pages/PhasesPage').then(m => ({ default: m.PhasesPage })));
const ComparisonPage = lazy(() => import('./pages/ComparisonPage').then(m => ({ default: m.ComparisonPage })));
const ProgressPage = lazy(() => import('./pages/ProgressPage').then(m => ({ default: m.ProgressPage })));
const EvaluationPage = lazy(() => import('./pages/EvaluationPage').then(m => ({ default: m.EvaluationPage })));
const AboutPage = lazy(() => import('./pages/AboutPage').then(m => ({ default: m.AboutPage })));

function PageSkeleton() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-8 space-y-4">
      <div className="relative">
        <div className="w-12 h-12 rounded-2xl border-2 border-[#7FEA35]/30 border-t-[#7FEA35] animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-[#7FEA35] animate-pulse" />
        </div>
      </div>
      <div className="text-center space-y-1">
        <p className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase">
          Loading Biomechanical Viewport
        </p>
        <p className="text-[11px] text-slate-500 font-mono">
          Calibrating kinematics & 3D telemetry...
        </p>
      </div>
    </div>
  );
}

export function App() {
  // Mode A: Live Batting Coach is the primary default experience
  const [currentTab, setCurrentTab] = useState<NavTab>('live');
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [targetShot, setTargetShot] = useState<string>('Cover Drive');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Sidebar collapse state with localStorage persistence
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('cricketiq_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const toggleSidebarCollapse = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('cricketiq_sidebar_collapsed', String(next));
      } catch {}
      return next;
    });
  };

  // Global keyboard shortcuts: '[' for sidebar, 'Cmd/Ctrl + K' for Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
        return;
      }
      if (
        e.key === '[' &&
        !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)
      ) {
        e.preventDefault();
        toggleSidebarCollapse();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    // Load latest session
    api.listSessions(1).then((res) => {
      if (res.sessions.length > 0) {
        setActiveSessionId(res.sessions[0].session_id);
      }
    }).catch(() => {});
  }, []);

  const handleSessionSelected = (sessionId: string) => {
    setActiveSessionId(sessionId);
  };

  const handleSelectShotFromPalette = (shotName: string) => {
    setTargetShot(shotName);
    setCurrentTab('library');
  };

  return (
    <MotionProvider>
      <div className="min-h-screen bg-[#050505] text-slate-100 flex flex-col font-sans selection:bg-[#7FEA35] selection:text-[#050505] relative antialiased">
        {/* Subtle Sports-Tech Scanline Background Grid */}
        <div className="fixed inset-0 pointer-events-none bg-scanlines opacity-40 z-0" />

        {/* Global Command Palette (Ctrl/Cmd + K) */}
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
          onSelectTab={(tab) => {
            setCurrentTab(tab);
            setIsCommandPaletteOpen(false);
          }}
          onSelectShot={handleSelectShotFromPalette}
        />

        {/* Mobile Top Header (hidden on desktop md:) */}
        <header className="md:hidden flex items-center justify-between px-4 h-14 bg-[#0A0C0E]/90 backdrop-blur-md border-b border-[#303438] sticky top-0 z-20">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsMobileNavOpen(true)}
              className="p-1.5 rounded-lg text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#181B1D] cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <BrandLogo
              variant="navbar"
              onClick={() => setCurrentTab('dashboard')}
            />
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="p-1.5 rounded-lg text-[#A5A9AD] hover:text-[#7FEA35] hover:bg-[#181B1D] cursor-pointer"
              title="Command Palette (Ctrl+K)"
            >
              <Command className="w-4 h-4" />
            </button>
            {activeSessionId && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#181B1D] text-[#7FEA35] border border-[#303438]">
                {activeSessionId.slice(0, 6)}...
              </span>
            )}
          </div>
        </header>

        {/* Main Container: Sticky/Collapsible Sidebar + Page Content */}
        <div className="flex flex-1 min-h-0 relative z-10">
          <Sidebar
            currentTab={currentTab}
            onSelectTab={setCurrentTab}
            activeSessionId={activeSessionId}
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={toggleSidebarCollapse}
            isMobileOpen={isMobileNavOpen}
            onCloseMobile={() => setIsMobileNavOpen(false)}
          />

          <div className="flex-1 flex flex-col min-w-0">
            <SystemHealthBanner />
            <main className="flex-1 pb-16">
              <Suspense fallback={<PageSkeleton />}>
                {/* Mode A: Primary Real-Time Live AI Batting Coach */}
                {currentTab === 'live' && (
                  <LiveCoachPage
                    onSelectTab={setCurrentTab}
                    onSelectSession={handleSessionSelected}
                    initialTargetShot={targetShot}
                  />
                )}

                {/* Centralized Shot Library */}
                {currentTab === 'library' && (
                  <ShotLibraryPage
                    onSelectTab={setCurrentTab}
                    onSelectShotForAction={(shotName) => setTargetShot(shotName)}
                    onSelectSession={handleSessionSelected}
                  />
                )}

                {/* Mode B: Detailed Video Analysis & Analytics Suite */}
                {currentTab === 'dashboard' && (
                  <DashboardPage
                    onSelectTab={setCurrentTab}
                    onSelectSession={handleSessionSelected}
                  />
                )}

                {currentTab === 'upload' && (
                  <UploadPage
                    onSessionCreated={handleSessionSelected}
                    onSelectTab={setCurrentTab}
                    initialShotType={targetShot}
                  />
                )}

                {currentTab === 'workspace' && (
                  <WorkspacePage
                    sessionId={activeSessionId}
                    onSelectTab={setCurrentTab}
                    onSelectSession={handleSessionSelected}
                  />
                )}

                {currentTab === 'biomechanics' && (
                  <BiomechanicsPage
                    sessionId={activeSessionId}
                    onSelectTab={setCurrentTab}
                  />
                )}

                {currentTab === 'phases' && (
                  <PhasesPage
                    sessionId={activeSessionId}
                    onSelectTab={setCurrentTab}
                  />
                )}

                {currentTab === 'comparison' && (
                  <ComparisonPage
                    sessionId={activeSessionId}
                    onSelectTab={setCurrentTab}
                    onSelectSession={handleSessionSelected}
                  />
                )}

                {currentTab === 'progress' && (
                  <ProgressPage
                    onSelectSession={handleSessionSelected}
                    onSelectTab={setCurrentTab}
                  />
                )}

                {currentTab === 'evaluation' && <EvaluationPage />}

                {currentTab === 'about' && <AboutPage onSelectTab={setCurrentTab} />}
              </Suspense>
            </main>

            {/* Sports-Tech Brand Footer */}
            <footer className="border-t border-[#303438] bg-[#050505]/95 backdrop-blur-md py-8 text-xs text-[#A5A9AD]">
              <div className="max-w-[1550px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                  <span className="text-[#F5F5F5] font-black text-sm tracking-tight">
                    Cricket<span className="text-[#7FEA35]">IQ</span>
                  </span>
                  <span className="text-[#303438]">|</span>
                  <span className="text-[#7FEA35] font-bold tracking-wider text-[11px] font-mono">
                    AI POWERED BATTING COACH
                  </span>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-3 text-[11px] text-[#A5A9AD] font-mono">
                  <span>Real-Time Practice</span>
                  <span>•</span>
                  <span>Video Assessment</span>
                  <span>•</span>
                  <span>25 Shot Library</span>
                  <span>•</span>
                  <span>Kinematic Ghost</span>
                  <span>•</span>
                  <button
                    onClick={() => setIsCommandPaletteOpen(true)}
                    className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-[#181B1D] text-slate-300 hover:text-white border border-[#303438] cursor-pointer"
                  >
                    <Command className="w-3 h-3 text-[#7FEA35]" />
                    <span>K for Quick Jump</span>
                  </button>
                </div>
              </div>
            </footer>
          </div>
        </div>
      </div>
    </MotionProvider>
  );
}

export default App;
