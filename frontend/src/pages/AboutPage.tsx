import React from 'react';
import {
  Video,
  Activity,
  Layers,
  TrendingUp,
  CheckCircle2,
  ShieldAlert,
  Camera,
  Target,
  Sparkles,
  Compass,
  ArrowRight
} from 'lucide-react';
import { NavTab } from '../types/cricket';

interface AboutPageProps {
  onSelectTab?: (tab: NavTab) => void;
}

export const AboutPage: React.FC<AboutPageProps> = ({ onSelectTab }) => {
  return (
    <div className="max-w-[1550px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10 animate-in fade-in duration-200">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-[#303438]">
        <div className="space-y-2 max-w-3xl">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#7FEA35]/15 border border-[#7FEA35]/30 text-xs font-mono text-[#7FEA35] font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered Cricket Batting Coach</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-[#F5F5F5] tracking-tight">
            Master Your Cricket Batting Technique
          </h1>
          <p className="text-sm text-[#A5A9AD] leading-relaxed">
            CricketIQ transforms ordinary practice videos and live camera feeds into instant, objective movement insights. Designed for cricketers, coaches, and academies seeking clear, evidence-based feedback after every shot.
          </p>
        </div>

        {onSelectTab && (
          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => onSelectTab('live')}
              className="px-5 py-2.5 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] font-bold text-xs transition-all shadow-lg shadow-[#7FEA35]/20 cursor-pointer flex items-center space-x-1.5"
            >
              <Video className="w-4 h-4 fill-current" />
              <span>Start Live Practice</span>
            </button>
            <button
              onClick={() => onSelectTab('library')}
              className="px-4 py-2.5 rounded-xl bg-[#181B1D] hover:bg-[#303438] text-[#F5F5F5] font-semibold text-xs border border-[#303438] transition-colors cursor-pointer"
            >
              Explore Shot Library
            </button>
          </div>
        )}
      </div>

      {/* The 4-Step How It Works Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-[#F5F5F5] uppercase tracking-wider font-mono">
            How CricketIQ Works
          </h2>
          <p className="text-xs text-[#A5A9AD]">
            A seamless, four-step training loop designed for practice on the field or in the nets.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Step 1 */}
          <div className="p-5 rounded-2xl bg-[#181B1D] border border-[#303438] space-y-3 relative group hover:border-[#7FEA35]/50 transition-all">
            <div className="w-8 h-8 rounded-lg bg-[#7FEA35]/15 text-[#7FEA35] font-mono font-bold text-sm flex items-center justify-center">
              1
            </div>
            <h3 className="text-sm font-bold text-[#F5F5F5]">Record or Upload</h3>
            <p className="text-xs text-[#A5A9AD] leading-relaxed">
              Place your phone or laptop on a tripod side-on to your crease and practice live, or upload existing net practice videos.
            </p>
          </div>

          {/* Step 2 */}
          <div className="p-5 rounded-2xl bg-[#181B1D] border border-[#303438] space-y-3 relative group hover:border-[#7FEA35]/50 transition-all">
            <div className="w-8 h-8 rounded-lg bg-[#7FEA35]/15 text-[#7FEA35] font-mono font-bold text-sm flex items-center justify-center">
              2
            </div>
            <h3 className="text-sm font-bold text-[#F5F5F5]">Movement Analysis</h3>
            <p className="text-xs text-[#A5A9AD] leading-relaxed">
              CricketIQ tracks key body positions across the swing, calculating front knee bend, head position, torso angle, and arm elevation.
            </p>
          </div>

          {/* Step 3 */}
          <div className="p-5 rounded-2xl bg-[#181B1D] border border-[#303438] space-y-3 relative group hover:border-[#7FEA35]/50 transition-all">
            <div className="w-8 h-8 rounded-lg bg-[#7FEA35]/15 text-[#7FEA35] font-mono font-bold text-sm flex items-center justify-center">
              3
            </div>
            <h3 className="text-sm font-bold text-[#F5F5F5]">Understand the Shot</h3>
            <p className="text-xs text-[#A5A9AD] leading-relaxed">
              Receive immediate, plain-English coaching observations grounded in your actual movement measurements and targeted drills.
            </p>
          </div>

          {/* Step 4 */}
          <div className="p-5 rounded-2xl bg-[#181B1D] border border-[#303438] space-y-3 relative group hover:border-[#7FEA35]/50 transition-all">
            <div className="w-8 h-8 rounded-lg bg-[#7FEA35]/15 text-[#7FEA35] font-mono font-bold text-sm flex items-center justify-center">
              4
            </div>
            <h3 className="text-sm font-bold text-[#F5F5F5]">Track Your Progress</h3>
            <p className="text-xs text-[#A5A9AD] leading-relaxed">
              Compare your latest stroke against previous attempts or textbook benchmarks to see how your balance and footwork improve over time.
            </p>
          </div>
        </div>
      </div>

      {/* Why Objective Video Coaching Matters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-[#181B1D] border border-[#303438] space-y-4">
          <h3 className="text-base font-bold text-[#F5F5F5] flex items-center space-x-2">
            <Target className="w-4 h-4 text-[#7FEA35]" />
            <span>Why Objective Video Analysis Matters</span>
          </h3>
          <p className="text-xs text-[#A5A9AD] leading-relaxed">
            Cricket batting happens in fractions of a second. At game speed, it is difficult for a batter or an observer to accurately evaluate whether the front knee was sufficiently flexed, whether the head stayed directly over the line of the ball, or whether the leading elbow collapsed during downswing.
          </p>
          <p className="text-xs text-[#A5A9AD] leading-relaxed">
            CricketIQ replaces guesswork with clear, visual evidence so you understand exactly what happened during contact and what to adjust on your very next repetition.
          </p>
        </div>

        {/* Camera Positioning & Setup Tips */}
        <div className="p-6 rounded-2xl bg-[#181B1D] border border-[#303438] space-y-4">
          <h3 className="text-base font-bold text-[#F5F5F5] flex items-center space-x-2">
            <Camera className="w-4 h-4 text-[#7FEA35]" />
            <span>Camera Setup for Best Results</span>
          </h3>
          <ul className="space-y-2 text-xs text-[#A5A9AD]">
            <li className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-[#7FEA35] shrink-0 mt-0.5" />
              <span><strong>Side-on Angle:</strong> Position the camera 3 to 5 meters away, perpendicular (90°) to your batting crease, for clear stride and elbow tracking.</span>
            </li>
            <li className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-[#7FEA35] shrink-0 mt-0.5" />
              <span><strong>Waist Height:</strong> Set your tripod or phone stand at approximately waist level to minimize perspective distortion.</span>
            </li>
            <li className="flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-[#7FEA35] shrink-0 mt-0.5" />
              <span><strong>Good Lighting:</strong> Well-lit natural outdoor light or bright indoor practice nets yield crisp video with minimal motion blur.</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Coaching Standards & Safety Notice */}
      <div className="p-6 rounded-2xl bg-[#111315] border border-[#303438] space-y-3">
        <div className="flex items-center space-x-2 text-[#F5F5F5] font-bold text-sm">
          <ShieldAlert className="w-4 h-4 text-[#7FEA35]" />
          <span>Coaching Standards & Safety Boundary</span>
        </div>
        <p className="text-xs text-[#A5A9AD] leading-relaxed">
          CricketIQ is a supplementary sports-technology tool created to assist batters and coaches in analyzing batting movement. All feedback and suggested drills are evidence-grounded technical suggestions derived from established cricket coaching literature.
        </p>
        <p className="text-[11px] text-[#A5A9AD] leading-relaxed">
          CricketIQ does not diagnose physical or musculoskeletal injuries, guarantee match performance outcomes, or replace the expertise of certified human cricket coaches. Always warm up thoroughly before practice and train within your physical limits.
        </p>
      </div>
    </div>
  );
};
