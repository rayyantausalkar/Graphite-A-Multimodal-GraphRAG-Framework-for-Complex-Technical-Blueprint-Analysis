"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, Eye, EyeOff } from "lucide-react";
import { BlueprintTopology, BlueprintNode, BlueprintEdge } from "@/lib/types";
import { HoverTooltipHUD } from "@/components/canvas3d/HoverTooltipHUD";

// Subsystem Color Mapping (Industrial Cyan Light Palette)
const SUBSYSTEM_COLORS = [
  "#0D9488", // Teal / Process
  "#B45309", // Warm Amber / Safety & Isolation
  "#123B3A", // Dark Teal / Utility
  "#0284C7", // Cyan / Feedstock
  "#D97706", // Gold / High Pressure
  "#4F46E5", // Indigo / Instrumentation
  "#059669", // Emerald / Cooling
  "#7C3AED", // Violet / Chemical
];

interface BlueprintCanvas2DProps {
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

export function BlueprintCanvas2D({
  topology,
  highlightedNodeIds,
  highlightedEdgeIds,
  selectedNode,
  onSelectNode,
  layers,
}: BlueprintCanvas2DProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Pan & Zoom Transform State
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Hover state
  const [hoveredNode, setHoveredNode] = useState<BlueprintNode | null>(null);
  const [pointerPos, setPointerPos] = useState({ x: 0, y: 0 });

  const imgW = topology.image_width || 2000;
  const imgH = topology.image_height || 1400;

  // Fit to screen on initial mount or when image dimensions change
  const fitToScreen = useCallback(() => {
    if (!containerRef.current) return;
    const { clientWidth, clientHeight } = containerRef.current;
    if (clientWidth <= 0 || clientHeight <= 0) return;

    const padding = 60;
    const scaleX = (clientWidth - padding * 2) / imgW;
    const scaleY = (clientHeight - padding * 2) / imgH;
    const fitScale = Math.min(scaleX, scaleY, 1.2);

    const fitX = (clientWidth - imgW * fitScale) / 2;
    const fitY = (clientHeight - imgH * fitScale) / 2;

    setScale(fitScale);
    setOffset({ x: fitX, y: fitY });
  }, [imgW, imgH]);

  useEffect(() => {
    fitToScreen();
    window.addEventListener("resize", fitToScreen);
    return () => window.removeEventListener("resize", fitToScreen);
  }, [fitToScreen]);

  // Center on selected node if selected externally
  useEffect(() => {
    if (!selectedNode || !containerRef.current) return;
    const { clientWidth, clientHeight } = containerRef.current;
    const targetScale = Math.max(scale, 0.9);
    const targetX = clientWidth / 2 - selectedNode.cx * targetScale;
    const targetY = clientHeight / 2 - selectedNode.cy * targetScale;

    setOffset({ x: targetX, y: targetY });
    setScale(targetScale);
  }, [selectedNode]);

  // Mouse wheel zoom centered at cursor
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newScale = Math.min(Math.max(scale * zoomFactor, 0.2), 5.0);

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Preserve world coordinate under cursor
    const newX = mouseX - (mouseX - offset.x) * (newScale / scale);
    const newY = mouseY - (mouseY - offset.y) * (newScale / scale);

    setScale(newScale);
    setOffset({ x: newX, y: newY });
  };

  // Drag pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
    if (hoveredNode) {
      setPointerPos({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Zoom control buttons
  const zoomIn = () => {
    if (!containerRef.current) return;
    const { clientWidth, clientHeight } = containerRef.current;
    const newScale = Math.min(scale * 1.25, 5.0);
    const newX = clientWidth / 2 - (clientWidth / 2 - offset.x) * (newScale / scale);
    const newY = clientHeight / 2 - (clientHeight / 2 - offset.y) * (newScale / scale);
    setScale(newScale);
    setOffset({ x: newX, y: newY });
  };

  const zoomOut = () => {
    if (!containerRef.current) return;
    const { clientWidth, clientHeight } = containerRef.current;
    const newScale = Math.max(scale * 0.8, 0.2);
    const newX = clientWidth / 2 - (clientWidth / 2 - offset.x) * (newScale / scale);
    const newY = clientHeight / 2 - (clientHeight / 2 - offset.y) * (newScale / scale);
    setScale(newScale);
    setOffset({ x: newX, y: newY });
  };

  // Highlighted edges set
  const highlightedSet = useMemo(() => {
    const set = new Set<string>();
    highlightedEdgeIds.forEach(([u, v]) => {
      set.add(`${u}->${v}`);
      set.add(`${v}->${u}`);
    });
    return set;
  }, [highlightedEdgeIds]);

  // Convert waypoints array to SVG path string
  const getPathData = (waypoints: [number, number][]) => {
    if (!waypoints || waypoints.length < 2) return "";
    return (
      `M ${waypoints[0][0]} ${waypoints[0][1]} ` +
      waypoints
        .slice(1)
        .map(([x, y]) => `L ${x} ${y}`)
        .join(" ")
    );
  };

  return (
    <div
      ref={containerRef}
      className={`relative h-full w-full overflow-hidden select-none bg-[#EFECE6] ${
        isDragging ? "cursor-grabbing" : "cursor-grab"
      }`}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Blueprint Visual Drafting Canvas */}
      <div
        className="absolute top-0 left-0 transition-transform duration-75 origin-top-left"
        style={{
          transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
        }}
      >
        {/* White Blueprint Drafting Backing */}
        <div
          className="relative bg-white shadow-2xl rounded-sm border border-[#123B3A]/20"
          style={{ width: imgW, height: imgH }}
        >
          {/* Layer 1: Blueprint Schematic Raster */}
          {layers.blueprint && (
            <img
              src="/api/blueprint/image"
              alt="P&ID Technical Blueprint"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              style={{ opacity: 0.95 }}
            />
          )}

          {/* Layer 2: 249 Orthogonal Flow Conduits (Pipelines SVG) */}
          {layers.pipes && (
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox={`0 0 ${imgW} ${imgH}`}
            >
              <defs>
                <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3.5" result="glow" />
                  <feMerge>
                    <feMergeNode in="glow" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Normal Inactive Pipelines */}
              {topology.edges.map((edge, idx) => {
                const isHi = highlightedSet.has(`${edge.source}->${edge.target}`);
                if (isHi || !edge.waypoints || edge.waypoints.length < 2) return null;
                return (
                  <path
                    key={`pipe-${idx}`}
                    d={getPathData(edge.waypoints)}
                    fill="none"
                    stroke="#123B3A"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeOpacity="0.45"
                  />
                );
              })}

              {/* Active Flow Pipelines (Highlighted with animated glow) */}
              {topology.edges.map((edge, idx) => {
                const isHi = highlightedSet.has(`${edge.source}->${edge.target}`);
                if (!isHi || !edge.waypoints || edge.waypoints.length < 2) return null;
                const pathData = getPathData(edge.waypoints);
                return (
                  <g key={`pipe-hi-${idx}`}>
                    {/* Glowing Underlayer */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke="#55D6BE"
                      strokeWidth="8"
                      strokeOpacity="0.5"
                      filter="url(#cyanGlow)"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    {/* Core Pipe Line */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke="#0D9488"
                      strokeWidth="3.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    {/* Animated Flow Pulse */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke="#55D6BE"
                      strokeWidth="3.5"
                      strokeDasharray="8 12"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="animate-[dash_1.5s_linear_infinite]"
                    />
                  </g>
                );
              })}
            </svg>
          )}

          {/* Layer 3: Interactive Equipment Hotspots & ISA Tags */}
          {layers.equipment && (
            <div className="absolute inset-0 pointer-events-auto">
              {topology.nodes.map((node) => {
                const isHovered = hoveredNode?.id === node.id;
                const isSelected = selectedNode?.id === node.id;
                const isHighlighted = highlightedNodeIds.includes(node.id);
                const subColor =
                  SUBSYSTEM_COLORS[(node.subsystem_id || 0) % SUBSYSTEM_COLORS.length];

                // Bounding Box or Default Hotspot
                const [xmin, ymin, xmax, ymax] = node.bbox || [
                  node.cx - 24,
                  node.cy - 24,
                  node.cx + 24,
                  node.cy + 24,
                ];
                const width = Math.max(xmax - xmin, 28);
                const height = Math.max(ymax - ymin, 28);

                return (
                  <div
                    key={node.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectNode(node);
                    }}
                    onMouseEnter={(e) => {
                      setHoveredNode(node);
                      setPointerPos({ x: e.clientX, y: e.clientY });
                    }}
                    onMouseLeave={() => setHoveredNode(null)}
                    style={{
                      left: `${xmin}px`,
                      top: `${ymin}px`,
                      width: `${width}px`,
                      height: `${height}px`,
                    }}
                    className={`absolute cursor-pointer transition-all duration-150 rounded-lg group ${
                      isSelected
                        ? "border-2 border-[#123B3A] bg-[#123B3A]/20 shadow-lg ring-4 ring-[#55D6BE]/40 z-30"
                        : isHighlighted
                        ? "border-2 border-[#55D6BE] bg-[#55D6BE]/25 shadow-md ring-3 ring-[#55D6BE]/30 z-20 animate-pulse"
                        : isHovered
                        ? "border-2 border-[#123B3A] bg-[#123B3A]/15 shadow-sm z-20"
                        : "border border-[#123B3A]/25 bg-[#123B3A]/5 hover:border-[#123B3A] z-10"
                    }`}
                  >
                    {/* Pulsing beacon on highlighted or selected elements */}
                    {(isHighlighted || isSelected) && (
                      <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#55D6BE] opacity-75" />
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-[#123B3A]" />
                      </span>
                    )}

                    {/* Equipment Tag Badge */}
                    <div
                      className={`absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded px-1.5 py-0.2 font-mono text-[10px] font-semibold transition shadow-xs pointer-events-none ${
                        isSelected
                          ? "bg-[#123B3A] text-white"
                          : isHighlighted
                          ? "bg-[#55D6BE] text-[#101516]"
                          : isHovered
                          ? "bg-[#123B3A] text-white"
                          : "bg-white/95 text-[#101516] border border-[#123B3A]/20"
                      }`}
                    >
                      {node.tag || node.id}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Floating Hover Telemetry HUD */}
      <HoverTooltipHUD node={hoveredNode} pointerPos={pointerPos} />

      {/* 2D Zoom & Navigation Controls (Bottom-Right) */}
      <div className="absolute bottom-6 right-6 z-30 flex items-center gap-1.5 rounded-2xl border border-[#123B3A]/15 bg-white/95 p-1.5 shadow-xl backdrop-blur-md">
        <button
          onClick={zoomIn}
          className="rounded-xl p-2 text-[#101516]/75 transition hover:bg-[#F7F6F2] hover:text-[#101516]"
          title="Zoom In (+)"
        >
          <ZoomIn className="h-4 w-4" />
        </button>

        <span className="min-w-[48px] text-center font-mono text-xs font-semibold text-[#123B3A]">
          {Math.round(scale * 100)}%
        </span>

        <button
          onClick={zoomOut}
          className="rounded-xl p-2 text-[#101516]/75 transition hover:bg-[#F7F6F2] hover:text-[#101516]"
          title="Zoom Out (-)"
        >
          <ZoomOut className="h-4 w-4" />
        </button>

        <div className="h-4 w-[1px] bg-[#123B3A]/20 mx-0.5" />

        <button
          onClick={fitToScreen}
          className="rounded-xl p-2 text-[#101516]/75 transition hover:bg-[#F7F6F2] hover:text-[#101516]"
          title="Fit Blueprint to Window"
        >
          <Maximize2 className="h-4 w-4" />
        </button>

        <button
          onClick={() => {
            setScale(1);
            if (containerRef.current) {
              const { clientWidth, clientHeight } = containerRef.current;
              setOffset({
                x: (clientWidth - imgW) / 2,
                y: (clientHeight - imgH) / 2,
              });
            }
          }}
          className="rounded-xl p-2 text-[#101516]/75 transition hover:bg-[#F7F6F2] hover:text-[#101516]"
          title="100% Native Scale"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      {/* Mini-Map Overview Thumbnail (Bottom-Left above inspector) */}
      <div className="absolute top-22 right-6 z-20 hidden md:block rounded-xl border border-[#123B3A]/15 bg-white/95 p-2 shadow-xl backdrop-blur-md">
        <div className="text-[10px] font-brand font-semibold text-[#101516]/60 mb-1 flex items-center justify-between">
          <span>Overview</span>
          <span className="font-mono text-[9px] text-[#123B3A]">
            {imgW} × {imgH}
          </span>
        </div>
        <div
          className="relative overflow-hidden rounded border border-[#123B3A]/15 bg-[#F7F6F2]"
          style={{ width: 140, height: (140 * imgH) / imgW }}
        >
          <img
            src="/api/blueprint/image"
            alt="Overview"
            className="w-full h-full object-contain opacity-70"
          />
          {/* Viewport Window Indicator */}
          {containerRef.current && (
            <div
              className="absolute border-2 border-[#123B3A] bg-[#123B3A]/15 pointer-events-none rounded-xs"
              style={{
                left: `${Math.max(
                  0,
                  Math.min(140, (-offset.x / (imgW * scale)) * 140)
                )}px`,
                top: `${Math.max(
                  0,
                  Math.min(
                    (140 * imgH) / imgW,
                    (-offset.y / (imgH * scale)) * ((140 * imgH) / imgW)
                  )
                )}px`,
                width: `${Math.min(
                  140,
                  ((containerRef.current.clientWidth || 800) / (imgW * scale)) * 140
                )}px`,
                height: `${Math.min(
                  (140 * imgH) / imgW,
                  ((containerRef.current.clientHeight || 600) / (imgH * scale)) *
                    ((140 * imgH) / imgW)
                )}px`,
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
