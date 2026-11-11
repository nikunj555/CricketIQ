import React from 'react';
import * as THREE from 'three';

export const PitchEnvironment3D: React.FC = () => {
  return (
    <group position={[0, 0, 0]}>
      {/* Turf Pitch Surface */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.002, 0]} receiveShadow>
        <planeGeometry args={[3.2, 5.0]} />
        <meshStandardMaterial
          color="#0c1012"
          roughness={0.8}
          metalness={0.1}
        />
      </mesh>

      {/* Turf Grid Floor Grid Lines */}
      <gridHelper
        args={[8, 16, '#303438', '#181b1d']}
        position={[0, -0.001, 0]}
      />

      {/* Popping Crease (White Line at Z = 0) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, 0]}>
        <planeGeometry args={[2.44, 0.04]} />
        <meshBasicMaterial color="#f5f5f5" />
      </mesh>

      {/* Bowling / Stumps Crease Line (Z = -1.22m) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, -1.22]}>
        <planeGeometry args={[2.64, 0.03]} />
        <meshBasicMaterial color="#7FEA35" transparent opacity={0.6} />
      </mesh>

      {/* Return Creases (Lateral boundaries) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-1.22, 0.001, -0.6]}>
        <planeGeometry args={[0.03, 1.4]} />
        <meshBasicMaterial color="#40454a" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[1.22, 0.001, -0.6]}>
        <planeGeometry args={[0.03, 1.4]} />
        <meshBasicMaterial color="#40454a" />
      </mesh>

      {/* 3 Stumps Marker Silhouette at Crease */}
      {[-0.08, 0, 0.08].map((x, i) => (
        <mesh key={i} position={[x, 0.36, -1.22]}>
          <cylinderGeometry args={[0.012, 0.012, 0.72, 8]} />
          <meshStandardMaterial
            color="#7FEA35"
            emissive="#7FEA35"
            emissiveIntensity={0.6}
            roughness={0.3}
          />
        </mesh>
      ))}
      {/* Bails */}
      <mesh position={[0, 0.725, -1.22]}>
        <cylinderGeometry args={[0.008, 0.008, 0.22, 8]} />
        <meshStandardMaterial color="#ffffff" emissive="#7FEA35" emissiveIntensity={0.8} />
      </mesh>

      {/* Soft Ground Fog Glow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.0005, 0]}>
        <ringGeometry args={[0.1, 1.8, 32]} />
        <meshBasicMaterial color="#7FEA35" transparent opacity={0.04} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
};
