"use client";

import React, { useMemo } from "react";
import * as THREE from "three";
import { useTexture } from "@react-three/drei";

interface GroundBlueprintPlaneProps {
  width: number;
  height: number;
  scale: number;
  visible: boolean;
  opacity?: number;
}

export function GroundBlueprintPlane({
  width,
  height,
  scale,
  visible,
  opacity = 0.65,
}: GroundBlueprintPlaneProps) {
  const planeWidth = width * scale;
  const planeHeight = height * scale;

  // Attempt to load blueprint image as texture
  const texture = useTexture("/api/blueprint/image");

  useMemo(() => {
    if (texture) {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
    }
  }, [texture]);

  if (!visible) return null;

  return (
    <group position={[0, -0.05, 0]}>
      {/* Primary Blueprint Raster Texture */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[planeWidth, planeHeight]} />
        <meshBasicMaterial
          map={texture}
          transparent
          opacity={opacity}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Cyber Blueprint Base Grid & Rim Glow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <planeGeometry args={[planeWidth + 4, planeHeight + 4]} />
        <meshBasicMaterial
          color="#040814"
          transparent
          opacity={0.92}
        />
      </mesh>
    </group>
  );
}
