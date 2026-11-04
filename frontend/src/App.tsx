import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { NavTab } from './types/cricket';
import { LiveCoachPage } from './pages/LiveCoachPage';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { BiomechanicsPage } from './pages/BiomechanicsPage';
import { PhasesPage } from './pages/PhasesPage';
import { ComparisonPage } from './pages/ComparisonPage';
import { ProgressPage } from './pages/ProgressPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { AboutPage } from './pages/AboutPage';
import { ShotLibraryPage } from './pages/ShotLibraryPage';
import { BrandLogo } from './components/BrandLogo';
import { Menu } from 'lucide-react';
import { api } from './services/api';

export function App() {
  // Mode A: Live Batting Coach is the primary default experience
  const [currentTab, setCurrentTab] = useState<NavTab>('live');
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [targetShot, setTargetShot] = useState<string>('Cover Drive');

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

  // Global keyboard shortcut '[' to collapse/expand sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
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

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-navy-950">
      {/* Mobile Top Header (hidden on desktop md:) */}
      <header className="md:hidden flex items-center justify-between px-4 h-14 bg-[#0A0C0E] border-b border-[#303438] sticky top-0 z-20">
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
        {activeSessionId && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#181B1D] text-[#7FEA35] border border-[#303438]">
            {activeSessionId.slice(0, 6)}...
          </span>
        )}
      </header>

      {/* Main Container: Sticky/Collapsible Sidebar + Page Content */}
      <div className="flex flex-1 min-h-0">
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
          <main className="flex-1 pb-16">
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
          </main>

          {/* Sports-Tech Brand Footer */}
          <footer className="border-t border-[#303438] bg-[#050505] py-8 text-xs text-[#A5A9AD]">
            <div className="max-w-[1550px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center space-x-3">
                <span className="text-[#F5F5F5] font-black text-sm">
                  Cricket<span className="text-[#7FEA35]">IQ</span>
                </span>
                <span className="text-[#303438]">|</span>
                <span className="text-[#7FEA35] font-bold tracking-wider text-[11px] font-mono">
                  AI POWERED BATTING COACH
                </span>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3 text-[11px] text-[#A5A9AD] font-medium">
                <span>Real-Time Practice</span>
                <span>•</span>
                <span>Video Technique Assessment</span>
                <span>•</span>
                <span>25 Shot Library</span>
                <span>•</span>
                <span>Movement Tracking</span>
                <span>•</span>
                <span>Practice History</span>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default App;
