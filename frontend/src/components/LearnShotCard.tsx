import React from 'react';
import { ExternalLink, GraduationCap } from 'lucide-react';
import { LearningVideo } from '../types/cricket';

interface LearnShotCardProps {
  videos?: LearningVideo[] | null;
  className?: string;
}

export const LearnShotCard: React.FC<LearnShotCardProps> = ({ videos, className = '' }) => {
  if (!videos || videos.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {videos.map((vid, idx) => {
        const isRelated = vid.match === 'related';

        return (
          <div
            key={vid.url || idx}
            className="p-4 rounded-xl bg-[#111315] border border-[#303438] hover:border-[#7FEA35]/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
          >
            <div className="space-y-1 min-w-0">
              <div className="flex items-center space-x-2">
                <GraduationCap className="w-4 h-4 text-[#7FEA35] shrink-0" />
                <h4 className="text-sm font-bold text-[#F5F5F5] truncate">
                  Learn this shot: {vid.title}
                </h4>
              </div>

              {isRelated && (
                <div className="text-[11px] font-mono text-amber-400 font-semibold pl-6">
                  Similar technique
                </div>
              )}

              <p className="text-xs text-[#A5A9AD] pl-6">
                {vid.channel || 'Sikana Education'}
              </p>
            </div>

            <a
              href={vid.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center space-x-1.5 px-3.5 py-2 rounded-lg bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] text-xs font-bold transition-all shrink-0 cursor-pointer shadow-sm w-full sm:w-auto"
            >
              <span>Open lesson</span>
              <ExternalLink className="w-3.5 h-3.5 stroke-[2.5]" />
            </a>
          </div>
        );
      })}
    </div>
  );
};
