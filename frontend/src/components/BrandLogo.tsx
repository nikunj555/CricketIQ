import React from 'react';

interface BrandLogoProps {
  variant?: 'full' | 'navbar' | 'mark' | 'hero';
  className?: string;
  onClick?: () => void;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  variant = 'full',
  className = '',
  onClick,
}) => {
  // Batsman Emblem SVG
  const BatsmanMark = ({ size = 36 }: { size?: number }) => (
    <div
      style={{ width: size, height: size }}
      className="relative shrink-0 rounded-xl bg-[#111315] border border-[#303438] flex items-center justify-center p-1.5 shadow-md shadow-black/40 overflow-hidden group"
    >
      {/* Background Kinetic Energy Glow */}
      <div className="absolute inset-0 bg-gradient-to-tr from-[#7FEA35]/15 via-transparent to-transparent opacity-80" />

      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10"
      >
        <defs>
          {/* Lime Green Motion Trail Gradient */}
          <linearGradient id="limeTrail" x1="15" y1="85" x2="85" y2="15" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#7FEA35" stopOpacity="0.1" />
            <stop offset="50%" stopColor="#7FEA35" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#94EE58" stopOpacity="1" />
          </linearGradient>

          {/* Bat Blade Gradient */}
          <linearGradient id="batGradient" x1="45" y1="50" x2="80" y2="20" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="70%" stopColor="#F5F5F5" />
            <stop offset="100%" stopColor="#7FEA35" />
          </linearGradient>
        </defs>

        {/* Dynamic Curved Kinetic Motion Arc */}
        <path
          d="M 18 78 C 22 55, 38 32, 68 20 C 78 16, 86 18, 88 22 C 89 26, 82 32, 70 38 C 50 48, 36 66, 32 82 Z"
          fill="url(#limeTrail)"
        />

        {/* Cricket Ball Impact Particle */}
        <circle cx="86" cy="22" r="4.5" fill="#7FEA35" />
        <circle cx="86" cy="22" r="7" stroke="#7FEA35" strokeWidth="1" strokeDasharray="2 2" opacity="0.6" />

        {/* Stylized White Batsman Silhouette */}
        {/* Head / Helmet */}
        <circle cx="46" cy="30" r="6" fill="#FFFFFF" />
        <path d="M 47 30 L 53 32 L 48 34 Z" fill="#7FEA35" /> {/* Helmet visor slit */}

        {/* Torso & Shoulders leaning forward into drive */}
        <path
          d="M 43 36 C 41 42, 40 48, 42 54 L 49 53 C 50 47, 49 41, 46 36 Z"
          fill="#FFFFFF"
        />

        {/* Lead Arm (Top Hand driving high) */}
        <path
          d="M 45 37 L 54 39 L 60 46"
          stroke="#FFFFFF"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Rear Arm (Bottom Hand supporting blade) */}
        <path
          d="M 43 40 L 50 44 L 58 48"
          stroke="#CBD5E1"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Cricket Bat (Flowing upwards into follow-through) */}
        <line
          x1="55"
          y1="50"
          x2="80"
          y2="22"
          stroke="url(#batGradient)"
          strokeWidth="4"
          strokeLinecap="round"
        />
        {/* Bat Handle Grip */}
        <line
          x1="53"
          y1="53"
          x2="59"
          y2="46"
          stroke="#FFFFFF"
          strokeWidth="2.5"
          strokeLinecap="round"
        />

        {/* Front Leg (Deep forward stride & knee bend) */}
        <path
          d="M 42 54 L 56 64 L 62 82"
          stroke="#FFFFFF"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Front Foot Ground Anchor */}
        <ellipse cx="64" cy="83" rx="4" ry="2" fill="#FFFFFF" />

        {/* Rear Leg (Braced back leg on toe) */}
        <path
          d="M 41 54 L 32 66 L 24 78"
          stroke="#94A3B8"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Rear Toe */}
        <circle cx="23" cy="79" r="2" fill="#94A3B8" />

        {/* Ground Crease Line */}
        <line x1="15" y1="84" x2="85" y2="84" stroke="#303438" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  );

  // Variant: Compact Mark Only
  if (variant === 'mark') {
    return (
      <div
        onClick={onClick}
        className={`inline-flex items-center cursor-pointer select-none ${className}`}
        title="CricketIQ — AI Batting Coach"
      >
        <BatsmanMark size={38} />
      </div>
    );
  }

  // Variant: Top Navigation Bar Logo
  if (variant === 'navbar') {
    return (
      <div
        onClick={onClick}
        className={`inline-flex items-center space-x-2.5 cursor-pointer select-none group ${className}`}
        title="CricketIQ — AI Powered Batting Coach"
      >
        <BatsmanMark size={36} />
        <div className="flex flex-col">
          <div className="flex items-center space-x-1">
            <span className="text-lg font-black tracking-tight text-[#F5F5F5] group-hover:text-white transition-colors">
              Cricket
            </span>
            <span className="text-lg font-black tracking-tight text-[#7FEA35]">
              IQ
            </span>
            <span className="ml-1 text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-bold tracking-wider">
              AI COACH
            </span>
          </div>
          <span className="text-[9px] font-mono tracking-widest text-[#A5A9AD] uppercase -mt-0.5">
            Batting Technique AI
          </span>
        </div>
      </div>
    );
  }

  // Variant: Hero Landing Showcase (Dashboard Hero Banner)
  if (variant === 'hero') {
    return (
      <div className={`flex flex-col sm:flex-row items-start sm:items-center gap-4 ${className}`}>
        <BatsmanMark size={64} />
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl sm:text-4xl font-black tracking-tight text-[#F5F5F5]">
              Cricket<span className="text-[#7FEA35]">IQ</span>
            </h1>
            <span className="inline-flex items-center space-x-1.5 text-[10px] sm:text-xs uppercase font-mono px-2 py-0.5 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30 font-bold tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-[#7FEA35] animate-pulse" />
              <span>Version 2.0 Live</span>
            </span>
          </div>
          <div className="text-xs sm:text-sm font-mono tracking-widest uppercase text-[#7FEA35] font-bold">
            AI POWERED BATTING COACH
          </div>
        </div>
      </div>
    );
  }

  // Variant: Full Complete Brand Mark (Default)
  return (
    <div
      onClick={onClick}
      className={`inline-flex items-center space-x-3 cursor-pointer select-none group ${className}`}
    >
      <BatsmanMark size={44} />
      <div className="flex flex-col">
        <div className="flex items-center space-x-1.5">
          <span className="text-xl font-black tracking-tight text-[#F5F5F5]">
            Cricket
          </span>
          <span className="text-xl font-black tracking-tight text-[#7FEA35]">
            IQ
          </span>
        </div>
        <div className="text-[10px] font-mono tracking-widest uppercase text-[#7FEA35] font-bold">
          AI POWERED BATTING COACH
        </div>
      </div>
    </div>
  );
};