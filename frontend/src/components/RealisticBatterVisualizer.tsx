import React, { useState, useEffect, useRef, useMemo } from 'react';
import referenceShotsData from '../data/reference_shots.json';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Eye,
  Sliders,
  Sparkles,
  Layers,
  ChevronRight,
  ShieldCheck,
  Compass,
  Maximize2
} from 'lucide-react';

export type CameraViewAngle = 'side' | 'front' | 'perspective';

export interface RealisticBatterVisualizerProps {
  shotName: string;
  category?: string;
  handedness?: 'Right' | 'Left';
  cameraView?: CameraViewAngle | string;
  initialPhaseIndex?: number;
  autoPlay?: boolean;
  onPhaseChange?: (phaseIndex: number, phaseName: string) => void;
  className?: string;
  showControls?: boolean;
}

export const PHASES = [
  { name: 'Stance', label: '1. Stance', window: '0% - 15%', cue: 'Balanced ready base, relaxed hands' },
  { name: 'Backlift', label: '2. Backlift', window: '15% - 35%', cue: 'Cock wrists, lift bat toward slips' },
  { name: 'Stride', label: '3. Stride', window: '35% - 50%', cue: 'Decisive footwork establishing base' },
  { name: 'Downswing', label: '4. Downswing', window: '50% - 65%', cue: 'Lead elbow directs pendulum down the line' },
  { name: 'Impact window', label: '5. Impact', window: '65% - 75%', cue: 'Ball contacted under the eye-line' },
  { name: 'Follow-through', label: '6. Follow-through', window: '75% - 90%', cue: 'Deceleration and balanced high finish' },
  { name: 'Recovery', label: '7. Recovery', window: '90% - 100%', cue: 'Re-centering weight to ready position' },
];

/**
 * Biomechanical joint configuration for a keyframe in 2D space.
 * All positions are normalized in [-1, 1] relative to the pelvic center (0, 0).
 */
interface JointPose {
  // Spine & Head
  hipCenter: [number, number];
  chest: [number, number];
  neck: [number, number];
  head: [number, number];
  headAngleDeg: number;
  torsoAngleDeg: number;

  // Arms (Lead / Left for Right-hander)
  leadShoulder: [number, number];
  leadElbow: [number, number];
  leadWrist: [number, number];

  // Arms (Rear / Right for Right-hander)
  rearShoulder: [number, number];
  rearElbow: [number, number];
  rearWrist: [number, number];

  // Bat geometry
  batHandle: [number, number];
  batTip: [number, number];
  batAngleDeg: number;

  // Legs (Lead / Left for Right-hander)
  leadHip: [number, number];
  leadKnee: [number, number];
  leadAnkle: [number, number];
  leadFoot: [number, number];

  // Legs (Rear / Right for Right-hander)
  rearHip: [number, number];
  rearKnee: [number, number];
  rearAnkle: [number, number];
  rearFoot: [number, number];

  // Key measurements for HUD display
  leadKneeAngle: number;
  leadElbowAngle: number;
  torsoLeanAngle: number;
}

const REFERENCE_SHOTS: Record<string, any> = referenceShotsData as any;
const PHASE_KEYS = ['stance', 'backlift', 'stride', 'downswing', 'impact', 'follow_through', 'recovery'];

function findReferenceShot(name: string): any {
  if (!name) return null;
  const n = name.trim().toLowerCase();
  for (const [k, v] of Object.entries(REFERENCE_SHOTS)) {
    if (k.toLowerCase() === n || (v as any)?.slug === n.replace(/\s+/g, '-')) {
      return v;
    }
  }
  for (const [k, v] of Object.entries(REFERENCE_SHOTS)) {
    if (k.toLowerCase().includes(n) || n.includes(k.toLowerCase())) {
      return v;
    }
  }
  return null;
}

/**
 * Generate shot-specific kinematics for each of the 7 phases.
 * Accurately models front-foot drives, back-foot cross-bat shots, sweeps, cuts, and innovative strokes.
 */
function getPoseForShotAndPhase(
  shot: string,
  phaseIndex: number,
  viewAngle: CameraViewAngle,
  handedness: 'Right' | 'Left' = 'Right'
): JointPose {
  const s = (shot || 'Cover Drive').toLowerCase();

  // Normalize progression [0.0 - 1.0] across 7 phases
  const p = Math.max(0, Math.min(6, phaseIndex));

  // Determine shot family
  const isDrive = s.includes('drive');
  const isCoverDrive = s.includes('cover drive');
  const isStraightDrive = s.includes('straight drive');
  const isPullOrHook = s.includes('pull') || s.includes('hook');
  const isCutOrPunch = s.includes('cut') || s.includes('punch');
  const isSweep = s.includes('sweep');
  const isDefensive = s.includes('defensive');
  const isFlick = s.includes('flick') || s.includes('glance') || s.includes('clip');
  const isHelicopter = s.includes('helicopter');
  const isScoop = s.includes('scoop') || s.includes('ramp');

  // Base proportions (meters normalized scale: head height ~0.22, torso ~0.48, legs ~0.85)
  // Default Stance:
  // Pelvis at (0, 0.1), Ground at y = 1.0, Head at y = -0.75
  let hipY = 0.12;
  let hipX = 0.0;
  let torsoLean = 14; // degrees forward
  let headTilt = 5;

  let leadStrideX = 0.25;
  let leadKneeY = 0.55;
  let leadKneeFlex = 162;
  let rearKneeFlex = 160;

  let leadElbowFlex = 100;
  let batAngle = 25; // degrees from vertical
  let batLen = 0.72;

  // Check authoritative reference_shots.json keyframe pose first
  const refShot = findReferenceShot(shot);
  const phaseKey = PHASE_KEYS[p] || 'impact';
  const kf = refShot?.phases?.[phaseKey]?.keyframe_pose;

  if (kf) {
    hipX = kf.hip_x ?? 0.0;
    hipY = kf.hip_y ?? 0.12;
    leadStrideX = kf.lead_stride_x ?? 0.24;
    leadKneeFlex = kf.lead_knee_flex ?? 160;
    rearKneeFlex = kf.rear_knee_flex ?? 155;
    leadElbowFlex = kf.lead_elbow_flex ?? 110;
    batAngle = kf.bat_angle ?? 25;
    torsoLean = kf.torso_lean ?? 15;
  } else if (isSweep) {
    // Sweep shot: deep kneeling base, rear knee dropped to turf
    switch (p) {
      case 0: // Stance
        hipX = 0; hipY = 0.1; leadStrideX = 0.24; leadKneeFlex = 160; rearKneeFlex = 158; batAngle = 20; torsoLean = 15; break;
      case 1: // Backlift
        hipX = -0.05; hipY = 0.08; leadStrideX = 0.22; leadKneeFlex = 162; rearKneeFlex = 155; batAngle = -45; torsoLean = 12; break;
      case 2: // Stride (Front foot lunges forward, body drops)
        hipX = 0.15; hipY = 0.35; leadStrideX = 0.65; leadKneeFlex = 110; rearKneeFlex = 115; batAngle = -30; torsoLean = 28; break;
      case 3: // Downswing (Horizontal sweeping plane)
        hipX = 0.22; hipY = 0.42; leadStrideX = 0.72; leadKneeFlex = 102; rearKneeFlex = 85; batAngle = 45; torsoLean = 34; break;
      case 4: // Impact (Rear knee on canvas turf, horizontal blade roll)
        hipX = 0.25; hipY = 0.46; leadStrideX = 0.75; leadKneeFlex = 98; rearKneeFlex = 75; batAngle = 88; torsoLean = 36; break;
      case 5: // Follow-through (Wrap around shoulder)
        hipX = 0.28; hipY = 0.44; leadStrideX = 0.75; leadKneeFlex = 105; rearKneeFlex = 80; batAngle = 140; torsoLean = 30; break;
      case 6: // Recovery
        hipX = 0.1; hipY = 0.2; leadStrideX = 0.4; leadKneeFlex = 145; rearKneeFlex = 135; batAngle = 40; torsoLean = 20; break;
    }
  } else if (isPullOrHook) {
    // Pull / Hook: back-foot transfer, chest uncoils horizontally, swivel on rear toe
    switch (p) {
      case 0: // Stance
        hipX = 0; hipY = 0.1; leadStrideX = 0.22; leadKneeFlex = 162; rearKneeFlex = 160; batAngle = 20; torsoLean = 14; break;
      case 1: // Backlift (High hands, back towards slip)
        hipX = -0.08; hipY = 0.06; leadStrideX = 0.18; leadKneeFlex = 165; rearKneeFlex = 152; batAngle = -55; torsoLean = 8; break;
      case 2: // Stride (Back and across onto rear foot)
        hipX = -0.15; hipY = 0.08; leadStrideX = -0.05; leadKneeFlex = 155; rearKneeFlex = 142; batAngle = -40; torsoLean = 6; break;
      case 3: // Downswing (Horizontal pull swing at waist/chest)
        hipX = -0.12; hipY = 0.10; leadStrideX = -0.02; leadKneeFlex = 150; rearKneeFlex = 140; batAngle = 40; torsoLean = 8; break;
      case 4: // Impact (Waist-high horizontal strike, weight anchored back)
        hipX = -0.08; hipY = 0.10; leadStrideX = 0.05; leadKneeFlex = 148; rearKneeFlex = 138; batAngle = 92; torsoLean = 10; break;
      case 5: // Follow-through (Full rotational swivel toward square leg)
        hipX = -0.02; hipY = 0.08; leadStrideX = 0.15; leadKneeFlex = 155; rearKneeFlex = 150; batAngle = 165; torsoLean = 12; break;
      case 6: // Recovery
        hipX = 0; hipY = 0.1; leadStrideX = 0.2; leadKneeFlex = 160; rearKneeFlex = 158; batAngle = 30; torsoLean = 14; break;
    }
  } else if (isCutOrPunch) {
    // Square Cut / Back-foot punch: weight back and across, arms flex then slash down through point
    switch (p) {
      case 0: // Stance
        hipX = 0; hipY = 0.1; leadStrideX = 0.22; leadKneeFlex = 162; rearKneeFlex = 160; batAngle = 20; torsoLean = 14; break;
      case 1: // Backlift (High backswing over right shoulder)
        hipX = -0.06; hipY = 0.05; leadStrideX = 0.18; leadKneeFlex = 168; rearKneeFlex = 150; batAngle = -60; torsoLean = 10; break;
      case 2: // Stride (Step back and across towards off stump)
        hipX = -0.16; hipY = 0.09; leadStrideX = 0.02; leadKneeFlex = 165; rearKneeFlex = 136; batAngle = -45; torsoLean = 12; break;
      case 3: // Downswing (Slashing path high to low)
        hipX = -0.12; hipY = 0.12; leadStrideX = 0.05; leadKneeFlex = 162; rearKneeFlex = 138; batAngle = 45; torsoLean = 16; break;
      case 4: // Impact (Extended arms slashing blade outside off stump)
        hipX = -0.08; hipY = 0.13; leadStrideX = 0.08; leadKneeFlex = 160; rearKneeFlex = 140; batAngle = 80; torsoLean = 18; break;
      case 5: // Follow-through (Controlled high finish through point)
        hipX = -0.04; hipY = 0.11; leadStrideX = 0.12; leadKneeFlex = 162; rearKneeFlex = 148; batAngle = 135; torsoLean = 15; break;
      case 6: // Recovery
        hipX = 0; hipY = 0.1; leadStrideX = 0.2; leadKneeFlex = 160; rearKneeFlex = 158; batAngle = 30; torsoLean = 14; break;
    }
  } else if (isDefensive) {
    // Forward / Back-foot Defensive: soft hands, compact stride, bat and pad pressed tight
    switch (p) {
      case 0: // Stance
        hipX = 0; hipY = 0.1; leadStrideX = 0.22; leadKneeFlex = 162; rearKneeFlex = 160; batAngle = 20; torsoLean = 14; break;
      case 1: // Backlift (Controlled, modest lift toward slips)
        hipX = -0.04; hipY = 0.08; leadStrideX = 0.2; leadKneeFlex = 164; rearKneeFlex = 156; batAngle = -35; torsoLean = 12; break;
      case 2: // Stride (Compact front foot stride to pitch of ball)
        hipX = 0.12; hipY = 0.18; leadStrideX = 0.48; leadKneeFlex = 136; rearKneeFlex = 155; batAngle = -20; torsoLean = 22; break;
      case 3: // Downswing (Downwards soft hands pendulum)
        hipX = 0.18; hipY = 0.22; leadStrideX = 0.52; leadKneeFlex = 130; rearKneeFlex = 154; batAngle = 10; torsoLean = 25; break;
      case 4: // Impact (Angled down to turf under eyes, lead knee ~128°)
        hipX = 0.22; hipY = 0.24; leadStrideX = 0.54; leadKneeFlex = 126; rearKneeFlex = 152; batAngle = 18; torsoLean = 26; break;
      case 5: // Follow-through (No check swing, deadened finish)
        hipX = 0.22; hipY = 0.24; leadStrideX = 0.54; leadKneeFlex = 126; rearKneeFlex = 152; batAngle = 22; torsoLean = 26; break;
      case 6: // Recovery
        hipX = 0.08; hipY = 0.14; leadStrideX = 0.32; leadKneeFlex = 150; rearKneeFlex = 156; batAngle = 25; torsoLean = 16; break;
    }
  } else {
    // Default Front-Foot Drives (Cover Drive, Straight Drive, On Drive, Lofted Drive)
    switch (p) {
      case 0: // Stance
        hipX = 0; hipY = 0.1; leadStrideX = 0.24; leadKneeFlex = 164; rearKneeFlex = 160; batAngle = 22; torsoLean = 15; break;
      case 1: // Backlift (Smooth lift towards slips, shoulders coil)
        hipX = -0.05; hipY = 0.07; leadStrideX = 0.20; leadKneeFlex = 166; rearKneeFlex = 155; batAngle = -50; torsoLean = 12; break;
      case 2: // Stride (Dynamic forward step, head leads movement)
        hipX = 0.16; hipY = 0.22; leadStrideX = 0.62; leadKneeFlex = 138; rearKneeFlex = 158; batAngle = -28; torsoLean = 22; break;
      case 3: // Downswing (High leading elbow directs vertical pendulum)
        hipX = 0.24; hipY = 0.26; leadStrideX = 0.68; leadKneeFlex = 126; rearKneeFlex = 156; batAngle = 8; torsoLean = 25; break;
      case 4: // Impact (Textbook drive: knee flexed to 120°-124°, head directly over contact)
        hipX = 0.28; hipY = 0.28; leadStrideX = 0.72; leadKneeFlex = 122; rearKneeFlex = 154; batAngle = 24; torsoLean = 27; break;
      case 5: // Follow-through (High elbow finish through cover/mid-off)
        hipX = 0.30; hipY = 0.25; leadStrideX = 0.72; leadKneeFlex = 126; rearKneeFlex = 156; batAngle = (isStraightDrive ? 120 : (isCoverDrive ? 115 : 125)); torsoLean = 22; break;
      case 6: // Recovery
        hipX = 0.12; hipY = 0.15; leadStrideX = 0.38; leadKneeFlex = 152; rearKneeFlex = 158; batAngle = 35; torsoLean = 16; break;
    }
  }

  // Handle Left-Handed Mirroring
  if (handedness === 'Left') {
    hipX = -hipX;
    leadStrideX = -leadStrideX;
    batAngle = -batAngle;
  }

  // Adjust for View Angle (perspective projection shifts)
  let projX = hipX;
  if (viewAngle === 'front') {
    // In front view, stride is forward toward camera, width is lateral
    projX = hipX * 0.3;
  } else if (viewAngle === 'perspective') {
    projX = hipX * 0.85;
  }

  // Construct Skeleton Nodes in Normalized Canvas Coordinates
  const hipCenter: [number, number] = [projX, hipY];
  const chest: [number, number] = [
    projX + Math.sin((torsoLean * Math.PI) / 180) * 0.32,
    hipY - Math.cos((torsoLean * Math.PI) / 180) * 0.32
  ];
  const neck: [number, number] = [
    chest[0] + Math.sin((torsoLean * Math.PI) / 180) * 0.14,
    chest[1] - Math.cos((torsoLean * Math.PI) / 180) * 0.14
  ];
  const head: [number, number] = [
    neck[0] + Math.sin(((torsoLean + headTilt) * Math.PI) / 180) * 0.16,
    neck[1] - Math.cos(((torsoLean + headTilt) * Math.PI) / 180) * 0.16
  ];

  // Shoulders
  const shoulderSpan = viewAngle === 'front' ? 0.24 : 0.14;
  const leadShoulder: [number, number] = [neck[0] + shoulderSpan * 0.5, neck[1] + 0.04];
  const rearShoulder: [number, number] = [neck[0] - shoulderSpan * 0.5, neck[1] + 0.04];

  // Lead Arm & Elbow
  let leadElbow: [number, number];
  let leadWrist: [number, number];
  let rearElbow: [number, number];
  let rearWrist: [number, number];

  if (p <= 1) {
    // Stance & Backlift: Hands near back hip / waist
    leadElbow = [leadShoulder[0] + 0.06, leadShoulder[1] + 0.20];
    leadWrist = [leadShoulder[0] - 0.02, leadShoulder[1] + 0.36];
    rearElbow = [rearShoulder[0] - 0.10, rearShoulder[1] + 0.18];
    rearWrist = [leadWrist[0] - 0.04, leadWrist[1] + 0.02];
  } else if (p <= 3) {
    // Stride & Downswing
    leadElbow = [leadShoulder[0] + 0.15, leadShoulder[1] + 0.16];
    leadWrist = [leadShoulder[0] + 0.10, leadShoulder[1] + 0.38];
    rearElbow = [rearShoulder[0] - 0.05, rearShoulder[1] + 0.24];
    rearWrist = [leadWrist[0] - 0.04, leadWrist[1] + 0.02];
  } else if (p === 4) {
    // Impact Window: Dominant high lead elbow
    leadElbow = [leadShoulder[0] + 0.22, leadShoulder[1] + 0.12];
    leadWrist = [leadShoulder[0] + 0.18, leadShoulder[1] + 0.38];
    rearElbow = [rearShoulder[0] + 0.04, rearShoulder[1] + 0.22];
    rearWrist = [leadWrist[0] - 0.04, leadWrist[1] + 0.02];
  } else {
    // Follow-through & Finish: Arms elevated through the stroke
    const ftHeight = p === 5 ? -0.15 : 0.05;
    leadElbow = [leadShoulder[0] + 0.28, leadShoulder[1] + ftHeight];
    leadWrist = [leadShoulder[0] + 0.22, leadShoulder[1] + ftHeight - 0.12];
    rearElbow = [rearShoulder[0] + 0.15, rearShoulder[1] + ftHeight + 0.08];
    rearWrist = [leadWrist[0] - 0.04, leadWrist[1] + 0.04];
  }

  // Bat Orientation anchored to wrists
  const batHandle: [number, number] = [(leadWrist[0] + rearWrist[0]) / 2, (leadWrist[1] + rearWrist[1]) / 2];
  const batRad = (batAngle * Math.PI) / 180;
  const batTip: [number, number] = [
    batHandle[0] + Math.sin(batRad) * batLen,
    batHandle[1] + Math.cos(batRad) * batLen
  ];

  // Pelvis & Legs
  const hipSpan = viewAngle === 'front' ? 0.18 : 0.10;
  const leadHip: [number, number] = [hipCenter[0] + hipSpan * 0.5, hipCenter[1]];
  const rearHip: [number, number] = [hipCenter[0] - hipSpan * 0.5, hipCenter[1]];

  // Front Foot Stride
  const footY = 0.95; // Turf ground level
  const leadFoot: [number, number] = [projX + leadStrideX, footY];
  const rearFoot: [number, number] = [projX - 0.25, footY];

  // Knee IK calculation
  const leadKneeX = (leadHip[0] + leadFoot[0]) / 2 + 0.08;
  const leadKnee: [number, number] = [leadKneeX, (leadHip[1] + footY) / 2 + 0.06];

  const rearKneeX = (rearHip[0] + rearFoot[0]) / 2 - 0.04;
  const rearKnee: [number, number] = [rearKneeX, (rearHip[1] + footY) / 2 + 0.04];

  const leadAnkle: [number, number] = [leadFoot[0], footY - 0.08];
  const rearAnkle: [number, number] = [rearFoot[0], footY - 0.08];

  return {
    hipCenter,
    chest,
    neck,
    head,
    headAngleDeg: headTilt,
    torsoAngleDeg: torsoLean,
    leadShoulder,
    leadElbow,
    leadWrist,
    rearShoulder,
    rearElbow,
    rearWrist,
    batHandle,
    batTip,
    batAngleDeg: batAngle,
    leadHip,
    leadKnee,
    leadAnkle,
    leadFoot,
    rearHip,
    rearKnee,
    rearAnkle,
    rearFoot,
    leadKneeAngle: Math.round(leadKneeFlex),
    leadElbowAngle: Math.round(leadElbowFlex),
    torsoLeanAngle: Math.round(torsoLean),
  };
}

export const RealisticBatterVisualizer: React.FC<RealisticBatterVisualizerProps> = ({
  shotName,
  category = 'Drives',
  handedness = 'Right',
  cameraView: cameraViewProp,
  initialPhaseIndex = 4,
  autoPlay = false,
  onPhaseChange,
  className = '',
  showControls = true,
}) => {
  const [activePhaseIndex, setActivePhaseIndex] = useState<number>(initialPhaseIndex);
  const [isPlaying, setIsPlaying] = useState<boolean>(autoPlay);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);

  const initialView: CameraViewAngle = cameraViewProp
    ? (cameraViewProp.toLowerCase().includes('front') ? 'front' : (cameraViewProp.toLowerCase().includes('persp') || cameraViewProp.toLowerCase().includes('oblique') ? 'perspective' : 'side'))
    : 'side';

  const [cameraView, setCameraView] = useState<CameraViewAngle>(initialView);
  const [subFrameProgress, setSubFrameProgress] = useState<number>(0); // 0.0 to 1.0 within phase

  useEffect(() => {
    if (cameraViewProp) {
      const v: CameraViewAngle = cameraViewProp.toLowerCase().includes('front')
        ? 'front'
        : (cameraViewProp.toLowerCase().includes('persp') || cameraViewProp.toLowerCase().includes('oblique') ? 'perspective' : 'side');
      setCameraView(v);
    }
  }, [cameraViewProp]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const lastTickTimeRef = useRef<number>(performance.now());

  // Sync external initialPhaseIndex if changed
  useEffect(() => {
    if (initialPhaseIndex !== undefined && initialPhaseIndex >= 0 && initialPhaseIndex < PHASES.length) {
      setActivePhaseIndex(initialPhaseIndex);
      setSubFrameProgress(0);
    }
  }, [initialPhaseIndex]);

  // Notify parent on phase change
  useEffect(() => {
    if (onPhaseChange) {
      onPhaseChange(activePhaseIndex, PHASES[activePhaseIndex].name);
    }
  }, [activePhaseIndex, onPhaseChange]);

  // Current interpolated pose
  const currentPose = useMemo(() => {
    const p1 = getPoseForShotAndPhase(shotName, activePhaseIndex, cameraView, handedness);
    const nextIdx = (activePhaseIndex + 1) % PHASES.length;
    const p2 = getPoseForShotAndPhase(shotName, nextIdx, cameraView, handedness);

    // Smooth linear interpolation between phase keyframes
    const t = subFrameProgress;
    const lerp = (a: number, b: number) => a + (b - a) * t;
    const lerpPt = (ptA: [number, number], ptB: [number, number]): [number, number] => [
      lerp(ptA[0], ptB[0]),
      lerp(ptA[1], ptB[1]),
    ];

    return {
      hipCenter: lerpPt(p1.hipCenter, p2.hipCenter),
      chest: lerpPt(p1.chest, p2.chest),
      neck: lerpPt(p1.neck, p2.neck),
      head: lerpPt(p1.head, p2.head),
      headAngleDeg: lerp(p1.headAngleDeg, p2.headAngleDeg),
      torsoAngleDeg: lerp(p1.torsoAngleDeg, p2.torsoAngleDeg),
      leadShoulder: lerpPt(p1.leadShoulder, p2.leadShoulder),
      leadElbow: lerpPt(p1.leadElbow, p2.leadElbow),
      leadWrist: lerpPt(p1.leadWrist, p2.leadWrist),
      rearShoulder: lerpPt(p1.rearShoulder, p2.rearShoulder),
      rearElbow: lerpPt(p1.rearElbow, p2.rearElbow),
      rearWrist: lerpPt(p1.rearWrist, p2.rearWrist),
      batHandle: lerpPt(p1.batHandle, p2.batHandle),
      batTip: lerpPt(p1.batTip, p2.batTip),
      batAngleDeg: lerp(p1.batAngleDeg, p2.batAngleDeg),
      leadHip: lerpPt(p1.leadHip, p2.leadHip),
      leadKnee: lerpPt(p1.leadKnee, p2.leadKnee),
      leadAnkle: lerpPt(p1.leadAnkle, p2.leadAnkle),
      leadFoot: lerpPt(p1.leadFoot, p2.leadFoot),
      rearHip: lerpPt(p1.rearHip, p2.rearHip),
      rearKnee: lerpPt(p1.rearKnee, p2.rearKnee),
      rearAnkle: lerpPt(p1.rearAnkle, p2.rearAnkle),
      rearFoot: lerpPt(p1.rearFoot, p2.rearFoot),
      leadKneeAngle: Math.round(lerp(p1.leadKneeAngle, p2.leadKneeAngle)),
      leadElbowAngle: Math.round(lerp(p1.leadElbowAngle, p2.leadElbowAngle)),
      torsoLeanAngle: Math.round(lerp(p1.torsoLeanAngle, p2.torsoLeanAngle)),
    };
  }, [shotName, activePhaseIndex, subFrameProgress, cameraView]);

  // Main animation tick loop
  useEffect(() => {
    const loop = (now: number) => {
      if (isPlaying) {
        const deltaSec = (now - lastTickTimeRef.current) / 1000;
        const phaseDuration = 0.45 / Math.max(0.2, playbackSpeed);

        setSubFrameProgress((prev) => {
          const next = prev + deltaSec / phaseDuration;
          if (next >= 1.0) {
            setActivePhaseIndex((cur) => (cur + 1) % PHASES.length);
            return 0.0;
          }
          return next;
        });
      }
      lastTickTimeRef.current = now;
      animFrameIdRef.current = requestAnimationFrame(loop);
    };

    lastTickTimeRef.current = performance.now();
    animFrameIdRef.current = requestAnimationFrame(loop);

    return () => {
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
    };
  }, [isPlaying, playbackSpeed]);

  // Render Anatomical Realistic Cricket Batter onto HTML5 Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high-DPI displays
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // Screen coordinate transformer: maps normalized [-1, 1] to canvas pixels
    const originX = w * 0.45;
    const originY = h * 0.52;
    const scale = Math.min(w, h) * 0.52;

    const toX = (x: number) => originX + x * scale;
    const toY = (y: number) => originY + y * scale;

    // 1. Draw Professional Cricket Pitch & Crease Background
    drawCricketPitch(ctx, w, h, toY(0.95));

    // 2. Draw Stumps & Bails behind the batter
    drawStumps(ctx, toX(-0.55), toY(0.95), scale * 0.38);

    // 3. Render Human Anatomical Batter Components
    // Layering order: Rear Arm -> Rear Leg -> Torso / Jersey -> Lead Leg (Pads) -> Head / Helmet -> Lead Arm -> Cricket Bat
    const pose = currentPose;

    // --- REAR LEG (Pants + Foot) ---
    drawLimbSegment(ctx, toX(pose.rearHip[0]), toY(pose.rearHip[1]), toX(pose.rearKnee[0]), toY(pose.rearKnee[1]), 22, '#E2E8F0', '#CBD5E1');
    drawCricketPad(ctx, toX(pose.rearKnee[0]), toY(pose.rearKnee[1]), toX(pose.rearAnkle[0]), toY(pose.rearAnkle[1]), 20, false);
    drawSpikesShoe(ctx, toX(pose.rearAnkle[0]), toY(pose.rearAnkle[1]), toX(pose.rearFoot[0]), toY(pose.rearFoot[1]), false);

    // --- REAR ARM ---
    drawLimbSegment(ctx, toX(pose.rearShoulder[0]), toY(pose.rearShoulder[1]), toX(pose.rearElbow[0]), toY(pose.rearElbow[1]), 16, '#0284C7', '#0369A1'); // Blue cricket jersey sleeve
    drawLimbSegment(ctx, toX(pose.rearElbow[0]), toY(pose.rearElbow[1]), toX(pose.rearWrist[0]), toY(pose.rearWrist[1]), 14, '#E0B298', '#C6947D'); // Skin tone forearm
    drawBattingGlove(ctx, toX(pose.rearWrist[0]), toY(pose.rearWrist[1]), 12);

    // --- TORSO & ATHLETIC CRICKET JERSEY ---
    drawCricketJersey(
      ctx,
      toX(pose.rearShoulder[0]), toY(pose.rearShoulder[1]),
      toX(pose.leadShoulder[0]), toY(pose.leadShoulder[1]),
      toX(pose.hipCenter[0]), toY(pose.hipCenter[1]),
      toX(pose.chest[0]), toY(pose.chest[1]),
      pose.torsoAngleDeg
    );

    // --- LEAD LEG (Front Legging Guard / Batting Pad) ---
    drawLimbSegment(ctx, toX(pose.leadHip[0]), toY(pose.leadHip[1]), toX(pose.leadKnee[0]), toY(pose.leadKnee[1]), 24, '#F8FAFC', '#E2E8F0');
    drawCricketPad(ctx, toX(pose.leadKnee[0]), toY(pose.leadKnee[1]), toX(pose.leadAnkle[0]), toY(pose.leadAnkle[1]), 24, true);
    drawSpikesShoe(ctx, toX(pose.leadAnkle[0]), toY(pose.leadAnkle[1]), toX(pose.leadFoot[0]), toY(pose.leadFoot[1]), true);

    // --- HEAD, NECK & CRICKET HELMET WITH VISOR GRILL ---
    drawNeck(ctx, toX(pose.chest[0]), toY(pose.chest[1]), toX(pose.neck[0]), toY(pose.neck[1]), 16);
    drawCricketHelmet(ctx, toX(pose.head[0]), toY(pose.head[1]), 22, pose.headAngleDeg);

    // --- LEAD ARM (Front Driving Arm) ---
    drawLimbSegment(ctx, toX(pose.leadShoulder[0]), toY(pose.leadShoulder[1]), toX(pose.leadElbow[0]), toY(pose.leadElbow[1]), 18, '#0284C7', '#0369A1'); // Royal Blue jersey
    drawLimbSegment(ctx, toX(pose.leadElbow[0]), toY(pose.leadElbow[1]), toX(pose.leadWrist[0]), toY(pose.leadWrist[1]), 15, '#E0B298', '#C6947D'); // Athletic forearm
    drawBattingGlove(ctx, toX(pose.leadWrist[0]), toY(pose.leadWrist[1]), 14);

    // --- REALISTIC ENGLISH WILLOW CRICKET BAT ---
    drawCricketBat(
      ctx,
      toX(pose.batHandle[0]), toY(pose.batHandle[1]),
      toX(pose.batTip[0]), toY(pose.batTip[1]),
      pose.batAngleDeg
    );

    // --- BIOMECHANICAL ANGLE ARC OVERLAYS ---
    drawAngleArc(ctx, toX(pose.leadHip[0]), toY(pose.leadHip[1]), toX(pose.leadKnee[0]), toY(pose.leadKnee[1]), toX(pose.leadAnkle[0]), toY(pose.leadAnkle[1]), `${pose.leadKneeAngle}°`, '#7FEA35');

    ctx.restore();
  }, [currentPose]);

  // Helper: Draw Cricket Pitch, Turf & Crease Markings
  const drawCricketPitch = (ctx: CanvasRenderingContext2D, w: number, h: number, groundY: number) => {
    // Turf gradient
    const turfGrad = ctx.createLinearGradient(0, groundY, 0, h);
    turfGrad.addColorStop(0, '#1E293B');
    turfGrad.addColorStop(0.15, '#0F172A');
    turfGrad.addColorStop(1, '#020617');
    ctx.fillStyle = turfGrad;
    ctx.fillRect(0, groundY, w, h - groundY);

    // White Popping Crease Line
    ctx.beginPath();
    ctx.moveTo(w * 0.1, groundY);
    ctx.lineTo(w * 0.9, groundY);
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Crease Return Marks
    ctx.strokeStyle = '#94A3B8';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(w * 0.35, groundY - 8);
    ctx.lineTo(w * 0.35, groundY + 8);
    ctx.moveTo(w * 0.65, groundY - 8);
    ctx.lineTo(w * 0.65, groundY + 8);
    ctx.stroke();

    // Subtle Pitch Lighting Vignette
    const vignette = ctx.createRadialGradient(w * 0.5, groundY * 0.7, 50, w * 0.5, groundY * 0.7, w * 0.6);
    vignette.addColorStop(0, 'rgba(127, 234, 53, 0.05)');
    vignette.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, w, groundY);
  };

  // Helper: Draw Wickets / Stumps
  const drawStumps = (ctx: CanvasRenderingContext2D, baseX: number, baseY: number, stumpH: number) => {
    ctx.fillStyle = '#D97706'; // Polished timber
    const stumpW = 4;
    const gap = 9;

    for (let i = 0; i < 3; i++) {
      const x = baseX + i * gap;
      ctx.beginPath();
      ctx.roundRect(x, baseY - stumpH, stumpW, stumpH, 2);
      ctx.fill();
    }
    // Bails on top
    ctx.fillStyle = '#F59E0B';
    ctx.fillRect(baseX - 2, baseY - stumpH - 3, gap * 2 + stumpW + 4, 3);
  };

  // Helper: Draw Smooth Muscle Limb Segment
  const drawLimbSegment = (
    ctx: CanvasRenderingContext2D,
    x1: number, y1: number,
    x2: number, y2: number,
    thickness: number,
    colorTop: string,
    colorBottom: string
  ) => {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const perp = angle + Math.PI / 2;
    const r = thickness / 2;

    const grad = ctx.createLinearGradient(x1, y1, x2, y2);
    grad.addColorStop(0, colorTop);
    grad.addColorStop(1, colorBottom);

    ctx.beginPath();
    ctx.moveTo(x1 + Math.cos(perp) * r, y1 + Math.sin(perp) * r);
    ctx.lineTo(x2 + Math.cos(perp) * (r * 0.85), y2 + Math.sin(perp) * (r * 0.85));
    ctx.arc(x2, y2, r * 0.85, perp, perp + Math.PI);
    ctx.lineTo(x1 - Math.cos(perp) * r, y1 - Math.sin(perp) * r);
    ctx.arc(x1, y1, r, perp + Math.PI, perp);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.3)';
    ctx.lineWidth = 1;
    ctx.stroke();
  };

  // Helper: Draw Cricket Batting Pad (Legguard) with authentic knee roll & vertical bolsters
  const drawCricketPad = (
    ctx: CanvasRenderingContext2D,
    kneeX: number, kneeY: number,
    ankleX: number, ankleY: number,
    width: number,
    isLead: boolean
  ) => {
    const angle = Math.atan2(ankleY - kneeY, ankleX - kneeX);
    const dist = Math.hypot(ankleX - kneeX, ankleY - kneeY);

    ctx.save();
    ctx.translate(kneeX, kneeY);
    ctx.rotate(angle);

    // Main Pad Cushion Body
    const padGrad = ctx.createLinearGradient(0, -width / 2, 0, width / 2);
    padGrad.addColorStop(0, isLead ? '#FFFFFF' : '#E2E8F0');
    padGrad.addColorStop(0.5, isLead ? '#F8FAFC' : '#CBD5E1');
    padGrad.addColorStop(1, '#94A3B8');

    ctx.fillStyle = padGrad;
    ctx.beginPath();
    ctx.roundRect(-width * 0.3, -width * 0.55, dist + width * 0.4, width * 1.1, [10, 6, 6, 10]);
    ctx.fill();

    // Knee Roll (Padded horizontal bolster over patella)
    ctx.fillStyle = '#0F172A';
    ctx.beginPath();
    ctx.roundRect(-4, -width * 0.58, 12, width * 1.16, 3);
    ctx.fill();
    ctx.strokeStyle = '#7FEA35'; // Lime trim
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 3 Vertical Cane Bolsters
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.lineWidth = 2;
    for (let b = -0.3; b <= 0.3; b += 0.3) {
      ctx.beginPath();
      ctx.moveTo(10, b * width);
      ctx.lineTo(dist, b * width);
      ctx.stroke();
    }

    // Instep wing protection
    ctx.fillStyle = '#0284C7';
    ctx.beginPath();
    ctx.roundRect(dist - 5, -width * 0.5, 14, width, 4);
    ctx.fill();

    ctx.restore();
  };

  // Helper: Draw Cricket Batting Helmet with Face-Guard Visor Grill
  const drawCricketHelmet = (ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, tiltDeg: number) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((tiltDeg * Math.PI) / 180);

    // Helmet Shell (Dark Navy Indian National Team Style)
    const shellGrad = ctx.createRadialGradient(-radius * 0.3, -radius * 0.4, 2, 0, 0, radius);
    shellGrad.addColorStop(0, '#1E3A8A');
    shellGrad.addColorStop(0.7, '#0F172A');
    shellGrad.addColorStop(1, '#020617');

    ctx.beginPath();
    ctx.arc(0, 0, radius, Math.PI * 0.95, Math.PI * 2.1);
    ctx.lineTo(radius * 0.6, radius * 0.6);
    ctx.lineTo(-radius * 0.6, radius * 0.6);
    ctx.closePath();
    ctx.fillStyle = shellGrad;
    ctx.fill();
    ctx.strokeStyle = '#38BDF8';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Helmet Peak (Sun Visor)
    ctx.fillStyle = '#0F172A';
    ctx.beginPath();
    ctx.moveTo(radius * 0.4, -radius * 0.2);
    ctx.lineTo(radius * 1.1, radius * 0.1);
    ctx.lineTo(radius * 0.7, radius * 0.25);
    ctx.closePath();
    ctx.fill();

    // Ear Guard Panel
    ctx.fillStyle = '#1E293B';
    ctx.beginPath();
    ctx.arc(-radius * 0.1, radius * 0.2, radius * 0.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#64748B';
    ctx.stroke();

    // Steel Face-Guard Visor Grill (Silver bars)
    ctx.strokeStyle = '#E2E8F0';
    ctx.lineWidth = 2;
    ctx.beginPath();
    // Top bar
    ctx.moveTo(radius * 0.3, radius * 0.1);
    ctx.lineTo(radius * 0.9, radius * 0.3);
    // Middle bar
    ctx.moveTo(radius * 0.2, radius * 0.35);
    ctx.lineTo(radius * 0.85, radius * 0.55);
    // Bottom chin bar
    ctx.moveTo(radius * 0.1, radius * 0.6);
    ctx.lineTo(radius * 0.7, radius * 0.75);
    ctx.stroke();

    // Vertical grill connectors
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(radius * 0.6, radius * 0.2);
    ctx.lineTo(radius * 0.55, radius * 0.7);
    ctx.moveTo(radius * 0.8, radius * 0.28);
    ctx.lineTo(radius * 0.7, radius * 0.75);
    ctx.stroke();

    // Human Eyes / Face contour behind visor
    ctx.fillStyle = '#FBBF24'; // Eye reflection / skin
    ctx.beginPath();
    ctx.arc(radius * 0.45, radius * 0.2, 2.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  };

  // Helper: Draw Cricket Jersey with realistic athletic drape & collars
  const drawCricketJersey = (
    ctx: CanvasRenderingContext2D,
    rsX: number, rsY: number,
    lsX: number, lsY: number,
    hipX: number, hipY: number,
    chestX: number, chestY: number,
    tiltDeg: number
  ) => {
    const jerseyGrad = ctx.createLinearGradient(rsX, rsY, lsX, hipY);
    jerseyGrad.addColorStop(0, '#0284C7'); // Royal Blue team jersey
    jerseyGrad.addColorStop(0.5, '#0369A1');
    jerseyGrad.addColorStop(1, '#0C4A6E');

    ctx.beginPath();
    ctx.moveTo(rsX, rsY);
    ctx.lineTo(lsX, lsY);
    ctx.lineTo(hipX + 16, hipY);
    ctx.lineTo(hipX - 16, hipY);
    ctx.closePath();
    ctx.fillStyle = jerseyGrad;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Athletic Gold / Lime Side Trim Panels
    ctx.strokeStyle = '#7FEA35';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(lsX, lsY);
    ctx.lineTo(hipX + 16, hipY);
    ctx.stroke();

    // Collar
    ctx.fillStyle = '#F8FAFC';
    ctx.beginPath();
    ctx.moveTo((rsX + lsX) / 2 - 8, (rsY + lsY) / 2);
    ctx.lineTo((rsX + lsX) / 2 + 8, (rsY + lsY) / 2);
    ctx.lineTo((rsX + lsX) / 2, (rsY + lsY) / 2 + 8);
    ctx.closePath();
    ctx.fill();
  };

  // Helper: Draw Neck
  const drawNeck = (ctx: CanvasRenderingContext2D, cx: number, cy: number, nx: number, ny: number, width: number) => {
    ctx.strokeStyle = '#E0B298';
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(nx, ny);
    ctx.stroke();
  };

  // Helper: Draw Padded Cricket Batting Glove
  const drawBattingGlove = (ctx: CanvasRenderingContext2D, x: number, y: number, radius: number) => {
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#0F172A';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Sausage finger roll segments
    ctx.fillStyle = '#7FEA35'; // Lime green protection inserts
    ctx.beginPath();
    ctx.roundRect(x - radius * 0.4, y - radius * 0.6, radius * 0.8, radius * 0.4, 2);
    ctx.fill();

    // Wristband
    ctx.fillStyle = '#0284C7';
    ctx.fillRect(x - radius * 0.8, y + radius * 0.3, radius * 1.6, 4);
  };

  // Helper: Draw Spikes Cricket Shoe
  const drawSpikesShoe = (ctx: CanvasRenderingContext2D, ax: number, ay: number, fx: number, fy: number, isLead: boolean) => {
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.roundRect(fx - (isLead ? 12 : 6), fy - 8, 22, 10, [3, 6, 2, 2]);
    ctx.fill();
    ctx.strokeStyle = '#CBD5E1';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Spikes metal plate
    ctx.fillStyle = '#475569';
    ctx.fillRect(fx - (isLead ? 10 : 4), fy + 2, 18, 2);
  };

  // Helper: Draw Realistic English Willow Cricket Bat with Wood Grain & Brand Stickers
  const drawCricketBat = (
    ctx: CanvasRenderingContext2D,
    hx: number, hy: number,
    tx: number, ty: number,
    angleDeg: number
  ) => {
    const dist = Math.hypot(tx - hx, ty - hy);
    const angle = Math.atan2(ty - hy, tx - hx);

    ctx.save();
    ctx.translate(hx, hy);
    ctx.rotate(angle);

    const handleLen = dist * 0.30;
    const bladeLen = dist * 0.70;
    const bladeW = 18;

    // 1. Rubber Chevron Grip Handle (White / Navy spiral)
    const gripGrad = ctx.createLinearGradient(0, -3, 0, 3);
    gripGrad.addColorStop(0, '#FFFFFF');
    gripGrad.addColorStop(0.5, '#E2E8F0');
    gripGrad.addColorStop(1, '#0284C7');

    ctx.fillStyle = gripGrad;
    ctx.beginPath();
    ctx.roundRect(0, -4, handleLen, 8, 3);
    ctx.fill();
    ctx.strokeStyle = '#0F172A';
    ctx.lineWidth = 1;
    ctx.stroke();

    // 2. Bat Shoulder / Neck Transition
    ctx.fillStyle = '#F59E0B';
    ctx.beginPath();
    ctx.moveTo(handleLen, -4);
    ctx.lineTo(handleLen + 8, -bladeW / 2);
    ctx.lineTo(handleLen + 8, bladeW / 2);
    ctx.lineTo(handleLen, 4);
    ctx.closePath();
    ctx.fill();

    // 3. English Willow Blade Body
    const bladeGrad = ctx.createLinearGradient(handleLen, 0, handleLen + bladeLen, 0);
    bladeGrad.addColorStop(0, '#FDE68A'); // Natural golden English willow
    bladeGrad.addColorStop(0.7, '#FCD34D');
    bladeGrad.addColorStop(1, '#F59E0B');

    ctx.fillStyle = bladeGrad;
    ctx.beginPath();
    ctx.roundRect(handleLen + 8, -bladeW / 2, bladeLen - 12, bladeW, [0, 4, 4, 0]);
    ctx.fill();
    ctx.strokeStyle = '#B45309';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 4. Willow Grain Lines (Natural wood grain lines running along face)
    ctx.strokeStyle = 'rgba(180, 83, 9, 0.25)';
    ctx.lineWidth = 1;
    for (let g = -5; g <= 5; g += 2.5) {
      ctx.beginPath();
      ctx.moveTo(handleLen + 10, g);
      ctx.lineTo(handleLen + bladeLen - 14, g);
      ctx.stroke();
    }

    // 5. Brand Sponsor Sticker (Red / Hologram Bar across sweet spot)
    ctx.fillStyle = '#DC2626'; // Red sponsor crest
    ctx.fillRect(handleLen + 18, -bladeW / 2 + 2, 28, bladeW - 4);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 7px sans-serif';
    ctx.fillText('PRO', handleLen + 22, 2.5);

    // 6. Rubber Toe Guard (Protects bottom of blade from turf moisture)
    ctx.fillStyle = '#0F172A';
    ctx.fillRect(handleLen + bladeLen - 6, -bladeW / 2, 4, bladeW);

    ctx.restore();
  };

  // Helper: Draw Joint Angle Arc
  const drawAngleArc = (
    ctx: CanvasRenderingContext2D,
    x1: number, y1: number,
    x2: number, y2: number,
    x3: number, y3: number,
    label: string,
    color: string
  ) => {
    const a1 = Math.atan2(y1 - y2, x1 - x2);
    const a2 = Math.atan2(y3 - y2, x3 - x2);

    ctx.beginPath();
    ctx.arc(x2, y2, 24, a1, a2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Text Label
    ctx.font = 'bold 11px monospace';
    ctx.fillStyle = color;
    ctx.fillText(label, x2 + 18, y2 - 10);
  };

  return (
    <div className={`flex flex-col bg-[#0B0D0F] rounded-2xl border border-[#303438] overflow-hidden shadow-2xl ${className}`}>
      {/* Visualizer Top Bar */}
      <div className="px-4 py-3 bg-[#111315] border-b border-[#303438] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#7FEA35]/15 border border-[#7FEA35]/30 flex items-center justify-center text-[#7FEA35]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-[#F5F5F5]">{shotName}</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#181B1D] text-[#7FEA35] border border-[#303438]">
                {category}
              </span>
            </div>
            <p className="text-[11px] text-[#A5A9AD]">
              Anatomical Biomechanical Visualizer • {PHASES[activePhaseIndex].name}
            </p>
          </div>
        </div>

        {/* View Angle Selector Toggle */}
        <div className="flex items-center space-x-1.5 bg-[#181B1D] p-1 rounded-xl border border-[#303438] text-xs">
          <span className="text-[10px] font-mono text-[#A5A9AD] px-1.5">View:</span>
          {(['side', 'front', 'perspective'] as CameraViewAngle[]).map((v) => (
            <button
              key={v}
              onClick={() => setCameraView(v)}
              className={`px-2.5 py-1 rounded-lg capitalize font-mono text-[11px] transition-all cursor-pointer ${
                cameraView === v
                  ? 'bg-[#7FEA35] text-black font-bold shadow-sm'
                  : 'text-[#A5A9AD] hover:text-[#F5F5F5]'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Main Canvas Canvas Frame */}
      <div className="relative aspect-[16/10] sm:aspect-video w-full bg-[#050505] flex items-center justify-center overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-full object-contain"
        />

        {/* Live Kinematics HUD Overlays */}
        <div className="absolute top-3 left-3 flex flex-col space-y-1.5 pointer-events-none">
          <div className="bg-[#111315]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#303438] text-xs font-mono text-[#F5F5F5] flex items-center space-x-3">
            <div>
              <span className="text-[#A5A9AD] text-[10px]">Lead Knee: </span>
              <strong className="text-[#7FEA35] text-sm">{currentPose.leadKneeAngle}°</strong>
            </div>
            <div className="border-l border-[#303438] pl-3">
              <span className="text-[#A5A9AD] text-[10px]">Torso Lean: </span>
              <strong className="text-[#38BDF8] text-sm">{currentPose.torsoLeanAngle}°</strong>
            </div>
            <div className="border-l border-[#303438] pl-3">
              <span className="text-[#A5A9AD] text-[10px]">Lead Elbow: </span>
              <strong className="text-[#FBBF24] text-sm">{currentPose.leadElbowAngle}°</strong>
            </div>
          </div>
        </div>

        {/* Phase Pill HUD */}
        <div className="absolute top-3 right-3 bg-[#111315]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#303438] text-xs font-mono text-[#F5F5F5] flex items-center space-x-2 pointer-events-none">
          <span className="w-2 h-2 rounded-full bg-[#7FEA35] animate-pulse" />
          <span className="font-bold text-[#7FEA35]">{PHASES[activePhaseIndex].label}</span>
          <span className="text-[10px] text-[#A5A9AD]">({PHASES[activePhaseIndex].window})</span>
        </div>

        {/* Bottom Coaching Cue Pill */}
        <div className="absolute bottom-3 left-3 right-3 bg-[#111315]/90 backdrop-blur-md px-4 py-2 rounded-xl border border-[#303438] text-xs text-[#F5F5F5] flex items-center justify-between pointer-events-none">
          <div className="flex items-center space-x-2 truncate">
            <Compass className="w-4 h-4 text-[#7FEA35] shrink-0" />
            <span className="truncate">
              <strong>Key Mechanical Cue: </strong>
              <span className="text-[#A5A9AD]">{PHASES[activePhaseIndex].cue}</span>
            </span>
          </div>
          <span className="text-[10px] font-mono text-[#7FEA35] shrink-0">
            MCC Biomechanical Target
          </span>
        </div>
      </div>

      {/* Interactive Controls & 7-Phase Timeline Selector */}
      {showControls && (
        <div className="p-4 bg-[#111315] border-t border-[#303438] space-y-3.5">
          {/* 7 Batting Movement Phase Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-1.5">
            {PHASES.map((ph, idx) => {
              const isSelected = activePhaseIndex === idx;
              return (
                <button
                  key={ph.name}
                  onClick={() => {
                    setActivePhaseIndex(idx);
                    setSubFrameProgress(0);
                  }}
                  className={`p-2 rounded-xl text-left border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#7FEA35]/15 border-[#7FEA35] text-[#7FEA35] shadow-sm'
                      : 'bg-[#181B1D] border-[#303438] text-[#A5A9AD] hover:text-[#F5F5F5] hover:bg-[#23272B]'
                  }`}
                >
                  <div className="text-[9px] font-mono uppercase text-[#A5A9AD]">{ph.window}</div>
                  <div className={`text-xs font-bold truncate ${isSelected ? 'text-[#7FEA35]' : 'text-[#F5F5F5]'}`}>
                    {ph.name}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Player Toolbar: Play, Pause, Speed, Restart */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-[#7FEA35] hover:bg-[#94EE58] text-black font-bold text-xs transition-colors cursor-pointer"
                title={isPlaying ? 'Pause Animation' : 'Play Animation'}
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5 fill-black" /> : <Play className="w-3.5 h-3.5 fill-black" />}
                <span>{isPlaying ? 'Pause' : 'Play'}</span>
              </button>

              <button
                onClick={() => {
                  setActivePhaseIndex(0);
                  setSubFrameProgress(0);
                }}
                className="p-2 rounded-xl bg-[#181B1D] hover:bg-[#23272B] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438] text-xs transition-colors cursor-pointer"
                title="Restart from Stance"
              >
                <RotateCcw className="w-4 h-4" />
              </button>

              <button
                onClick={() => {
                  setActivePhaseIndex((prev) => (prev + 1) % PHASES.length);
                  setSubFrameProgress(0);
                }}
                className="p-2 rounded-xl bg-[#181B1D] hover:bg-[#23272B] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438] text-xs transition-colors cursor-pointer"
                title="Step Next Phase"
              >
                <FastForward className="w-4 h-4" />
              </button>
            </div>

            {/* Playback Speed Selectors */}
            <div className="flex items-center space-x-2">
              <span className="text-[11px] font-mono text-[#A5A9AD]">Tempo:</span>
              {[0.25, 0.5, 0.75, 1.0, 1.5].map((spd) => (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  className={`px-2 py-1 rounded-lg text-[10px] font-mono font-semibold transition-all cursor-pointer ${
                    playbackSpeed === spd
                      ? 'bg-[#7FEA35] text-black'
                      : 'bg-[#181B1D] text-[#A5A9AD] hover:text-[#F5F5F5] border border-[#303438]'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
