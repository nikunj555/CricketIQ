import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { PhaseKeyframe, getShotAnimation } from '../../data/shotAnimations';
import { ShotVariant, varyShotAnimation } from '../../data/shotVariants';

interface BatterSkeleton3DProps {
  shotName?: string;
  variant?: ShotVariant;
  replayToken?: number;
  currentPhaseKey?: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery';
  phaseProgress?: number; // 0 to 1 within the current phase (or overall)
  isPlaying?: boolean;
  playbackSpeed?: number;
  isLeftHanded?: boolean;
  isGhost?: boolean;
  ghostColor?: string;
  highlightJoint?: string | null;
  showTrail?: boolean;
  trailColor?: string;
}

const PHASE_KEYS: Array<'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery'> = [
  'stance',
  'backlift',
  'stride',
  'downswing',
  'impact',
  'follow_through',
  'recovery'
];

// Helper to interpolate between two 3D tuples
function lerp3(a: [number, number, number], b: [number, number, number], t: number, mirrorX = false): [number, number, number] {
  const mx = mirrorX ? -1 : 1;
  return [
    (a[0] + (b[0] - a[0]) * t) * mx,
    a[1] + (b[1] - a[1]) * t,
    a[2] + (b[2] - a[2]) * t
  ];
}

export const BatterSkeleton3D: React.FC<BatterSkeleton3DProps> = ({
  shotName = 'Cover Drive',
  variant,
  replayToken = 0,
  currentPhaseKey,
  isPlaying = true,
  playbackSpeed = 1.0,
  isLeftHanded = false,
  isGhost = false,
  ghostColor = '#00f0ff',
  highlightJoint = null,
  showTrail = true,
  trailColor = '#7fea35'
}) => {
  const animDef = useMemo(() => {
    const base = getShotAnimation(shotName);
    return base && variant ? varyShotAnimation(base, variant) : base;
  }, [shotName, variant]);

  // Internal time accumulator for playback
  const timeRef = useRef(0);
  const trailPointsRef = useRef<THREE.Vector3[]>([]);

  React.useEffect(() => {
    timeRef.current = 0;
    trailPointsRef.current = [];
  }, [replayToken, variant?.id, shotName]);

  // Compute interpolated pose at time t
  const currentPose = useMemo(() => {
    if (!animDef) return null;
    // If specific phase requested and not playing, snap to that phase
    if (currentPhaseKey && !isPlaying) {
      const kf = animDef.phases[currentPhaseKey] || animDef.phases['impact'] || animDef.phases['stance'];
      return { kfA: kf, kfB: kf, factor: 0 };
    }
    return null;
  }, [animDef, currentPhaseKey, isPlaying]);

  // Joint and Bone Meshes references
  const jointRefs = useRef<Record<string, THREE.Mesh | null>>({});
  const boneRefs = useRef<Record<string, THREE.Mesh | null>>({});
  const batRef = useRef<THREE.Group | null>(null);
  const trailLineRef = useRef<THREE.Line | null>(null);

  // Colors
  const boneColor = isGhost ? ghostColor : '#7fea35';
  const emissiveColor = isGhost ? ghostColor : '#7fea35';
  const jointColor = isGhost ? '#ffffff' : '#94ee58';
  const opacity = isGhost ? 0.35 : 0.95;

  useFrame((_, delta) => {
    if (!animDef) return;
    if (isPlaying) {
      timeRef.current += delta * playbackSpeed * 0.9;
    }

    // Determine current phase and next phase based on looped cycle
    const cycleDuration = 3.2; // total cycle in seconds
    const loopT = (timeRef.current % cycleDuration) / cycleDuration; // 0 to 1

    let kfA: PhaseKeyframe;
    let kfB: PhaseKeyframe;
    let blend: number;

    if (currentPose) {
      kfA = currentPose.kfA;
      kfB = currentPose.kfB;
      blend = 0;
    } else {
      // 7 phases mapped across normalized time
      const totalPhases = PHASE_KEYS.length;
      const phaseIndexFloat = loopT * totalPhases;
      const indexA = Math.floor(phaseIndexFloat) % totalPhases;
      const indexB = (indexA + 1) % totalPhases;
      blend = phaseIndexFloat - Math.floor(phaseIndexFloat);
      // Smooth step easing
      blend = blend * blend * (3 - 2 * blend);

      kfA = animDef.phases[PHASE_KEYS[indexA]];
      kfB = animDef.phases[PHASE_KEYS[indexB]];
    }

    if (!kfA || !kfB) return;

    // Interpolate key joints in 3D
    const mirrorX = isLeftHanded;
    const hip = lerp3(kfA.torso.hip, kfB.torso.hip, blend, mirrorX);
    const chest = lerp3(kfA.torso.chest, kfB.torso.chest, blend, mirrorX);
    const head: [number, number, number] = [
      (kfA.head.x + (kfB.head.x - kfA.head.x) * blend) * (mirrorX ? -1 : 1),
      kfA.head.y + (kfB.head.y - kfA.head.y) * blend,
      kfA.head.z + (kfB.head.z - kfA.head.z) * blend
    ];

    // Arms
    const lShoulder = lerp3(kfA.leadArm.shoulderPos, kfB.leadArm.shoulderPos, blend, mirrorX);
    const lElbow = lerp3(kfA.leadArm.elbowPos, kfB.leadArm.elbowPos, blend, mirrorX);
    const lWrist = lerp3(kfA.leadArm.wristPos, kfB.leadArm.wristPos, blend, mirrorX);

    const rShoulder = lerp3(kfA.rearArm.shoulderPos, kfB.rearArm.shoulderPos, blend, mirrorX);
    const rElbow = lerp3(kfA.rearArm.elbowPos, kfB.rearArm.elbowPos, blend, mirrorX);
    const rWrist = lerp3(kfA.rearArm.wristPos, kfB.rearArm.wristPos, blend, mirrorX);

    // Legs
    const lKnee = lerp3(kfA.leadLeg.kneePos, kfB.leadLeg.kneePos, blend, mirrorX);
    const lFoot = lerp3(kfA.leadLeg.footPos, kfB.leadLeg.footPos, blend, mirrorX);

    const rKnee = lerp3(kfA.rearLeg.kneePos, kfB.rearLeg.kneePos, blend, mirrorX);
    const rFoot = lerp3(kfA.rearLeg.footPos, kfB.rearLeg.footPos, blend, mirrorX);

    // Bat
    const batHandle = lerp3(kfA.bat.handlePos, kfB.bat.handlePos, blend, mirrorX);
    const batTip = lerp3(kfA.bat.tipPos, kfB.bat.tipPos, blend, mirrorX);

    // Update joint sphere positions
    const joints: Record<string, [number, number, number]> = {
      hip,
      chest,
      head,
      lShoulder,
      lElbow,
      lWrist,
      rShoulder,
      rElbow,
      rWrist,
      lKnee,
      lFoot,
      rKnee,
      rFoot,
      batTip
    };

    Object.entries(joints).forEach(([name, pos]) => {
      const mesh = jointRefs.current[name];
      if (mesh) {
        mesh.position.set(pos[0], pos[1], pos[2]);
      }
    });

    // Helper to position and orient a cylinder bone between two points
    const updateBone = (boneName: string, p1: [number, number, number], p2: [number, number, number]) => {
      const bone = boneRefs.current[boneName];
      if (!bone) return;

      const v1 = new THREE.Vector3(...p1);
      const v2 = new THREE.Vector3(...p2);
      const mid = new THREE.Vector3().addVectors(v1, v2).multiplyScalar(0.5);
      const dist = v1.distanceTo(v2);

      bone.position.copy(mid);
      bone.scale.set(1, dist, 1);

      // Orient cylinder (default height along Y) toward target
      const dir = new THREE.Vector3().subVectors(v2, v1).normalize();
      const up = new THREE.Vector3(0, 1, 0);
      const quat = new THREE.Quaternion().setFromUnitVectors(up, dir);
      bone.setRotationFromQuaternion(quat);
    };

    // Update bone segments
    updateBone('spine', hip, chest);
    updateBone('neck', chest, head);
    updateBone('lUpperArm', lShoulder, lElbow);
    updateBone('lForearm', lElbow, lWrist);
    updateBone('rUpperArm', rShoulder, rElbow);
    updateBone('rForearm', rElbow, rWrist);
    updateBone('lThigh', hip, lKnee);
    updateBone('lShin', lKnee, lFoot);
    updateBone('rThigh', hip, rKnee);
    updateBone('rShin', rKnee, rFoot);

    // Update Bat model
    if (batRef.current) {
      const vHandle = new THREE.Vector3(...batHandle);
      const vTip = new THREE.Vector3(...batTip);
      const mid = new THREE.Vector3().addVectors(vHandle, vTip).multiplyScalar(0.5);
      const length = vHandle.distanceTo(vTip);

      batRef.current.position.copy(mid);
      // Vector pointing from toe up to handle (toward hands)
      const dir = new THREE.Vector3().subVectors(vHandle, vTip).normalize();
      const up = new THREE.Vector3(0, 1, 0);
      const quat = new THREE.Quaternion().setFromUnitVectors(up, dir);
      batRef.current.setRotationFromQuaternion(quat);
      batRef.current.scale.set(1, length / 0.85, 1);

      // Record bat tip position for luminous trail
      if (showTrail) {
        trailPointsRef.current.push(vTip.clone());
        if (trailPointsRef.current.length > 45) {
          trailPointsRef.current.shift();
        }
        if (trailLineRef.current) {
          const geom = trailLineRef.current.geometry as THREE.BufferGeometry;
          const posArray = new Float32Array(trailPointsRef.current.length * 3);
          trailPointsRef.current.forEach((pt, i) => {
            posArray[i * 3] = pt.x;
            posArray[i * 3 + 1] = pt.y;
            posArray[i * 3 + 2] = pt.z;
          });
          geom.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
          geom.attributes.position.needsUpdate = true;
        }
      }
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* 1. Joint Spheres */}
      {[
        { name: 'head', r: 0.10 },
        { name: 'chest', r: 0.08 },
        { name: 'hip', r: 0.08 },
        { name: 'lShoulder', r: 0.05 },
        { name: 'lElbow', r: 0.045 },
        { name: 'lWrist', r: 0.04 },
        { name: 'rShoulder', r: 0.05 },
        { name: 'rElbow', r: 0.045 },
        { name: 'rWrist', r: 0.04 },
        { name: 'lKnee', r: 0.055 },
        { name: 'lFoot', r: 0.05 },
        { name: 'rKnee', r: 0.055 },
        { name: 'rFoot', r: 0.05 }
      ].map((joint) => {
        const isTargetJoint = highlightJoint && joint.name.toLowerCase().includes(highlightJoint.toLowerCase());
        return (
          <mesh
            key={joint.name}
            ref={(el) => {
              jointRefs.current[joint.name] = el;
            }}
          >
            <sphereGeometry args={[joint.r, 16, 16]} />
            <meshStandardMaterial
              color={isTargetJoint ? '#ff0055' : jointColor}
              emissive={isTargetJoint ? '#ff0055' : emissiveColor}
              emissiveIntensity={isTargetJoint ? 2.5 : isGhost ? 0.4 : 1.2}
              roughness={0.2}
              metalness={0.5}
              transparent={isGhost}
              opacity={opacity}
            />
          </mesh>
        );
      })}

      {/* 2. Bone Capsules */}
      {[
        'spine',
        'neck',
        'lUpperArm',
        'lForearm',
        'rUpperArm',
        'rForearm',
        'lThigh',
        'lShin',
        'rThigh',
        'rShin'
      ].map((boneName) => (
        <mesh
          key={boneName}
          ref={(el) => {
            boneRefs.current[boneName] = el;
          }}
        >
          <cylinderGeometry args={[0.022, 0.022, 1, 12]} />
          <meshStandardMaterial
            color={boneColor}
            emissive={emissiveColor}
            emissiveIntensity={isGhost ? 0.3 : 0.8}
            roughness={0.3}
            metalness={0.6}
            transparent={isGhost}
            opacity={opacity}
          />
        </mesh>
      ))}

      {/* 3. Authentic Cricket Bat Model */}
      <group ref={batRef}>
        {/* Handle */}
        <mesh position={[0, 0.28, 0]}>
          <cylinderGeometry args={[0.016, 0.018, 0.28, 12]} />
          <meshStandardMaterial
            color="#e2e8f0"
            roughness={0.6}
            metalness={0.1}
            transparent={isGhost}
            opacity={opacity}
          />
        </mesh>
        {/* Blade */}
        <mesh position={[0, -0.15, 0]}>
          <boxGeometry args={[0.11, 0.58, 0.038]} />
          <meshStandardMaterial
            color={isGhost ? ghostColor : '#c29b68'}
            emissive={isGhost ? ghostColor : '#7fea35'}
            emissiveIntensity={isGhost ? 0.3 : 0.2}
            roughness={0.4}
            metalness={0.2}
            transparent={isGhost}
            opacity={opacity}
          />
        </mesh>
        {/* Luminous Blade Edge */}
        {!isGhost && (
          <mesh position={[0.055, -0.15, 0]}>
            <boxGeometry args={[0.006, 0.58, 0.04]} />
            <meshStandardMaterial
              color="#7fea35"
              emissive="#7fea35"
              emissiveIntensity={1.8}
            />
          </mesh>
        )}
      </group>

      {/* 4. Luminous Bat Path Ribbon Trail */}
      {showTrail && !isGhost && (
        <line ref={trailLineRef as any}>
          <bufferGeometry />
          <lineBasicMaterial
            color={trailColor}
            linewidth={3}
            transparent
            opacity={0.7}
          />
        </line>
      )}

      {/* 5. Translucent Torso Volume Silhouette */}
      <mesh
        position={[0, 1.12, 0]}
        ref={(el) => {
          jointRefs.current['torsoVolume'] = el;
        }}
      >
        <capsuleGeometry args={[0.12, 0.32, 8, 16]} />
        <meshStandardMaterial
          color={isGhost ? ghostColor : '#7fea35'}
          emissive={isGhost ? ghostColor : '#7fea35'}
          emissiveIntensity={0.15}
          transparent
          opacity={isGhost ? 0.12 : 0.16}
          roughness={0.3}
          metalness={0.2}
        />
      </mesh>
    </group>
  );
};

