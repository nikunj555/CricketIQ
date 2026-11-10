import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Sparkles,
  Compass,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Info
} from 'lucide-react';
import referenceShotsRaw from '../data/reference_shots.json';
import { ShotVariant, varyReferenceShot } from '../data/shotVariants';

export type CameraViewAngle = 'side' | 'front' | 'perspective';

export interface ReferenceKeyframePose {
  hip_x: number;
  hip_y: number;
  lead_stride_x: number;
  lead_stride_dir_deg: number;
  rear_foot_x: number;
  rear_foot_mode: 'planted' | 'drags' | 'back-and-across' | 'kneeling';
  lead_knee_flex: number;
  rear_knee_flex: number;
  lead_elbow_flex: number;
  rear_elbow_flex: number;
  pelvis_rotation_deg: number;
  shoulder_rotation_deg: number;
  head_offset_x: number;
  hands_x: number;
  hands_y: number;
  bat_plane: 'vertical' | 'diagonal' | 'horizontal';
  bat_angle: number;
  bat_tip_x: number;
  bat_tip_y: number;
  wrist_cock_deg: number;
  torso_lean: number;
  shoulder_tilt: number;
  duration_weight: number;
  cue: string;
}

export interface ReferenceShotPhase {
  keyframe_pose: ReferenceKeyframePose;
  [key: string]: any;
}

export interface ReferenceShotDefinition {
  slug: string;
  category: string;
  analysis_status: string;
  source_type: string;
  status_message: string;
  ideal_bat_path?: string;
  coaching_cues?: string[];
  phases: Record<string, ReferenceShotPhase>;
}

const REFERENCE_SHOTS: Record<string, ReferenceShotDefinition> = referenceShotsRaw as unknown as Record<
  string,
  ReferenceShotDefinition
>;

export function findReferenceShot(nameOrId?: string | null): { name: string; data: ReferenceShotDefinition } | null {
  if (!nameOrId) return null;
  const raw = nameOrId.trim();
  const lower = raw.toLowerCase().replace(/[-_]/g, ' ');

  // Exact match
  if (REFERENCE_SHOTS[raw]) {
    return { name: raw, data: REFERENCE_SHOTS[raw] };
  }

  // Exact case-insensitive match or slug match
  for (const [shotName, data] of Object.entries(REFERENCE_SHOTS)) {
    if (
      shotName.toLowerCase() === lower ||
      data.slug === raw.toLowerCase().replace(/[\s_]/g, '-') ||
      data.slug.replace(/-/g, ' ') === lower
    ) {
      return { name: shotName, data };
    }
  }

  // Substring match
  for (const [shotName, data] of Object.entries(REFERENCE_SHOTS)) {
    const sLower = shotName.toLowerCase();
    if (sLower.includes(lower) || lower.includes(sLower)) {
      return { name: shotName, data };
    }
  }

  return null;
}

export interface RealisticBatterVisualizerProps {
  shotId?: string;
  shotName: string;
  variant?: ShotVariant;
  replayToken?: number;
  category?: string;
  handedness?: 'Right' | 'Left';
  cameraView?: CameraViewAngle | string;
  initialPhaseIndex?: number;
  autoPlay?: boolean;
  onPhaseChange?: (phaseIndex: number, phaseName: string) => void;
  className?: string;
  showControls?: boolean;
  debug?: boolean;
}

export const PHASES = [
  { name: 'Stance', key: 'stance', label: '1. Stance', window: '0% - 15%' },
  { name: 'Backlift', key: 'backlift', label: '2. Backlift', window: '15% - 35%' },
  { name: 'Stride', key: 'stride', label: '3. Stride', window: '35% - 50%' },
  { name: 'Downswing', key: 'downswing', label: '4. Downswing', window: '50% - 65%' },
  { name: 'Impact window', key: 'impact', label: '5. Impact', window: '65% - 75%' },
  { name: 'Follow-through', key: 'follow_through', label: '6. Follow-through', window: '75% - 90%' },
  { name: 'Recovery', key: 'recovery', label: '7. Recovery', window: '90% - 100%' },
];

export const PHASE_KEYS = ['stance', 'backlift', 'stride', 'downswing', 'impact', 'follow_through', 'recovery'];

export interface Point2D {
  x: number;
  y: number;
  depth: number;
}

export interface ProjectedPose {
  hipCenter: Point2D;
  chest: Point2D;
  neck: Point2D;
  head: Point2D;
  headAngleDeg: number;
  torsoAngleDeg: number;

  leadShoulder: Point2D;
  leadElbow: Point2D;
  leadWrist: Point2D;

  rearShoulder: Point2D;
  rearElbow: Point2D;
  rearWrist: Point2D;

  leadHip: Point2D;
  leadKnee: Point2D;
  leadAnkle: Point2D;
  leadFoot: Point2D;
  leadKneeling: boolean;

  rearHip: Point2D;
  rearKnee: Point2D;
  rearAnkle: Point2D;
  rearFoot: Point2D;
  rearKneeling: boolean;

  leadKneeAngle: number;
  leadElbowAngle: number;
  torsoLeanAngle: number;

  // Derived Bat Geometry (Grip Constraint Guaranteed)
  topHandGrip: Point2D;
  bottomHandGrip: Point2D;
  buttEnd: Point2D;
  handleEnd: Point2D;
  bladeShoulders: Point2D;
  toe: Point2D;
  batAxis: { x: number; y: number };
  batLength: number;
  bladeFaceDeg: number;
  isHandsSwitched: boolean;
}

/**
 * Biomechanical cricket easing:
 * Accelerates downswing into impact, holds momentarily at impact, decelerates in follow-through.
 */
function getBiomechanicalProgress(phaseIdx: number, rawProgress: number): number {
  const p = Math.max(0, Math.min(1, rawProgress));
  if (phaseIdx === 3) {
    // Downswing: rapid acceleration
    return Math.pow(p, 1.8);
  }
  if (phaseIdx === 4) {
    // Impact window: crisp contact sensation
    return p < 0.25 ? p * 0.5 : 0.125 + (p - 0.25) * (0.875 / 0.75);
  }
  if (phaseIdx === 5) {
    // Follow-through: smooth deceleration
    return 1 - Math.pow(1 - p, 1.9);
  }
  return p * p * (3 - 2 * p);
}

export const RealisticBatterVisualizer: React.FC<RealisticBatterVisualizerProps> = ({
  shotId,
  shotName,
  variant,
  replayToken = 0,
  category = 'Drives',
  handedness: initialHandedness = 'Right',
  cameraView: cameraViewProp,
  initialPhaseIndex = 0,
  autoPlay = true,
  onPhaseChange,
  className = '',
  showControls = true,
  debug: debugProp = false,
}) => {
  // Check debug flag from prop or URL (?debug=1)
  const isDebugUrl = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('debug') === '1';
  const [debugMode, setDebugMode] = useState<boolean>(debugProp || isDebugUrl);

  const resolveView = (v?: string): CameraViewAngle => {
    if (!v) return 'side';
    const s = v.toLowerCase();
    if (s.includes('front') || s === '0') return 'front';
    if (s.includes('persp') || s.includes('oblique') || s.includes('45')) return 'perspective';
    return 'side';
  };

  const [cameraView, setCameraView] = useState<CameraViewAngle>(resolveView(cameraViewProp));
  const [handedness, setHandedness] = useState<'Right' | 'Left'>(initialHandedness);

  const [activePhaseIndex, setActivePhaseIndex] = useState<number>(initialPhaseIndex);
  const [isPlaying, setIsPlaying] = useState<boolean>(autoPlay);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(0.75);
  const [subFrameProgress, setSubFrameProgress] = useState<number>(0);

  // HUD & Display Toggles
  const [showSkeleton, setShowSkeleton] = useState<boolean>(false);
  const [showAngleArcs, setShowAngleArcs] = useState<boolean>(true);
  const [showBatTrail, setShowBatTrail] = useState<boolean>(true);

  // Authoritative reference shot directly from reference_shots.json (NO cover-drive fallback!)
  const refShotInfo = useMemo(() => {
    const found = findReferenceShot(shotId || shotName);
    return found && variant ? { ...found, data: varyReferenceShot(found.data, variant) } : found;
  }, [shotId, shotName, variant]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const lastTickTimeRef = useRef<number>(performance.now());
  const batTrailBufferRef = useRef<Array<{ x: number; y: number; alpha: number }>>([]);

  // RESET on shot, cameraView, or handedness change (NO stale frames)
  useEffect(() => {
    setActivePhaseIndex(0);
    setSubFrameProgress(0);
    batTrailBufferRef.current = [];
    lastTickTimeRef.current = performance.now();
  }, [shotId, shotName, cameraView, handedness, replayToken]);

  useEffect(() => {
    if (cameraViewProp) {
      setCameraView(resolveView(cameraViewProp));
    }
  }, [cameraViewProp]);

  useEffect(() => {
    if (initialHandedness) {
      setHandedness(initialHandedness);
    }
  }, [initialHandedness]);

  // Sync external initialPhaseIndex if explicitly passed
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

  // 3D Forward Kinematics to 2D Screen Coordinate Projection
  const projectPoint3D = (
    pos: [number, number, number],
    view: CameraViewAngle,
    hand: 'Right' | 'Left',
    w: number,
    h: number
  ): Point2D => {
    let [x, y, z] = pos;

    // Left-handed batter: mirror lateral Z-axis
    if (hand === 'Left') {
      z = -z;
    }

    // Camera azimuthal angle around Y axis
    let angleRad = 0;
    if (view === 'front') {
      angleRad = -Math.PI / 2; // -90 deg: bowler perspective down pitch
    } else if (view === 'perspective') {
      angleRad = -45 * (Math.PI / 180); // -45 deg: broadcast 3/4 perspective
    } else {
      // Side view: slight 8° parallax angle so transverse cross-bat shots have visible depth
      angleRad = -8 * (Math.PI / 180);
    }

    const cosA = Math.cos(angleRad);
    const sinA = Math.sin(angleRad);

    const xProj = x * cosA - z * sinA;
    const zDepth = x * sinA + z * cosA;

    // Viewport scaling
    const groundY = h * 0.82;
    const scale = h * 0.42;
    const originX = w * (view === 'front' ? 0.50 : 0.46);

    const screenX = originX + xProj * scale;
    const screenY = groundY - y * scale;

    return {
      x: screenX,
      y: screenY,
      depth: zDepth
    };
  };

  // Compute Current Biomechanical Pose from Keyframe Pose Fields
  const currentKeyframePose = useMemo((): { pose: ProjectedPose; activeKeyframe: ReferenceKeyframePose } | null => {
    if (!refShotInfo || !refShotInfo.data.phases) return null;

    const curPhaseName = PHASE_KEYS[activePhaseIndex] || 'stance';
    const nextPhaseIdx = (activePhaseIndex + 1) % PHASE_KEYS.length;
    const nextPhaseName = PHASE_KEYS[nextPhaseIdx] || 'backlift';

    const p1 = refShotInfo.data.phases[curPhaseName] || refShotInfo.data.phases['stance'];
    const p2 = refShotInfo.data.phases[nextPhaseName] || refShotInfo.data.phases['stance'];
    if (!p1?.keyframe_pose || !p2?.keyframe_pose) return null;

    const kf1 = p1.keyframe_pose;
    const kf2 = p2.keyframe_pose;

    const t = getBiomechanicalProgress(activePhaseIndex, subFrameProgress);
    const lerp = (a: number, b: number) => a + (b - a) * t;

    const hip_x = lerp(kf1.hip_x, kf2.hip_x);
    const hip_y = lerp(kf1.hip_y, kf2.hip_y);
    const lead_stride_x = lerp(kf1.lead_stride_x, kf2.lead_stride_x);
    const lead_stride_dir_deg = lerp(kf1.lead_stride_dir_deg, kf2.lead_stride_dir_deg);
    const rear_foot_x = lerp(kf1.rear_foot_x, kf2.rear_foot_x);
    const lead_knee_flex = lerp(kf1.lead_knee_flex, kf2.lead_knee_flex);
    const rear_knee_flex = lerp(kf1.rear_knee_flex, kf2.rear_knee_flex);
    const lead_elbow_flex = lerp(kf1.lead_elbow_flex, kf2.lead_elbow_flex);
    const rear_elbow_flex = lerp(kf1.rear_elbow_flex, kf2.rear_elbow_flex);
    const pelvis_rotation_deg = lerp(kf1.pelvis_rotation_deg, kf2.pelvis_rotation_deg);
    const shoulder_rotation_deg = lerp(kf1.shoulder_rotation_deg, kf2.shoulder_rotation_deg);
    const head_offset_x = lerp(kf1.head_offset_x, kf2.head_offset_x);
    const hands_x = lerp(kf1.hands_x, kf2.hands_x);
    const hands_y = lerp(kf1.hands_y, kf2.hands_y);
    const bat_angle = lerp(kf1.bat_angle, kf2.bat_angle);
    const bat_tip_x = lerp(kf1.bat_tip_x, kf2.bat_tip_x);
    const bat_tip_y = lerp(kf1.bat_tip_y, kf2.bat_tip_y);
    const torso_lean = lerp(kf1.torso_lean, kf2.torso_lean);
    const shoulder_tilt = lerp(kf1.shoulder_tilt, kf2.shoulder_tilt);

    const rear_foot_mode = t < 0.5 ? kf1.rear_foot_mode : kf2.rear_foot_mode;
    const bat_plane = t < 0.5 ? kf1.bat_plane : kf2.bat_plane;

    const w = canvasRef.current?.clientWidth || 800;
    const h = canvasRef.current?.clientHeight || 500;
    const scale = h * 0.42;

    // 1. Pelvis and Hips in 3D
    const hipCenter3D: [number, number, number] = [hip_x, hip_y, 0];
    const pelvisRad = (pelvis_rotation_deg * Math.PI) / 180;
    const hipW = 0.10;
    const leadHip3D: [number, number, number] = [
      hipCenter3D[0] + hipW * Math.sin(pelvisRad),
      hipCenter3D[1],
      hipCenter3D[2] + hipW * Math.cos(pelvisRad)
    ];
    const rearHip3D: [number, number, number] = [
      hipCenter3D[0] - hipW * Math.sin(pelvisRad),
      hipCenter3D[1],
      hipCenter3D[2] - hipW * Math.cos(pelvisRad)
    ];

    // 2. Lead Leg
    const strideRad = (lead_stride_dir_deg * Math.PI) / 180;
    const leadFoot3D: [number, number, number] = [
      hip_x + lead_stride_x * Math.cos(strideRad),
      0.05,
      lead_stride_x * Math.sin(strideRad)
    ];
    const kneeFlexRad = (lead_knee_flex * Math.PI) / 180;
    const leadKnee3D: [number, number, number] = [
      leadHip3D[0] + (leadFoot3D[0] - leadHip3D[0]) * 0.55 + 0.04 * Math.cos(kneeFlexRad / 2),
      0.05 + 0.44 * Math.sin(kneeFlexRad / 2),
      leadFoot3D[2] * 0.55 + hipW * 0.5
    ];
    const leadAnkle3D: [number, number, number] = [leadFoot3D[0], 0.11, leadFoot3D[2]];

    // 3. Rear Leg
    const isRearKneeling = rear_foot_mode === 'kneeling';
    let rearFoot3D: [number, number, number];
    let rearKnee3D: [number, number, number];

    if (isRearKneeling) {
      rearFoot3D = [rear_foot_x - 0.22, 0.05, -0.12];
      rearKnee3D = [rear_foot_x, 0.07, -0.10];
    } else if (rear_foot_mode === 'drags') {
      rearFoot3D = [rear_foot_x + 0.12, 0.05, -0.12];
      const rKneeRad = (rear_knee_flex * Math.PI) / 180;
      rearKnee3D = [
        rearHip3D[0] + (rearFoot3D[0] - rearHip3D[0]) * 0.48,
        0.05 + 0.44 * Math.sin(rKneeRad / 2),
        -0.12
      ];
    } else {
      rearFoot3D = [rear_foot_x, 0.05, rear_foot_mode === 'back-and-across' ? -0.16 : -0.12];
      const rKneeRad = (rear_knee_flex * Math.PI) / 180;
      rearKnee3D = [
        rearHip3D[0] + (rearFoot3D[0] - rearHip3D[0]) * 0.5,
        0.05 + 0.44 * Math.sin(rKneeRad / 2),
        rearFoot3D[2]
      ];
    }
    const rearAnkle3D: [number, number, number] = [rearFoot3D[0], isRearKneeling ? 0.07 : 0.11, rearFoot3D[2]];

    // 4. Torso, Chest, Neck, Head
    const leanRad = (torso_lean * Math.PI) / 180;
    const tiltRad = (shoulder_tilt * Math.PI) / 180;
    const torsoLen = 0.44;
    const chest3D: [number, number, number] = [
      hipCenter3D[0] + torsoLen * Math.sin(leanRad),
      hipCenter3D[1] + torsoLen * Math.cos(leanRad),
      torsoLen * Math.sin(tiltRad)
    ];
    const neck3D: [number, number, number] = [
      chest3D[0] + 0.09 * Math.sin(leanRad),
      chest3D[1] + 0.09 * Math.cos(leanRad),
      chest3D[2]
    ];
    const head3D: [number, number, number] = [
      neck3D[0] + 0.14 * Math.sin(leanRad) + head_offset_x,
      neck3D[1] + 0.14,
      neck3D[2]
    ];

    // Shoulders
    const shRad = (shoulder_rotation_deg * Math.PI) / 180;
    const shW = 0.19;
    const leadShoulder3D: [number, number, number] = [
      chest3D[0] + shW * Math.sin(shRad),
      chest3D[1] - 0.01,
      chest3D[2] + shW * Math.cos(shRad)
    ];
    const rearShoulder3D: [number, number, number] = [
      chest3D[0] - shW * Math.sin(shRad),
      chest3D[1] + 0.01,
      chest3D[2] - shW * Math.cos(shRad)
    ];

    // 5. Hands and Bat Tip
    let handsZ = chest3D[2] + 0.10 * Math.cos(shRad);
    let tipZ = handsZ + 0.02;
    if (bat_plane === 'horizontal') {
      handsZ = chest3D[2] + 0.18 * Math.cos(shRad);
      tipZ = handsZ + 0.28 * Math.sin((bat_angle * Math.PI) / 180);
    } else if (bat_plane === 'diagonal') {
      handsZ = chest3D[2] + 0.14 * Math.cos(shRad);
      tipZ = handsZ + 0.18 * Math.sin(strideRad);
    }

    const hands3D: [number, number, number] = [hands_x, hands_y, handsZ];
    const batTip3D: [number, number, number] = [bat_tip_x, bat_tip_y, tipZ];

    // Project points to 2D screen
    const p = (pt: [number, number, number]) => projectPoint3D(pt, cameraView, handedness, w, h);

    const leadShoulderP = p(leadShoulder3D);
    const rearShoulderP = p(rearShoulder3D);
    const handsP = p(hands3D);
    const tipP = p(batTip3D);

    // ==========================================
    // STEP 2: THE BAT, DONE CORRECTLY (MATHEMATICAL GRIP CONSTRAINT)
    // ==========================================
    const isReverse = (refShotInfo.data.slug || refShotInfo.name).toLowerCase().includes('reverse');
    const isHandsSwitched = isReverse;

    const batLength = scale * 0.92;
    const dx = tipP.x - handsP.x;
    const dy = tipP.y - handsP.y;
    const handTipDist = Math.hypot(dx, dy);

    let ux: number;
    let uy: number;
    if (handTipDist > 10) {
      ux = dx / handTipDist;
      uy = dy / handTipDist;
    } else {
      const rad = (bat_angle * Math.PI) / 180;
      ux = Math.sin(rad);
      uy = -Math.cos(rad);
    }

    // Butt end sits 5% ABOVE top hand along -u
    const buttEnd: Point2D = {
      x: handsP.x - ux * (batLength * 0.05),
      y: handsP.y - uy * (batLength * 0.05),
      depth: handsP.depth
    };

    // Top Hand grip sits 5% from butt (= handsP)
    const topHandGrip: Point2D = handsP;

    // Bottom Hand grip sits 21% from butt (= 16% from top hand along +u)
    const bottomHandGrip: Point2D = {
      x: handsP.x + ux * (batLength * 0.16),
      y: handsP.y + uy * (batLength * 0.16),
      depth: handsP.depth
    };

    // Handle end sits at 30% of bat length from butt
    const handleEnd: Point2D = {
      x: buttEnd.x + ux * (batLength * 0.30),
      y: buttEnd.y + uy * (batLength * 0.30),
      depth: handsP.depth
    };

    // Blade shoulders sit at 36% of bat length
    const bladeShoulders: Point2D = {
      x: buttEnd.x + ux * (batLength * 0.36),
      y: buttEnd.y + uy * (batLength * 0.36),
      depth: handsP.depth
    };

    // Blade toe sits at 100% of bat length
    const toe: Point2D = {
      x: buttEnd.x + ux * batLength,
      y: buttEnd.y + uy * batLength,
      depth: tipP.depth
    };

    // Map wrists to grip points
    let leadWristP: Point2D;
    let rearWristP: Point2D;
    if (!isHandsSwitched) {
      leadWristP = topHandGrip;
      rearWristP = bottomHandGrip;
    } else {
      leadWristP = bottomHandGrip;
      rearWristP = topHandGrip;
    }

    // Derive elbows from shoulders and wrists using flex angles
    const computeElbow = (sh: Point2D, wr: Point2D, flexDeg: number, isLeadArm: boolean): Point2D => {
      const midX = (sh.x + wr.x) / 2;
      const midY = (sh.y + wr.y) / 2;
      const armLen = Math.hypot(wr.x - sh.x, wr.y - sh.y);
      const perpX = -(wr.y - sh.y) / Math.max(1, armLen);
      const perpY = (wr.x - sh.x) / Math.max(1, armLen);
      const flexOffset = Math.sin((flexDeg * Math.PI) / 360) * (scale * 0.18);
      const sign = isLeadArm ? 1 : -1;
      return {
        x: midX + perpX * flexOffset * sign,
        y: midY + perpY * flexOffset * sign,
        depth: (sh.depth + wr.depth) / 2
      };
    };

    const leadElbowP = computeElbow(leadShoulderP, leadWristP, lead_elbow_flex, true);
    const rearElbowP = computeElbow(rearShoulderP, rearWristP, rear_elbow_flex, false);

    return {
      activeKeyframe: kf1,
      pose: {
        hipCenter: p(hipCenter3D),
        chest: p(chest3D),
        neck: p(neck3D),
        head: p(head3D),
        headAngleDeg: Math.round(torso_lean * 0.4),
        torsoAngleDeg: Math.round(torso_lean),

        leadShoulder: leadShoulderP,
        leadElbow: leadElbowP,
        leadWrist: leadWristP,

        rearShoulder: rearShoulderP,
        rearElbow: rearElbowP,
        rearWrist: rearWristP,

        leadHip: p(leadHip3D),
        leadKnee: p(leadKnee3D),
        leadAnkle: p(leadAnkle3D),
        leadFoot: p(leadFoot3D),
        leadKneeling: false,

        rearHip: p(rearHip3D),
        rearKnee: p(rearKnee3D),
        rearAnkle: p(rearAnkle3D),
        rearFoot: p(rearFoot3D),
        rearKneeling: isRearKneeling,

        leadKneeAngle: Math.round(lead_knee_flex),
        leadElbowAngle: Math.round(lead_elbow_flex),
        torsoLeanAngle: Math.round(torso_lean),

        topHandGrip,
        bottomHandGrip,
        buttEnd,
        handleEnd,
        bladeShoulders,
        toe,
        batAxis: { x: ux, y: uy },
        batLength,
        bladeFaceDeg: Math.round(bat_angle),
        isHandsSwitched
      }
    };
  }, [refShotInfo, activePhaseIndex, subFrameProgress, cameraView, handedness]);

  // Main animation tick loop with duration weights from keyframe_pose
  useEffect(() => {
    if (!refShotInfo) return;

    const loop = (now: number) => {
      if (isPlaying) {
        const deltaSec = Math.min(0.1, (now - lastTickTimeRef.current) / 1000);
        const curKey = PHASE_KEYS[activePhaseIndex] || 'stance';
        const weight = refShotInfo.data.phases[curKey]?.keyframe_pose?.duration_weight || 1.0;
        const phaseDuration = (0.55 * weight) / Math.max(0.2, playbackSpeed);

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
  }, [isPlaying, playbackSpeed, activePhaseIndex, refShotInfo]);

  // Render Anatomical Realistic Cricket Batter onto HTML5 Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !currentKeyframePose) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

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

    const groundY = h * 0.82;

    // 1. Draw Pitch Crease Markings
    drawCricketPitch(ctx, w, h, groundY);

    // 2. Draw Stumps & Bails
    const stumpsOrigin = projectPoint3D([-0.40, 0.0, 0.0], cameraView, handedness, w, h);
    drawStumps(ctx, stumpsOrigin.x, groundY, h * 0.22);

    // 3. Draw Swing Plane Guide Arc & Faint Path Trail
    if (showBatTrail && refShotInfo) {
      drawBatTrailArc(ctx, w, h);
    }

    const { pose } = currentKeyframePose;

    // Add current bat toe to live motion trail buffer
    if (isPlaying) {
      batTrailBufferRef.current.push({ x: pose.toe.x, y: pose.toe.y, alpha: 1.0 });
      if (batTrailBufferRef.current.length > 25) {
        batTrailBufferRef.current.shift();
      }
    }

    // Draw active motion trail behind bat toe
    if (showBatTrail && batTrailBufferRef.current.length > 1) {
      ctx.save();
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      for (let i = 1; i < batTrailBufferRef.current.length; i++) {
        const ptA = batTrailBufferRef.current[i - 1];
        const ptB = batTrailBufferRef.current[i];
        const ratio = i / batTrailBufferRef.current.length;
        ctx.beginPath();
        ctx.moveTo(ptA.x, ptA.y);
        ctx.lineTo(ptB.x, ptB.y);
        ctx.strokeStyle = `rgba(127, 234, 53, ${ratio * 0.75})`;
        ctx.lineWidth = 2 + ratio * 4;
        ctx.stroke();
      }
      ctx.restore();
    }

    // ==========================================
    // LAYERED ANATOMICAL RENDERING
    // ==========================================
    // Rear Leg
    drawLimbSegment(ctx, pose.rearHip.x, pose.rearHip.y, pose.rearKnee.x, pose.rearKnee.y, 22, '#E2E8F0', '#CBD5E1');
    drawCricketPad(ctx, pose.rearKnee.x, pose.rearKnee.y, pose.rearAnkle.x, pose.rearAnkle.y, 20, false, pose.rearKneeling);
    drawSpikesShoe(ctx, pose.rearAnkle.x, pose.rearAnkle.y, pose.rearFoot.x, pose.rearFoot.y, false);

    // Rear Arm
    drawLimbSegment(ctx, pose.rearShoulder.x, pose.rearShoulder.y, pose.rearElbow.x, pose.rearElbow.y, 16, '#0284C7', '#0369A1');
    drawLimbSegment(ctx, pose.rearElbow.x, pose.rearElbow.y, pose.rearWrist.x, pose.rearWrist.y, 14, '#E0B298', '#C6947D');

    // Torso & Jersey
    drawCricketJersey(
      ctx,
      pose.rearShoulder.x, pose.rearShoulder.y,
      pose.leadShoulder.x, pose.leadShoulder.y,
      pose.hipCenter.x, pose.hipCenter.y,
      pose.chest.x, pose.chest.y
    );

    // Lead Leg
    drawLimbSegment(ctx, pose.leadHip.x, pose.leadHip.y, pose.leadKnee.x, pose.leadKnee.y, 24, '#F8FAFC', '#E2E8F0');
    drawCricketPad(ctx, pose.leadKnee.x, pose.leadKnee.y, pose.leadAnkle.x, pose.leadAnkle.y, 24, true, pose.leadKneeling);
    drawSpikesShoe(ctx, pose.leadAnkle.x, pose.leadAnkle.y, pose.leadFoot.x, pose.leadFoot.y, true);

    // Head, Neck & Helmet
    drawNeck(ctx, pose.chest.x, pose.chest.y, pose.neck.x, pose.neck.y, 16);
    drawCricketHelmet(ctx, pose.head.x, pose.head.y, 22, pose.headAngleDeg);

    // Lead Arm
    drawLimbSegment(ctx, pose.leadShoulder.x, pose.leadShoulder.y, pose.leadElbow.x, pose.leadElbow.y, 18, '#0284C7', '#0369A1');
    drawLimbSegment(ctx, pose.leadElbow.x, pose.leadElbow.y, pose.leadWrist.x, pose.leadWrist.y, 15, '#E0B298', '#C6947D');

    // CRICKET BAT & HANDS (Derives correctly: handle held by hands, blade away)
    drawCricketBatAndHands(ctx, pose);

    // 4. Biomechanical Skeleton Overlay
    if (showSkeleton) {
      drawSkeletonOverlay(ctx, pose);
    }

    // 5. Joint Angle Arc Overlays
    if (showAngleArcs) {
      drawAngleArc(ctx, pose.leadHip.x, pose.leadHip.y, pose.leadKnee.x, pose.leadKnee.y, pose.leadAnkle.x, pose.leadAnkle.y, `${pose.leadKneeAngle}°`, '#7FEA35');
      drawAngleArc(ctx, pose.leadShoulder.x, pose.leadShoulder.y, pose.leadElbow.x, pose.leadElbow.y, pose.leadWrist.x, pose.leadWrist.y, `${pose.leadElbowAngle}°`, '#FBBF24');
    }

    // 6. Debug Overlay (?debug=1)
    if (debugMode) {
      drawDebugOverlay(ctx, pose);
    }

    ctx.restore();
  }, [currentKeyframePose, showSkeleton, showAngleArcs, showBatTrail, isPlaying, debugMode, refShotInfo]);

  // Draw authentic cricket bat and grip gloves
  const drawCricketBatAndHands = (ctx: CanvasRenderingContext2D, pose: ProjectedPose) => {
    const { buttEnd, handleEnd, bladeShoulders, toe, topHandGrip, bottomHandGrip, batAxis, batLength } = pose;
    const perp = { x: -batAxis.y, y: batAxis.x };

    ctx.save();

    // 1. BAT HANDLE (From buttEnd to handleEnd)
    const handleW = 7;
    ctx.beginPath();
    ctx.moveTo(buttEnd.x - perp.x * (handleW / 2), buttEnd.y - perp.y * (handleW / 2));
    ctx.lineTo(handleEnd.x - perp.x * (handleW / 2), handleEnd.y - perp.y * (handleW / 2));
    ctx.lineTo(handleEnd.x + perp.x * (handleW / 2), handleEnd.y + perp.y * (handleW / 2));
    ctx.lineTo(buttEnd.x + perp.x * (handleW / 2), buttEnd.y + perp.y * (handleW / 2));
    ctx.closePath();

    const handleGrad = ctx.createLinearGradient(buttEnd.x, buttEnd.y, handleEnd.x, handleEnd.y);
    handleGrad.addColorStop(0, '#FFFFFF');
    handleGrad.addColorStop(0.5, '#E2E8F0');
    handleGrad.addColorStop(1, '#0284C7');
    ctx.fillStyle = handleGrad;
    ctx.fill();
    ctx.strokeStyle = '#0F172A';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Rubber Butt Cap
    ctx.beginPath();
    ctx.arc(buttEnd.x, buttEnd.y, handleW * 0.65, 0, Math.PI * 2);
    ctx.fillStyle = '#0F172A';
    ctx.fill();

    // 2. WILLOW BLADE (From handleEnd to toe)
    const bladeW = 19;
    const toeW = 17;

    ctx.beginPath();
    // Start at left handle-shoulder joint
    ctx.moveTo(handleEnd.x - perp.x * (handleW / 2), handleEnd.y - perp.y * (handleW / 2));
    // Flare out to left blade shoulder
    ctx.quadraticCurveTo(
      bladeShoulders.x - perp.x * (bladeW * 0.8), bladeShoulders.y - perp.y * (bladeW * 0.8),
      bladeShoulders.x - perp.x * (bladeW / 2), bladeShoulders.y - perp.y * (bladeW / 2)
    );
    // Down to left toe corner
    ctx.lineTo(toe.x - perp.x * (toeW / 2), toe.y - perp.y * (toeW / 2));
    // Rounded bottom toe
    ctx.quadraticCurveTo(
      toe.x, toe.y + 4,
      toe.x + perp.x * (toeW / 2), toe.y + perp.y * (toeW / 2)
    );
    // Up to right blade shoulder
    ctx.lineTo(bladeShoulders.x + perp.x * (bladeW / 2), bladeShoulders.y + perp.y * (bladeW / 2));
    // In to right handle-shoulder joint
    ctx.quadraticCurveTo(
      bladeShoulders.x + perp.x * (bladeW * 0.8), bladeShoulders.y + perp.y * (bladeW * 0.8),
      handleEnd.x + perp.x * (handleW / 2), handleEnd.y + perp.y * (handleW / 2)
    );
    ctx.closePath();

    const bladeGrad = ctx.createLinearGradient(handleEnd.x, handleEnd.y, toe.x, toe.y);
    bladeGrad.addColorStop(0, '#FDE68A');
    bladeGrad.addColorStop(0.3, '#FCD34D');
    bladeGrad.addColorStop(0.85, '#F59E0B');
    bladeGrad.addColorStop(1, '#D97706');
    ctx.fillStyle = bladeGrad;
    ctx.fill();
    ctx.strokeStyle = '#B45309';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Central Willow Spine Ridge
    ctx.beginPath();
    ctx.moveTo(handleEnd.x, handleEnd.y);
    ctx.lineTo(toe.x, toe.y);
    ctx.strokeStyle = 'rgba(180, 83, 9, 0.35)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Red Sponsor Sticker on upper blade face
    const stickerStart = {
      x: handleEnd.x + batAxis.x * (batLength * 0.08),
      y: handleEnd.y + batAxis.y * (batLength * 0.08)
    };
    ctx.fillStyle = '#DC2626';
    ctx.beginPath();
    ctx.rect(stickerStart.x - perp.x * 7, stickerStart.y - perp.y * 7, 24, 12);
    ctx.fill();

    // 3. BATTING GLOVES HUGGING HANDLE ONLY (Top Hand & Bottom Hand)
    drawBattingGlove(ctx, topHandGrip.x, topHandGrip.y, 13, '#FFFFFF', '#7FEA35');
    drawBattingGlove(ctx, bottomHandGrip.x, bottomHandGrip.y, 12, '#FFFFFF', '#0284C7');

    ctx.restore();
  };

  // Helper: Draw Batting Glove
  const drawBattingGlove = (
    ctx: CanvasRenderingContext2D,
    x: number, y: number,
    radius: number,
    fillColor: string,
    accentColor: string
  ) => {
    ctx.fillStyle = fillColor;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#0F172A';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Padding Roll Accent
    ctx.fillStyle = accentColor;
    ctx.beginPath();
    ctx.roundRect(x - radius * 0.5, y - radius * 0.6, radius, radius * 0.45, 2);
    ctx.fill();
  };

  // Helper: Draw Full Swing Plane Guide Arc (from Backlift to Follow-through)
  const drawBatTrailArc = (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    if (!refShotInfo || !refShotInfo.data.phases) return;
    ctx.save();
    ctx.beginPath();
    let first = true;
    const SWING_KEYS = ['backlift', 'stride', 'downswing', 'impact', 'follow_through'];
    for (const pk of SWING_KEYS) {
      const pData = refShotInfo.data.phases[pk];
      if (!pData?.keyframe_pose) continue;
      const kf = pData.keyframe_pose;
      const pt = projectPoint3D([kf.bat_tip_x, kf.bat_tip_y, 0.05], cameraView, handedness, w, h);
      if (first) {
        ctx.moveTo(pt.x, pt.y);
        first = false;
      } else {
        ctx.lineTo(pt.x, pt.y);
      }
    }
    ctx.strokeStyle = 'rgba(127, 234, 53, 0.45)';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 4]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  };

  // Helper: Draw Debug Overlay (?debug=1)
  const drawDebugOverlay = (ctx: CanvasRenderingContext2D, p: ProjectedPose) => {
    ctx.save();

    // Bat Axis Arrow
    ctx.beginPath();
    ctx.moveTo(p.buttEnd.x, p.buttEnd.y);
    ctx.lineTo(p.toe.x, p.toe.y);
    ctx.strokeStyle = '#00F0FF';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Handle / Blade Boundary Joint
    const perp = { x: -p.batAxis.y, y: p.batAxis.x };
    ctx.beginPath();
    ctx.moveTo(p.handleEnd.x - perp.x * 15, p.handleEnd.y - perp.y * 15);
    ctx.lineTo(p.handleEnd.x + perp.x * 15, p.handleEnd.y + perp.y * 15);
    ctx.strokeStyle = '#EC4899';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Butt end marker
    ctx.beginPath();
    ctx.arc(p.buttEnd.x, p.buttEnd.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#EF4444';
    ctx.fill();
    ctx.font = 'bold 9px monospace';
    ctx.fillText('BUTT (0%)', p.buttEnd.x + 8, p.buttEnd.y);

    // Handle end marker
    ctx.fillStyle = '#EC4899';
    ctx.fillText('HANDLE END (30%)', p.handleEnd.x + 12, p.handleEnd.y);

    // Top Hand Grip Point
    ctx.beginPath();
    ctx.arc(p.topHandGrip.x, p.topHandGrip.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#7FEA35';
    ctx.fill();
    ctx.fillText(`TOP HAND (${p.isHandsSwitched ? 'REAR' : 'LEAD'})`, p.topHandGrip.x + 8, p.topHandGrip.y - 6);

    // Bottom Hand Grip Point
    ctx.beginPath();
    ctx.arc(p.bottomHandGrip.x, p.bottomHandGrip.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#F59E0B';
    ctx.fill();
    ctx.fillText(`BOTTOM HAND (${p.isHandsSwitched ? 'LEAD' : 'REAR'})`, p.bottomHandGrip.x + 8, p.bottomHandGrip.y + 12);

    // Toe Marker
    ctx.beginPath();
    ctx.arc(p.toe.x, p.toe.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#10B981';
    ctx.fill();
    ctx.fillText('TOE (100%)', p.toe.x + 8, p.toe.y + 4);

    // Distance verification readout
    const distToButt = Math.hypot(p.topHandGrip.x - p.buttEnd.x, p.topHandGrip.y - p.buttEnd.y);
    const distToToe = Math.hypot(p.topHandGrip.x - p.toe.x, p.topHandGrip.y - p.toe.y);

    ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
    ctx.fillRect(10, 10, 240, 68);
    ctx.strokeStyle = '#00F0FF';
    ctx.lineWidth = 1;
    ctx.strokeRect(10, 10, 240, 68);

    ctx.fillStyle = '#00F0FF';
    ctx.font = 'bold 10px monospace';
    ctx.fillText('DEBUG: GRIP GEOMETRY VERIFIED', 16, 26);
    ctx.fillStyle = '#7FEA35';
    ctx.fillText(`Dist(TopHand -> Butt): ${distToButt.toFixed(1)}px`, 16, 42);
    ctx.fillStyle = '#F59E0B';
    ctx.fillText(`Dist(TopHand -> Toe) : ${distToToe.toFixed(1)}px`, 16, 56);
    ctx.fillStyle = distToButt < distToToe ? '#7FEA35' : '#EF4444';
    ctx.fillText(`Status: ${distToButt < distToToe ? 'PASS (Hands on Handle)' : 'FAIL'}`, 16, 70);

    ctx.restore();
  };

  // Helper: Draw Biomechanical Skeleton
  const drawSkeletonOverlay = (ctx: CanvasRenderingContext2D, p: ProjectedPose) => {
    ctx.save();
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#38BDF8';

    const drawBone = (p1: Point2D, p2: Point2D) => {
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    };

    const drawJoint = (pt: Point2D, name: string) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#7FEA35';
      ctx.fill();
      ctx.strokeStyle = '#050505';
      ctx.lineWidth = 1;
      ctx.stroke();

      if (debugMode) {
        ctx.font = '8px monospace';
        ctx.fillStyle = '#A5A9AD';
        ctx.fillText(name, pt.x + 6, pt.y - 4);
      }
    };

    drawBone(p.head, p.neck);
    drawBone(p.neck, p.chest);
    drawBone(p.chest, p.hipCenter);

    drawBone(p.chest, p.leadShoulder);
    drawBone(p.leadShoulder, p.leadElbow);
    drawBone(p.leadElbow, p.leadWrist);

    drawBone(p.chest, p.rearShoulder);
    drawBone(p.rearShoulder, p.rearElbow);
    drawBone(p.rearElbow, p.rearWrist);

    drawBone(p.hipCenter, p.leadHip);
    drawBone(p.leadHip, p.leadKnee);
    drawBone(p.leadKnee, p.leadAnkle);
    drawBone(p.leadAnkle, p.leadFoot);

    drawBone(p.hipCenter, p.rearHip);
    drawBone(p.rearHip, p.rearKnee);
    drawBone(p.rearKnee, p.rearAnkle);
    drawBone(p.rearAnkle, p.rearFoot);

    drawJoint(p.head, 'Head');
    drawJoint(p.neck, 'Neck');
    drawJoint(p.chest, 'Chest');
    drawJoint(p.hipCenter, 'Hip');
    drawJoint(p.leadShoulder, 'LSh');
    drawJoint(p.leadElbow, 'LEl');
    drawJoint(p.leadWrist, 'LWr');
    drawJoint(p.rearShoulder, 'RSh');
    drawJoint(p.rearElbow, 'REl');
    drawJoint(p.rearWrist, 'RWr');
    drawJoint(p.leadHip, 'LHp');
    drawJoint(p.leadKnee, 'LKn');
    drawJoint(p.leadAnkle, 'LAnk');
    drawJoint(p.leadFoot, 'LFt');
    drawJoint(p.rearHip, 'RHp');
    drawJoint(p.rearKnee, 'RKn');
    drawJoint(p.rearAnkle, 'RAnk');
    drawJoint(p.rearFoot, 'RFt');

    ctx.restore();
  };

  // Helper: Draw Cricket Pitch & Crease Markings
  const drawCricketPitch = (ctx: CanvasRenderingContext2D, w: number, h: number, groundY: number) => {
    const turfGrad = ctx.createLinearGradient(0, groundY, 0, h);
    turfGrad.addColorStop(0, '#1E293B');
    turfGrad.addColorStop(0.15, '#0F172A');
    turfGrad.addColorStop(1, '#020617');
    ctx.fillStyle = turfGrad;
    ctx.fillRect(0, groundY, w, h - groundY);

    // Popping Crease Line
    ctx.beginPath();
    ctx.moveTo(w * 0.08, groundY);
    ctx.lineTo(w * 0.92, groundY);
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Crease Return Marks
    ctx.strokeStyle = '#94A3B8';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(w * 0.32, groundY - 8);
    ctx.lineTo(w * 0.32, groundY + 8);
    ctx.moveTo(w * 0.68, groundY - 8);
    ctx.lineTo(w * 0.68, groundY + 8);
    ctx.stroke();
  };

  // Helper: Draw Stumps
  const drawStumps = (ctx: CanvasRenderingContext2D, baseX: number, baseY: number, stumpH: number) => {
    ctx.fillStyle = '#D97706';
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

  // Helper: Draw Batting Pad
  const drawCricketPad = (
    ctx: CanvasRenderingContext2D,
    kneeX: number, kneeY: number,
    ankleX: number, ankleY: number,
    width: number,
    isLead: boolean,
    isKneeling: boolean = false
  ) => {
    const angle = Math.atan2(ankleY - kneeY, ankleX - kneeX);
    const dist = Math.hypot(ankleX - kneeX, ankleY - kneeY);

    ctx.save();
    ctx.translate(kneeX, kneeY);
    ctx.rotate(angle);

    const padGrad = ctx.createLinearGradient(0, -width / 2, 0, width / 2);
    padGrad.addColorStop(0, isLead ? '#FFFFFF' : '#E2E8F0');
    padGrad.addColorStop(0.5, isLead ? '#F8FAFC' : '#CBD5E1');
    padGrad.addColorStop(1, '#94A3B8');

    ctx.fillStyle = padGrad;
    ctx.beginPath();
    ctx.roundRect(-width * 0.3, -width * 0.55, dist + width * 0.4, width * 1.1, [10, 6, 6, 10]);
    ctx.fill();

    // Knee Roll
    ctx.fillStyle = isKneeling ? '#EF4444' : '#0F172A';
    ctx.beginPath();
    ctx.roundRect(-4, -width * 0.58, 12, width * 1.16, 3);
    ctx.fill();
    ctx.strokeStyle = '#7FEA35';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.restore();
  };

  // Helper: Draw Cricket Helmet with Visor Grill
  const drawCricketHelmet = (ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, tiltDeg: number) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((tiltDeg * Math.PI) / 180);

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

    // Helmet Peak
    ctx.fillStyle = '#0F172A';
    ctx.beginPath();
    ctx.moveTo(radius * 0.4, -radius * 0.2);
    ctx.lineTo(radius * 1.1, radius * 0.1);
    ctx.lineTo(radius * 0.7, radius * 0.25);
    ctx.closePath();
    ctx.fill();

    // Visor Grill
    ctx.strokeStyle = '#E2E8F0';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(radius * 0.3, radius * 0.1);
    ctx.lineTo(radius * 0.9, radius * 0.3);
    ctx.moveTo(radius * 0.2, radius * 0.35);
    ctx.lineTo(radius * 0.85, radius * 0.55);
    ctx.moveTo(radius * 0.1, radius * 0.6);
    ctx.lineTo(radius * 0.7, radius * 0.75);
    ctx.stroke();

    ctx.restore();
  };

  // Helper: Draw Cricket Jersey
  const drawCricketJersey = (
    ctx: CanvasRenderingContext2D,
    rsX: number, rsY: number,
    lsX: number, lsY: number,
    hipX: number, hipY: number,
    chestX: number, chestY: number
  ) => {
    const jerseyGrad = ctx.createLinearGradient(rsX, rsY, lsX, hipY);
    jerseyGrad.addColorStop(0, '#0284C7');
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

    // Side Trim Panels
    ctx.strokeStyle = '#7FEA35';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(lsX, lsY);
    ctx.lineTo(hipX + 16, hipY);
    ctx.stroke();
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

  // Helper: Draw Spikes Cricket Shoe
  const drawSpikesShoe = (ctx: CanvasRenderingContext2D, ax: number, ay: number, fx: number, fy: number, isLead: boolean) => {
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.roundRect(fx - (isLead ? 12 : 6), fy - 8, 22, 10, [3, 6, 2, 2]);
    ctx.fill();
    ctx.strokeStyle = '#CBD5E1';
    ctx.lineWidth = 1;
    ctx.stroke();
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

    ctx.font = 'bold 11px monospace';
    ctx.fillStyle = color;
    ctx.fillText(label, x2 + 18, y2 - 10);
  };

  // ==========================================
  // STEP 1: PREVIEW COMING SOON STATE (NEVER FALL BACK TO COVER DRIVE)
  // ==========================================
  if (!refShotInfo) {
    return (
      <div className={`flex flex-col items-center justify-center p-8 bg-[#0B0D0F] rounded-2xl border border-[#303438] min-h-[380px] text-center space-y-4 ${className}`}>
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div className="space-y-1.5 max-w-md">
          <h3 className="text-base font-bold text-[#F5F5F5]">Biomechanical Preview Coming Soon</h3>
          <p className="text-xs text-[#A5A9AD]">
            No verified keyframe trajectory currently authored for <strong className="text-[#F5F5F5]">"{shotName}"</strong>.
            CricketIQ displays authentic kinematics only and refuses generic fallbacks.
          </p>
        </div>
      </div>
    );
  }

  const activeKeyframe = currentKeyframePose?.activeKeyframe;
  const pose = currentKeyframePose?.pose;

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
              <h3 className="text-sm font-bold text-[#F5F5F5]">{refShotInfo.name}</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#181B1D] text-[#7FEA35] border border-[#303438]">
                {refShotInfo.data.category}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#181B1D] text-[#38BDF8] border border-[#303438]">
                {handedness}-handed
              </span>
            </div>
            <p className="text-[11px] text-[#A5A9AD]">
              3D Forward Kinematics • {PHASES[activePhaseIndex].name} • Plane: {activeKeyframe?.bat_plane || 'standard'}
            </p>
          </div>
        </div>

        {/* View Angle, Handedness & Debug Toggles */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Handedness Toggle */}
          <button
            onClick={() => setHandedness(handedness === 'Right' ? 'Left' : 'Right')}
            className="px-2.5 py-1 rounded-xl bg-[#181B1D] border border-[#303438] text-[11px] font-mono font-bold text-[#38BDF8] hover:text-white transition-all cursor-pointer"
            title="Toggle Right / Left Handed Batter"
          >
            {handedness === 'Right' ? 'RHB' : 'LHB (Mirrored)'}
          </button>

          {/* Camera View Angle Selector */}
          <div className="flex items-center space-x-1 bg-[#181B1D] p-1 rounded-xl border border-[#303438] text-xs">
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
                {v === 'side' ? 'Side (90°)' : v === 'front' ? 'Front (0°)' : '45°'}
              </button>
            ))}
          </div>

          {/* HUD Toggles */}
          <div className="flex items-center space-x-1 bg-[#181B1D] p-1 rounded-xl border border-[#303438]">
            <button
              onClick={() => setShowSkeleton(!showSkeleton)}
              className={`px-2 py-1 rounded-lg text-[10px] font-mono transition-all cursor-pointer ${
                showSkeleton ? 'bg-[#38BDF8] text-black font-bold' : 'text-[#A5A9AD] hover:text-[#F5F5F5]'
              }`}
            >
              Skeleton
            </button>
            <button
              onClick={() => setShowAngleArcs(!showAngleArcs)}
              className={`px-2 py-1 rounded-lg text-[10px] font-mono transition-all cursor-pointer ${
                showAngleArcs ? 'bg-[#7FEA35] text-black font-bold' : 'text-[#A5A9AD] hover:text-[#F5F5F5]'
              }`}
            >
              Angles
            </button>
            <button
              onClick={() => setShowBatTrail(!showBatTrail)}
              className={`px-2 py-1 rounded-lg text-[10px] font-mono transition-all cursor-pointer ${
                showBatTrail ? 'bg-[#7FEA35] text-black font-bold' : 'text-[#A5A9AD] hover:text-[#F5F5F5]'
              }`}
            >
              Trail
            </button>
            <button
              onClick={() => setDebugMode(!debugMode)}
              className={`px-2 py-1 rounded-lg text-[10px] font-mono transition-all cursor-pointer ${
                debugMode ? 'bg-[#EC4899] text-white font-bold' : 'text-[#A5A9AD] hover:text-[#F5F5F5]'
              }`}
            >
              Debug
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas Frame */}
      <div className="relative aspect-[16/10] sm:aspect-video w-full bg-[#050505] flex items-center justify-center overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-full object-contain"
        />

        {/* Live Kinematics HUD Overlays */}
        {pose && (
          <div className="absolute top-3 left-3 flex flex-col space-y-1.5 pointer-events-none">
            <div className="bg-[#111315]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#303438] text-xs font-mono text-[#F5F5F5] flex items-center space-x-3">
              <div>
                <span className="text-[#A5A9AD] text-[10px]">Lead Knee: </span>
                <strong className="text-[#7FEA35] text-sm">{pose.leadKneeAngle}°</strong>
              </div>
              <div className="border-l border-[#303438] pl-3">
                <span className="text-[#A5A9AD] text-[10px]">Torso Lean: </span>
                <strong className="text-[#38BDF8] text-sm">{pose.torsoLeanAngle}°</strong>
              </div>
              <div className="border-l border-[#303438] pl-3">
                <span className="text-[#A5A9AD] text-[10px]">Lead Elbow: </span>
                <strong className="text-[#FBBF24] text-sm">{pose.leadElbowAngle}°</strong>
              </div>
            </div>
          </div>
        )}

        {/* Phase Pill HUD */}
        <div className="absolute top-3 right-3 bg-[#111315]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#303438] text-xs font-mono text-[#F5F5F5] flex items-center space-x-2 pointer-events-none">
          <span className="w-2 h-2 rounded-full bg-[#7FEA35] animate-pulse" />
          <span className="font-bold text-[#7FEA35]">{PHASES[activePhaseIndex].label}</span>
          <span className="text-[10px] text-[#A5A9AD]">({PHASES[activePhaseIndex].window})</span>
        </div>

        {/* Bottom Technical Cue Pill (Reads directly from keyframe_pose.cue) */}
        <div className="absolute bottom-3 left-3 right-3 bg-[#111315]/90 backdrop-blur-md px-4 py-2 rounded-xl border border-[#303438] text-xs text-[#F5F5F5] flex items-center justify-between pointer-events-none">
          <div className="flex items-center space-x-2 truncate">
            <Compass className="w-4 h-4 text-[#7FEA35] shrink-0" />
            <span className="truncate">
              <strong>Key Mechanical Cue: </strong>
              <span className="text-[#A5A9AD]">{activeKeyframe?.cue || 'Maintain athletic balance and eyes level'}</span>
            </span>
          </div>
          <span className="text-[10px] font-mono text-[#7FEA35] shrink-0">
            Authored Baseline (Tunable)
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

export function getPoseForShotAndPhase(
  shotType: string,
  phaseIndex: number = 4,
  view: string = 'side',
  handedness: string = 'Right'
) {
  const refShotInfo = findReferenceShot(shotType);
  if (!refShotInfo || !refShotInfo.data.phases) return null;

  const phaseKey = PHASE_KEYS[Math.min(Math.max(0, phaseIndex), PHASE_KEYS.length - 1)];
  const phaseData =
    refShotInfo.data.phases[phaseKey] ||
    refShotInfo.data.phases['impact'] ||
    refShotInfo.data.phases['stance'];
  if (!phaseData || !phaseData.keyframe_pose) return null;

  const kf = phaseData.keyframe_pose;
  const isLeftHanded = handedness.toLowerCase() === 'left';
  const mirror = isLeftHanded ? -1 : 1;
  const rad = view === 'front' ? 0 : view === '45' ? (45 * Math.PI) / 180 : (90 * Math.PI) / 180;
  const cosA = Math.cos(rad);
  const sinA = Math.sin(rad);

  const proj = (pt: [number, number, number]): [number, number] => {
    const mx = pt[0] * mirror;
    const my = pt[1];
    const mz = pt[2];
    const xProj = mx * cosA - mz * sinA;
    const yProj = -my;
    return [xProj, yProj];
  };

  const hip3D: [number, number, number] = [kf.hip_x, kf.hip_y, 0];
  const torsoLen = 0.44;
  const leanRad = (kf.torso_lean * Math.PI) / 180;
  const chest3D: [number, number, number] = [
    hip3D[0] + torsoLen * Math.sin(leanRad),
    hip3D[1] + torsoLen * Math.cos(leanRad),
    0
  ];
  const neck3D: [number, number, number] = [
    chest3D[0] + 0.09 * Math.sin(leanRad),
    chest3D[1] + 0.09 * Math.cos(leanRad),
    0
  ];
  const head3D: [number, number, number] = [
    neck3D[0] + 0.14 * Math.sin(leanRad) + kf.head_offset_x,
    neck3D[1] + 0.14,
    0
  ];

  const shW = 0.19;
  const shRad = (kf.shoulder_rotation_deg * Math.PI) / 180;
  const leadShoulder3D: [number, number, number] = [
    chest3D[0] + shW * Math.sin(shRad),
    chest3D[1] - 0.01,
    shW * Math.cos(shRad)
  ];
  const rearShoulder3D: [number, number, number] = [
    chest3D[0] - shW * Math.sin(shRad),
    chest3D[1] + 0.01,
    -shW * Math.cos(shRad)
  ];

  const hipW = 0.10;
  const pRad = (kf.pelvis_rotation_deg * Math.PI) / 180;
  const leadHip3D: [number, number, number] = [
    hip3D[0] + hipW * Math.sin(pRad),
    hip3D[1],
    hipW * Math.cos(pRad)
  ];
  const rearHip3D: [number, number, number] = [
    hip3D[0] - hipW * Math.sin(pRad),
    hip3D[1],
    -hipW * Math.cos(pRad)
  ];

  const strideRad = (kf.lead_stride_dir_deg * Math.PI) / 180;
  const leadFoot3D: [number, number, number] = [
    kf.hip_x + kf.lead_stride_x * Math.cos(strideRad),
    0.05,
    kf.lead_stride_x * Math.sin(strideRad)
  ];
  const kneeFlexRad = (kf.lead_knee_flex * Math.PI) / 180;
  const leadKnee3D: [number, number, number] = [
    leadHip3D[0] + (leadFoot3D[0] - leadHip3D[0]) * 0.55 + 0.04 * Math.cos(kneeFlexRad / 2),
    0.05 + 0.44 * Math.sin(kneeFlexRad / 2),
    leadFoot3D[2] * 0.55
  ];
  const leadAnkle3D: [number, number, number] = [leadFoot3D[0], 0.11, leadFoot3D[2]];

  const rearFoot3D: [number, number, number] = [kf.rear_foot_x, 0.05, -0.12];
  const rearKneeRad = (kf.rear_knee_flex * Math.PI) / 180;
  const rearKnee3D: [number, number, number] = [
    rearHip3D[0] + (rearFoot3D[0] - rearHip3D[0]) * 0.5,
    0.05 + 0.44 * Math.sin(rearKneeRad / 2),
    -0.12
  ];
  const rearAnkle3D: [number, number, number] = [rearFoot3D[0], 0.11, -0.12];

  const hands3D: [number, number, number] = [kf.hands_x, kf.hands_y, 0.10];
  const batTip3D: [number, number, number] = [kf.bat_tip_x, kf.bat_tip_y, 0.12];

  return {
    head: proj(head3D),
    neck: proj(neck3D),
    chest: proj(chest3D),
    leadShoulder: proj(leadShoulder3D),
    leadElbow: proj([
      (leadShoulder3D[0] + hands3D[0]) / 2 + 0.05,
      (leadShoulder3D[1] + hands3D[1]) / 2 - 0.05,
      leadShoulder3D[2]
    ]),
    leadWrist: proj(hands3D),
    rearShoulder: proj(rearShoulder3D),
    rearElbow: proj([
      (rearShoulder3D[0] + hands3D[0]) / 2 - 0.05,
      (rearShoulder3D[1] + hands3D[1]) / 2 - 0.05,
      rearShoulder3D[2]
    ]),
    rearWrist: proj([hands3D[0] + 0.05, hands3D[1] - 0.05, hands3D[2]]),
    leadHip: proj(leadHip3D),
    leadKnee: proj(leadKnee3D),
    leadAnkle: proj(leadAnkle3D),
    rearHip: proj(rearHip3D),
    rearKnee: proj(rearKnee3D),
    rearAnkle: proj(rearAnkle3D),
    batHandle: proj(hands3D),
    batTip: proj(batTip3D),
  };
}
