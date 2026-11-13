import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three/examples/jsm/controls/OrbitControls.js';
import * as THREE from 'three';
import {
  Play,
  Pause,
  RotateCcw,
  Camera,
  Layers,
  Sparkles,
  Eye,
  Sliders
} from 'lucide-react';
import { BatterSkeleton3D } from './BatterSkeleton3D';
import { PitchEnvironment3D } from './PitchEnvironment3D';
import { useMotionSettings } from '../../context/MotionContext';
import { ShotVariant } from '../../data/shotVariants';

export interface Batter3DCanvasProps {
  shotName?: string;
  variant?: ShotVariant;
  replayToken?: number;
  tempoScale?: number;
  initialPhase?: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery';
  isGhost?: boolean;
  ghostColor?: string;
  highlightJoint?: string | null;
  showTrail?: boolean;
  showControls?: boolean;
  showPhaseScrubber?: boolean;
  showCameraPresets?: boolean;
  autoOrbitDefault?: boolean;
  className?: string;
  height?: string | number;
  onPhaseChange?: (phase: string) => void;
}

export function isWebGLAvailable(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

const PHASES: Array<{
  key: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery';
  label: string;
}> = [
  { key: 'stance', label: 'Stance' },
  { key: 'backlift', label: 'Backlift' },
  { key: 'stride', label: 'Stride' },
  { key: 'downswing', label: 'Downswing' },
  { key: 'impact', label: 'Impact' },
  { key: 'follow_through', label: 'Follow' },
  { key: 'recovery', label: 'Reset' }
];

export const Batter3DCanvas: React.FC<Batter3DCanvasProps> = ({
  shotName = 'Cover Drive',
  variant,
  replayToken = 0,
  tempoScale = 1,
  initialPhase,
  isGhost = false,
  ghostColor = '#00f0ff',
  highlightJoint = null,
  showTrail = true,
  showControls = true,
  showPhaseScrubber = true,
  showCameraPresets = true,
  autoOrbitDefault = false,
  className = '',
  height = '100%',
  onPhaseChange
}) => {
  const { isReducedMotion } = useMotionSettings();
  const [hasWebGL, setHasWebGL] = useState(true);
  const [isPlaying, setIsPlaying] = useState(!initialPhase);
  const [selectedPhase, setSelectedPhase] = useState<'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery' | undefined>(initialPhase);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [isLeftHanded, setIsLeftHanded] = useState(false);
  const [autoOrbit, setAutoOrbit] = useState(autoOrbitDefault && !isReducedMotion);
  const [cameraPreset, setCameraPreset] = useState<'side' | 'front' | 'angle'>('side');

  const controlsRef = useRef<OrbitControlsImpl | null>(null);

  useEffect(() => {
    setHasWebGL(isWebGLAvailable());
  }, []);

  useEffect(() => {
    if (initialPhase) {
      setSelectedPhase(initialPhase);
      setIsPlaying(false);
    }
  }, [initialPhase]);

  // Handle camera presets
  const applyCameraPreset = (preset: 'side' | 'front' | 'angle') => {
    setCameraPreset(preset);
    const controls = controlsRef.current;
    if (!controls) return;

    if (preset === 'side') {
      controls.object.position.set(0.0, 1.25, 3.2);
    } else if (preset === 'front') {
      controls.object.position.set(-3.2, 1.25, 0.0);
    } else {
      controls.object.position.set(-2.2, 1.5, 2.2);
    }
    controls.target.set(0, 1.0, 0);
    controls.update();
  };

  const handlePhaseClick = (phaseKey: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery') => {
    setSelectedPhase(phaseKey);
    setIsPlaying(false);
    onPhaseChange?.(phaseKey);
  };

  // WebGL Fallback
  if (!hasWebGL) {
    return (
      <div className={`relative bg-[#050505] rounded-2xl border border-[#303438] flex items-center justify-center p-6 ${className}`} style={{ height }}>
        <div className="text-center space-y-2">
          <p className="text-sm font-semibold text-slate-300">3D Acceleration Unavailable</p>
          <p className="text-xs text-slate-500">WebGL is disabled or unsupported on this display device.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`relative w-full rounded-2xl bg-gradient-to-b from-[#090B0D] via-[#050505] to-[#050505] border border-[#303438] overflow-hidden select-none ${className}`}
      style={{ height }}
    >
      {/* 3D WebGL Canvas Viewport */}
      <Canvas
        dpr={Math.min(2, typeof window !== 'undefined' ? window.devicePixelRatio : 1)}
        gl={{
          antialias: true,
          powerPreference: 'high-performance',
          alpha: true
        }}
        camera={{ position: [0.0, 1.25, 3.2], fov: 42 }}
      >
        <PerspectiveCamera makeDefault position={[0.0, 1.25, 3.2]} fov={42} />

        {/* Ambient & Key Lighting */}
        <ambientLight intensity={0.5} />
        <directionalLight position={[3, 5, 4]} intensity={1.2} color="#ffffff" />
        <directionalLight position={[-4, 3, -2]} intensity={0.4} color="#00f0ff" />
        <pointLight position={[0, 2.5, 0]} intensity={0.8} color="#7fea35" distance={6} />

        {/* Turf Pitch Ground Grid */}
        <PitchEnvironment3D />

        {/* The 3D Forward-Kinematics Batter Skeleton */}
        <BatterSkeleton3D
          shotName={shotName}
          variant={variant}
          replayToken={replayToken}
          currentPhaseKey={selectedPhase}
          isPlaying={isPlaying}
          playbackSpeed={playbackSpeed * tempoScale}
          isLeftHanded={isLeftHanded}
          isGhost={isGhost}
          ghostColor={ghostColor}
          highlightJoint={highlightJoint}
          showTrail={showTrail}
        />

        {/* Interactive Orbit Controls */}
        <OrbitControls
          ref={controlsRef as any}
          enableDamping
          dampingFactor={0.06}
          maxPolarAngle={Math.PI / 2 + 0.04}
          minDistance={1.2}
          maxDistance={5.5}
          target={[0, 1.0, 0]}
          autoRotate={autoOrbit && isPlaying && !isReducedMotion}
          autoRotateSpeed={0.6}
        />
      </Canvas>

      {/* Top Floating Telemetry Overlay (Shot Title & Badges) */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 pointer-events-none">
        <div className="px-3 py-1 rounded-xl bg-[#111315]/85 border border-[#303438] backdrop-blur-md flex items-center space-x-2 shadow-md">
          <div className="w-2 h-2 rounded-full bg-[#7FEA35] animate-pulse" />
          <span className="text-xs font-bold text-white tracking-tight">{shotName}</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#7FEA35]/15 text-[#7FEA35] border border-[#7FEA35]/30">
            3D Kinematics
          </span>
        </div>

        {isGhost && (
          <div className="px-2.5 py-1 rounded-xl bg-cyan-950/80 border border-cyan-800 text-cyan-300 text-[10px] font-mono font-bold">
            Ideal Benchmark Ghost
          </div>
        )}
      </div>

      {/* Camera Presets & Left-Handed Toggle (Top Right) */}
      {showCameraPresets && (
        <div className="absolute top-3 right-3 z-10 flex items-center space-x-1.5">
          {/* Camera Angles */}
          <div className="flex items-center bg-[#111315]/85 border border-[#303438] rounded-xl p-0.5 backdrop-blur-md shadow-md">
            <button
              onClick={() => applyCameraPreset('side')}
              className={`px-2 py-1 text-[10px] font-mono font-bold rounded-lg transition-colors cursor-pointer ${
                cameraPreset === 'side'
                  ? 'bg-[#7FEA35] text-[#050505]'
                  : 'text-[#A5A9AD] hover:text-white'
              }`}
              title="Side-on Perspective (Ideal for Drives & Defensive)"
            >
              Side
            </button>
            <button
              onClick={() => applyCameraPreset('front')}
              className={`px-2 py-1 text-[10px] font-mono font-bold rounded-lg transition-colors cursor-pointer ${
                cameraPreset === 'front'
                  ? 'bg-[#7FEA35] text-[#050505]'
                  : 'text-[#A5A9AD] hover:text-white'
              }`}
              title="Front-on Crease Perspective"
            >
              Front
            </button>
            <button
              onClick={() => applyCameraPreset('angle')}
              className={`px-2 py-1 text-[10px] font-mono font-bold rounded-lg transition-colors cursor-pointer ${
                cameraPreset === 'angle'
                  ? 'bg-[#7FEA35] text-[#050505]'
                  : 'text-[#A5A9AD] hover:text-white'
              }`}
              title="45° Oblique Pitch Perspective"
            >
              45°
            </button>
          </div>

          {/* Left/Right Handedness Mirror Toggle */}
          <button
            onClick={() => setIsLeftHanded(!isLeftHanded)}
            className={`px-2.5 py-1 rounded-xl border text-[10px] font-mono font-bold backdrop-blur-md transition-colors cursor-pointer shadow-md ${
              isLeftHanded
                ? 'bg-[#00f0ff]/20 text-[#00f0ff] border-[#00f0ff]/50'
                : 'bg-[#111315]/85 text-[#A5A9AD] border-[#303438] hover:text-white'
            }`}
            title="Toggle Left/Right Handed Batter Pose"
          >
            {isLeftHanded ? 'LH' : 'RH'}
          </button>
        </div>
      )}

      {/* Bottom Floating Bar: 7-Phase Scrubber & Speed Controls */}
      {showControls && (
        <div className="absolute bottom-3 inset-x-3 z-10 flex flex-col sm:flex-row items-center justify-between gap-2 p-2 rounded-2xl bg-[#111315]/85 border border-[#303438] backdrop-blur-md shadow-xl">
          {/* Play/Pause & Speed */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1.5 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-[#050505] transition-colors cursor-pointer shadow-sm"
              title={isPlaying ? 'Pause Motion' : 'Play Looping Motion'}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
            </button>

            {/* Playback Speed Chips */}
            <div className="flex items-center bg-[#181B1D] border border-[#303438] rounded-xl p-0.5 text-[10px] font-mono">
              {[0.25, 0.5, 1.0, 1.5].map((spd) => (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  className={`px-1.5 py-0.5 rounded-lg font-bold transition-colors cursor-pointer ${
                    playbackSpeed === spd
                      ? 'bg-[#303438] text-[#7FEA35]'
                      : 'text-[#A5A9AD] hover:text-white'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>

          {/* 7-Phase Interactive Buttons */}
          {showPhaseScrubber && (
            <div className="flex items-center space-x-1 overflow-x-auto max-w-full py-0.5">
              {PHASES.map((p) => {
                const isSelected = selectedPhase === p.key && !isPlaying;
                return (
                  <button
                    key={p.key}
                    onClick={() => handlePhaseClick(p.key)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-mono font-bold whitespace-nowrap transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#7FEA35] text-[#050505] shadow-xs'
                        : 'bg-[#181B1D] text-[#A5A9AD] hover:text-white hover:bg-[#303438]'
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          )}

          {/* Auto-Orbit Toggle */}
          {!isReducedMotion && (
            <button
              onClick={() => setAutoOrbit(!autoOrbit)}
              className={`p-1.5 rounded-xl border transition-colors cursor-pointer text-xs ${
                autoOrbit
                  ? 'bg-[#7FEA35]/15 text-[#7FEA35] border-[#7FEA35]/30'
                  : 'bg-[#181B1D] text-[#A5A9AD] border-[#303438] hover:text-white'
              }`}
              title="Auto-orbit camera around the batter"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

