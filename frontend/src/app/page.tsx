"use client";

import React, { useEffect, useState } from "react";
import {
  Box,
  GitBranch,
  Image as ImageIcon,
  Activity,
} from "lucide-react";
import { BlueprintTopology, BlueprintNode } from "@/lib/types";
import { fetchBlueprintTopology } from "@/lib/api";
import { BlueprintCanvas2D } from "@/components/canvas2d/BlueprintCanvas2D";
import { EquipmentInspector } from "@/components/ui/EquipmentInspector";
import { GroundedDialoguePanel } from "@/components/chat/GroundedDialoguePanel";

export default function Home() {
  const [topology, setTopology] = useState<BlueprintTopology | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 3D Scene Highlight & Selection State
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [highlightedEdgeIds, setHighlightedEdgeIds] = useState<[string, string][]>([]);
  const [selectedNode, setSelectedNode] = useState<BlueprintNode | null>(null);

  // Layer Toggles
  const [layers, setLayers] = useState({
    blueprint: true,
    equipment: true,
    pipes: true,
  });

  // Quick prompt integration between inspector and chat
  const [quickPrompt, setQuickPrompt] = useState<string | null>(null);

  useEffect(() => {
    fetchBlueprintTopology()
      .then((data) => {
        setTopology(data);
        setError(null);
      })
      .catch((err) => {
        console.error("Failed to load blueprint:", err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSelectNodeById = (nodeId: string) => {
    if (!topology) return;
    const found = topology.nodes.find((n) => n.id === nodeId);
    if (found) {
      setSelectedNode(found);
      setHighlightedNodeIds([found.id]);
    }
  };

  const handleInspectorAction = (
    action: "downstream" | "isolate" | "simulate",
    node: BlueprintNode
  ) => {
    const disp = node.tag || node.id;
    if (action === "downstream") {
      setQuickPrompt(`Show me downstream equipment and flow routes from ${disp}`);
    } else if (action === "isolate") {
      setQuickPrompt(`Find the minimal boundary valves required to isolate ${disp}`);
    } else if (action === "simulate") {
      setQuickPrompt(`Simulate isolation closure for ${disp}`);
    }
  };

  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-[#F7F6F2] text-[#101516]">
      {/* TOP NAVBAR */}
      <header className="flex h-14 items-center justify-between border-b border-[#123B3A]/15 bg-white/95 px-5 backdrop-blur-xl z-20 shadow-sm">
        <div className="flex items-center gap-3">
          <img
            src="/logo-emblem.png"
            alt="Graphite Logo"
            className="h-8 w-8 rounded-lg shadow-sm border border-[#123B3A]/15 object-contain"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-brand text-base font-bold tracking-wider text-[#101516]">
                GRAPHITE
              </span>
              <span className="rounded bg-[#F7F6F2] px-1.5 py-0.5 font-mono text-[10px] font-medium text-[#123B3A] border border-[#123B3A]/20">
                2D BLUEPRINT TWIN
              </span>
            </div>
          </div>
        </div>

        {/* 2D LAYER TOGGLE CHIPS */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setLayers((l) => ({ ...l, blueprint: !l.blueprint }))}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              layers.blueprint
                ? "border border-[#123B3A] bg-[#123B3A] text-white shadow-sm"
                : "border border-[#123B3A]/20 bg-white text-[#101516]/70 hover:bg-[#F7F6F2] hover:text-[#101516]"
            }`}
          >
            <ImageIcon className="h-3 w-3" />
            <span>Blueprint Raster</span>
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, equipment: !l.equipment }))}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              layers.equipment
                ? "border border-[#123B3A] bg-[#123B3A] text-white shadow-sm"
                : "border border-[#123B3A]/20 bg-white text-[#101516]/70 hover:bg-[#F7F6F2] hover:text-[#101516]"
            }`}
          >
            <Box className="h-3 w-3" />
            <span>Equipment Hotspots</span>
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, pipes: !l.pipes }))}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              layers.pipes
                ? "border border-[#123B3A] bg-[#123B3A] text-white shadow-sm"
                : "border border-[#123B3A]/20 bg-white text-[#101516]/70 hover:bg-[#F7F6F2] hover:text-[#101516]"
            }`}
          >
            <GitBranch className="h-3 w-3" />
            <span>Flow Conduits</span>
          </button>
        </div>

        {/* PLANT TELEMETRY STATS */}
        <div className="flex items-center gap-3 font-mono text-xs text-[#101516]/60">
          {topology && (
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-[#123B3A]" />
                <span className="text-[#101516] font-semibold">
                  {topology.nodes.length}
                </span>{" "}
                Assets
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-[#123B3A]/60" />
                <span className="text-[#101516] font-semibold">
                  {topology.edges.length}
                </span>{" "}
                Pipes
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-[#B45309]" />
                <span className="text-[#101516] font-semibold">
                  {Object.keys(topology.subsystems || {}).length}
                </span>{" "}
                Subsystems
              </span>
            </div>
          )}
        </div>
      </header>

      {/* MAIN 2D WORKSPACE & COPILOT */}
      <main className="relative flex flex-1 overflow-hidden">
        {loading && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#F7F6F2] gap-3 text-[#123B3A]">
            <Activity className="h-8 w-8 animate-spin" />
            <span className="font-mono text-sm font-semibold tracking-wider">
              INITIALIZING 2D BLUEPRINT TWIN & MMKG...
            </span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#F7F6F2] p-6 text-center text-[#B45309]">
            <h2 className="text-lg font-bold">Failed to connect to Graphite Backend</h2>
            <p className="mt-1 text-sm text-[#101516]/70">{error}</p>
            <p className="mt-4 text-xs text-[#101516]/50">
              Ensure the Python backend is running: <code>uv run python examples/run_layer4_server.py</code>
            </p>
          </div>
        )}

        {/* 2D Blueprint Canvas Viewport */}
        <div className="relative flex-1 h-full w-full">
          {/* Floating Brand & Page Title HUD */}
          <div className="pointer-events-none absolute top-5 left-6 z-10 select-none">
            <div className="flex items-center gap-3.5">
              <img
                src="/logo-emblem.png"
                alt="Graphite Logo"
                className="h-14 w-14 rounded-2xl shadow-md border border-[#123B3A]/20 bg-[#F7F6F2] p-0.5 object-contain"
              />
              <div>
                <div className="flex items-baseline gap-2.5">
                  <h1 className="type-brand text-[#101516]">
                    GRAPHITE
                  </h1>
                  <span className="type-technical text-[#123B3A] tracking-widest uppercase font-semibold">
                    v2.0 MMKG
                  </span>
                </div>
                <h2 className="type-page-title text-[#123B3A] -mt-1">
                  Interactive Blueprint Intelligence
                </h2>
              </div>
            </div>
            <p className="type-body text-[#101516]/75 max-w-md mt-1.5">
              Multimodal GraphRAG topological reasoning & interactive flow telemetry.
            </p>
          </div>

          {topology && (
            <BlueprintCanvas2D
              topology={topology}
              highlightedNodeIds={highlightedNodeIds}
              highlightedEdgeIds={highlightedEdgeIds}
              selectedNode={selectedNode}
              onSelectNode={setSelectedNode}
              layers={layers}
            />
          )}

          {/* Floating Selected Equipment Inspector */}
          <EquipmentInspector
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onAction={handleInspectorAction}
          />
        </div>

        {/* Grounded GraphRAG Dialogue Copilot */}
        <GroundedDialoguePanel
          onHighlightElements={(nodes, edges) => {
            setHighlightedNodeIds(nodes);
            setHighlightedEdgeIds(edges);
          }}
          onSelectNodeById={handleSelectNodeById}
          quickPromptText={quickPrompt}
          onClearQuickPrompt={() => setQuickPrompt(null)}
        />
      </main>
    </div>
  );
}
