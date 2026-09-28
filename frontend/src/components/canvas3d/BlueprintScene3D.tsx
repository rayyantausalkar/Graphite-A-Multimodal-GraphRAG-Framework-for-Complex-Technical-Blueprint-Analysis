"use client";

import React, { Suspense, useState, useRef, useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import type { OrbitControls as OrbitControlsType } from "three-stdlib";
import { BlueprintTopology, BlueprintNode } from "@/lib/types";
import { GroundBlueprintPlane } from "./GroundBlueprintPlane";
import { EquipmentMesh3D } from "./EquipmentMesh3D";
import { PipeConduits3D } from "./PipeConduits3D";
import { HoverTooltipHUD } from "./HoverTooltipHUD";

interface BlueprintScene3DProps {
  topology: BlueprintTopology;
  highlightedNodeIds: string[];
  highlightedEdgeIds: [string, string][];
  selectedNode: BlueprintNode | null;
  onSelectNode: (node: BlueprintNode) => void;
  layers: {
    blueprint: boolean;
    equipment: boolean;
    pipes: boolean;
  };
}

export function BlueprintScene3D({
  topology,
  highlightedNodeIds,
  highlightedEdgeIds,
  selectedNode,
  onSelectNode,
  layers,
}: BlueprintScene3DProps) {
  const [hoveredNode, setHoveredNode] = useState<BlueprintNode | null>(null);
  const [pointerPos, setPointerPos] = useState({ x: 0, y: 0 });
  const controlsRef = useRef<OrbitControlsType>(null);

  // Normalization scaling factor from blueprint pixels to 3D units
  // Map an image width (e.g. 1000px - 2000px) into ~50-80 3D units
  const maxDim = Math.max(topology.image_width || 1000, topology.image_height || 1000);
  const scale = 60 / maxDim;

  const handlePointerOver = useCallback((e: any, node: BlueprintNode) => {
    setHoveredNode(node);
    if (e.clientX && e.clientY) {
      setPointerPos({ x: e.clientX, y: e.clientY });
    }
  }, []);

  const handlePointerOut = useCallback(() => {
    setHoveredNode(null);
  }, []);

  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  return (
    <div
      className="relative h-full w-full bg-[#030712]"
      onMouseMove={(e) => {
        if (hoveredNode) {
          setPointerPos({ x: e.clientX, y: e.clientY });
        }
      }}
    >
      <Canvas shadows gl={{ antialias: true, alpha: false }}>
        <PerspectiveCamera makeDefault position={[0, 48, 55]} fov={42} />
        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.06}
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={8}
          maxDistance={220}
        />

        {/* Studio Lighting for Engineering Meshes */}
        <ambientLight intensity={0.65} />
        <directionalLight
          position={[25, 45, 30]}
          intensity={1.2}
          castShadow
          shadow-mapSize={[2048, 2048]}
        />
        <directionalLight position={[-25, 30, -30]} intensity={0.4} />
        <pointLight position={[0, 15, 0]} intensity={0.5} color="#00E5FF" />

        <Suspense fallback={null}>
          {/* Ground Blueprint Raster & Grid */}
          <GroundBlueprintPlane
            width={topology.image_width}
            height={topology.image_height}
            scale={scale}
            visible={layers.blueprint}
          />

          {/* 3D Glowing Pipe Conduits */}
          <PipeConduits3D
            edges={topology.edges}
            imageWidth={topology.image_width}
            imageHeight={topology.image_height}
            scale={scale}
            highlightedEdgeIds={highlightedEdgeIds}
            visible={layers.pipes}
          />

          {/* 3D Procedural Equipment Meshes */}
          {layers.equipment &&
            topology.nodes.map((node) => {
              const x3d = (node.cx - topology.image_width / 2) * scale;
              const z3d = (node.cy - topology.image_height / 2) * scale;
              const y3d = 0.1;

              const isHovered = hoveredNode?.id === node.id;
              const isSelected = selectedNode?.id === node.id;
              const isHighlighted = highlightedNodeIds.includes(node.id);

              return (
                <EquipmentMesh3D
                  key={node.id}
                  node={node}
                  position={[x3d, y3d, z3d]}
                  isHovered={isHovered}
                  isSelected={isSelected}
                  isHighlighted={isHighlighted}
                  onPointerOver={handlePointerOver}
                  onPointerOut={handlePointerOut}
                  onClick={(_, n) => onSelectNode(n)}
                />
              );
            })}
        </Suspense>
      </Canvas>

      {/* Floating Hover Telemetry HUD */}
      <HoverTooltipHUD node={hoveredNode} pointerPos={pointerPos} />

      {/* Canvas Viewport Controls */}
      <div className="absolute bottom-6 right-6 z-30 flex flex-col gap-2">
        <button
          onClick={resetCamera}
          className="rounded-xl border border-slate-700 bg-slate-900/80 p-2.5 text-slate-300 shadow-xl backdrop-blur-md transition hover:border-cyan-400 hover:text-white"
          title="Reset Camera View"
        >
          ⟲
        </button>
      </div>
    </div>
  );
}
