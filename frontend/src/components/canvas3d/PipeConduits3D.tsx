"use client";

import React, { useMemo } from "react";
import * as THREE from "three";
import { BlueprintEdge } from "@/lib/types";

interface PipeConduits3DProps {
  edges: BlueprintEdge[];
  imageWidth: number;
  imageHeight: number;
  scale: number;
  highlightedEdgeIds: [string, string][];
  visible: boolean;
}

export function PipeConduits3D({
  edges,
  imageWidth,
  imageHeight,
  scale,
  highlightedEdgeIds,
  visible,
}: PipeConduits3DProps) {
  if (!visible) return null;

  const highlightedSet = useMemo(() => {
    const set = new Set<string>();
    highlightedEdgeIds.forEach(([u, v]) => {
      set.add(`${u}->${v}`);
      set.add(`${v}->${u}`);
    });
    return set;
  }, [highlightedEdgeIds]);

  // Pre-calculate all straight orthogonal cylinder segments and elbow joints
  const { segments, joints } = useMemo(() => {
    const segList: Array<{
      key: string;
      position: [number, number, number];
      quaternion: THREE.Quaternion;
      length: number;
      isHighlighted: boolean;
    }> = [];

    const jointList: Array<{
      key: string;
      position: [number, number, number];
      isHighlighted: boolean;
    }> = [];

    const upVector = new THREE.Vector3(0, 1, 0);

    edges.forEach((edge, edgeIdx) => {
      if (!edge.waypoints || edge.waypoints.length < 2) return;

      const isHighlighted = highlightedSet.has(`${edge.source}->${edge.target}`);
      const y3d = isHighlighted ? 0.20 : 0.08;

      // Map 2D waypoints into 3D vectors
      const pts3d = edge.waypoints.map(([px, py]) => {
        return new THREE.Vector3(
          (px - imageWidth / 2) * scale,
          y3d,
          (py - imageHeight / 2) * scale
        );
      });

      // Build straight orthogonal cylinder for each segment
      for (let i = 0; i < pts3d.length - 1; i++) {
        const start = pts3d[i];
        const end = pts3d[i + 1];
        const dist = start.distanceTo(end);
        if (dist < 0.002) continue;

        const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(end, start).normalize();
        const quat = new THREE.Quaternion().setFromUnitVectors(upVector, dir);

        segList.push({
          key: `seg-${edgeIdx}-${i}`,
          position: [midpoint.x, midpoint.y, midpoint.z],
          quaternion: quat,
          length: dist,
          isHighlighted,
        });

        // Add spherical elbow joint at bends
        if (i > 0) {
          jointList.push({
            key: `joint-${edgeIdx}-${i}`,
            position: [start.x, start.y, start.z],
            isHighlighted,
          });
        }
      }
    });

    return { segments: segList, joints: jointList };
  }, [edges, imageWidth, imageHeight, scale, highlightedSet]);

  return (
    <group>
      {/* 1. Normal Straight Pipe Segments */}
      {segments
        .filter((s) => !s.isHighlighted)
        .map((s) => (
          <mesh
            key={s.key}
            position={s.position}
            quaternion={s.quaternion}
          >
            <cylinderGeometry args={[0.045, 0.045, s.length, 6]} />
            <meshStandardMaterial
              color="#0284C7"
              metalness={0.7}
              roughness={0.3}
              emissive="#0284C7"
              emissiveIntensity={0.25}
            />
          </mesh>
        ))}

      {/* 2. Highlighted Flow Pipe Segments */}
      {segments
        .filter((s) => s.isHighlighted)
        .map((s) => (
          <mesh
            key={s.key}
            position={s.position}
            quaternion={s.quaternion}
          >
            <cylinderGeometry args={[0.11, 0.11, s.length, 10]} />
            <meshStandardMaterial
              color="#00E5FF"
              metalness={0.8}
              roughness={0.15}
              emissive="#00E5FF"
              emissiveIntensity={0.95}
            />
          </mesh>
        ))}

      {/* 3. Normal Elbow Joints */}
      {joints
        .filter((j) => !j.isHighlighted)
        .map((j) => (
          <mesh key={j.key} position={j.position}>
            <sphereGeometry args={[0.048, 6, 6]} />
            <meshStandardMaterial color="#0284C7" metalness={0.7} roughness={0.3} />
          </mesh>
        ))}

      {/* 4. Highlighted Elbow Joints */}
      {joints
        .filter((j) => j.isHighlighted)
        .map((j) => (
          <mesh key={j.key} position={j.position}>
            <sphereGeometry args={[0.115, 8, 8]} />
            <meshStandardMaterial
              color="#00E5FF"
              emissive="#00E5FF"
              emissiveIntensity={0.95}
            />
          </mesh>
        ))}
    </group>
  );
}
