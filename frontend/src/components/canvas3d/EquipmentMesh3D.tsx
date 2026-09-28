"use client";

import React, { useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { BlueprintNode } from "@/lib/types";

// Louvain Community Subsystem Palette
export const SUBSYSTEM_PALETTE = [
  "#00E5FF", // Cyan (Process)
  "#3B82F6", // Blue (Process Water)
  "#10B981", // Emerald (Safety / Relief)
  "#F59E0B", // Amber (Steam / Heating)
  "#EC4899", // Pink (Chemical / Injections)
  "#8B5CF6", // Purple (Gas / Separation)
  "#14B8A6", // Teal (Cooling Loop)
  "#EF4444", // Red (High Pressure)
  "#6366F1", // Indigo (Instrument Air)
  "#EAB308", // Yellow (Feedstock)
];

interface EquipmentMesh3DProps {
  node: BlueprintNode;
  position: [number, number, number];
  isHovered: boolean;
  isSelected: boolean;
  isHighlighted: boolean;
  onPointerOver: (e: any, node: BlueprintNode) => void;
  onPointerOut: (e: any) => void;
  onClick: (e: any, node: BlueprintNode) => void;
}

export function EquipmentMesh3D({
  node,
  position,
  isHovered,
  isSelected,
  isHighlighted,
  onPointerOver,
  onPointerOut,
  onClick,
}: EquipmentMesh3DProps) {
  const meshRef = useRef<THREE.Group>(null);

  const subColor =
    SUBSYSTEM_PALETTE[(node.subsystem_id || 0) % SUBSYSTEM_PALETTE.length];

  // Subtle floating animation and target pulse
  useFrame((state) => {
    if (!meshRef.current) return;
    if (isSelected || isHighlighted) {
      const t = state.clock.getElapsedTime();
      meshRef.current.position.y = position[1] + Math.sin(t * 4) * 0.15 + 0.1;
    } else {
      meshRef.current.position.y = position[1];
    }
  });

  const scale = isHovered ? 1.3 : isSelected ? 1.2 : 1.0;
  const labelLower = (node.label || "").toLowerCase();

  // Procedural geometries based on equipment classification
  return (
    <group
      ref={meshRef}
      position={position}
      scale={[scale, scale, scale]}
      onPointerOver={(e) => {
        e.stopPropagation();
        onPointerOver(e, node);
      }}
      onPointerOut={(e) => {
        e.stopPropagation();
        onPointerOut(e);
      }}
      onClick={(e) => {
        e.stopPropagation();
        onClick(e, node);
      }}
    >
      {/* 1. Storage Tanks & Pressure Vessels */}
      {(labelLower.includes("tank") || labelLower.includes("vessel")) && (
        <group>
          {/* Main Vessel Body */}
          <mesh castShadow receiveShadow position={[0, 0.8, 0]}>
            <cylinderGeometry args={[0.65, 0.65, 1.4, 24]} />
            <meshStandardMaterial
              color={subColor}
              metalness={0.7}
              roughness={0.25}
              emissive={subColor}
              emissiveIntensity={isHovered ? 0.6 : isSelected ? 0.5 : 0.15}
            />
          </mesh>
          {/* Hemispherical Head */}
          <mesh position={[0, 1.5, 0]}>
            <sphereGeometry args={[0.65, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
            <meshStandardMaterial
              color={subColor}
              metalness={0.7}
              roughness={0.25}
            />
          </mesh>
        </group>
      )}

      {/* 2. Pumps & Compressors */}
      {(labelLower.includes("pump") || labelLower.includes("compressor")) && (
        <group>
          {/* Centrifugal Volute Casing */}
          <mesh castShadow receiveShadow position={[0, 0.45, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.55, 0.55, 0.4, 20]} />
            <meshStandardMaterial
              color={subColor}
              metalness={0.8}
              roughness={0.2}
              emissive={subColor}
              emissiveIntensity={isHovered ? 0.7 : isSelected ? 0.5 : 0.2}
            />
          </mesh>
          {/* Motor Body */}
          <mesh position={[-0.45, 0.45, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.38, 0.38, 0.55, 16]} />
            <meshStandardMaterial color="#1E293B" metalness={0.6} roughness={0.4} />
          </mesh>
          {/* Discharge Nozzle */}
          <mesh position={[0.2, 0.8, 0]}>
            <cylinderGeometry args={[0.15, 0.15, 0.4, 12]} />
            <meshStandardMaterial color={subColor} />
          </mesh>
        </group>
      )}

      {/* 3. Valves (Bowtie Dual Cones & Stem) */}
      {labelLower.includes("valve") && (
        <group position={[0, 0.4, 0]}>
          {/* Left Flow Cone */}
          <mesh rotation={[0, 0, -Math.PI / 2]} position={[-0.22, 0, 0]}>
            <coneGeometry args={[0.35, 0.4, 16]} />
            <meshStandardMaterial
              color={subColor}
              metalness={0.8}
              roughness={0.25}
              emissive={subColor}
              emissiveIntensity={isHovered ? 0.7 : isSelected ? 0.5 : 0.25}
            />
          </mesh>
          {/* Right Flow Cone */}
          <mesh rotation={[0, 0, Math.PI / 2]} position={[0.22, 0, 0]}>
            <coneGeometry args={[0.35, 0.4, 16]} />
            <meshStandardMaterial
              color={subColor}
              metalness={0.8}
              roughness={0.25}
              emissive={subColor}
              emissiveIntensity={isHovered ? 0.7 : isSelected ? 0.5 : 0.25}
            />
          </mesh>
          {/* Actuator Stem */}
          <mesh position={[0, 0.4, 0]}>
            <cylinderGeometry args={[0.06, 0.06, 0.5, 8]} />
            <meshStandardMaterial color="#64748B" metalness={0.9} />
          </mesh>
          {/* Handwheel Disc */}
          <mesh position={[0, 0.65, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.2, 0.04, 8, 20]} />
            <meshStandardMaterial color="#F8FAFC" metalness={0.5} />
          </mesh>
        </group>
      )}

      {/* 4. Default / Instruments / Sensors */}
      {!labelLower.includes("tank") &&
        !labelLower.includes("vessel") &&
        !labelLower.includes("pump") &&
        !labelLower.includes("compressor") &&
        !labelLower.includes("valve") && (
          <group position={[0, 0.45, 0]}>
            <mesh position={[0, -0.2, 0]}>
              <cylinderGeometry args={[0.08, 0.12, 0.4, 12]} />
              <meshStandardMaterial color="#475569" metalness={0.8} />
            </mesh>
            <mesh position={[0, 0.2, 0]}>
              <sphereGeometry args={[0.32, 16, 16]} />
              <meshStandardMaterial
                color={subColor}
                metalness={0.7}
                roughness={0.2}
                emissive={subColor}
                emissiveIntensity={isHovered ? 0.8 : isSelected ? 0.6 : 0.3}
              />
            </mesh>
          </group>
        )}

      {/* Selection / Target Indicator Halo */}
      {(isSelected || isHighlighted || isHovered) && (
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.7, 0.85, 32]} />
          <meshBasicMaterial
            color={isSelected ? "#FFFFFF" : isHighlighted ? "#00E5FF" : subColor}
            transparent
            opacity={0.8}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
    </group>
  );
}
