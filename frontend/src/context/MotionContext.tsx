import React, { createContext, useContext, useState, useEffect } from 'react';

interface MotionContextType {
  isReducedMotion: boolean;
  toggleReducedMotion: () => void;
}

const MotionContext = createContext<MotionContextType>({
  isReducedMotion: false,
  toggleReducedMotion: () => {},
});

export const MotionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isReducedMotion, setIsReducedMotion] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('cricketiq_reduced_motion');
      if (saved !== null) return saved === 'true';
    } catch {}
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });

  useEffect(() => {
    try {
      localStorage.setItem('cricketiq_reduced_motion', String(isReducedMotion));
    } catch {}
  }, [isReducedMotion]);

  const toggleReducedMotion = () => {
    setIsReducedMotion((prev) => !prev);
  };

  return (
    <MotionContext.Provider value={{ isReducedMotion, toggleReducedMotion }}>
      {children}
    </MotionContext.Provider>
  );
};

export const useMotionSettings = () => useContext(MotionContext);
