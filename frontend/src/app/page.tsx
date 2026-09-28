"use client";

import React, { useEffect, useState } from "react";
import {
  Layers,
  Box,
  GitBranch,
  Image as ImageIcon,
  Activity,
  Maximize2,
} from "lucide-react";
import { BlueprintTopology, BlueprintNode } from "@/lib/types";
import { fetchBlueprintTopology } from "@/lib/api";
import { BlueprintScene3D } from "@/components/canvas3d/BlueprintScene3D";
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
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-slate-950 text-slate-100">
      {/* TOP NAVBAR */}
      <header className="flex h-14 items-center justify-between border-b border-slate-800/80 bg-slate-950/90 px-5 backdrop-blur-xl z-20">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-sky-400 text-slate-950 font-black shadow-md shadow-cyan-500/20">
            ⬡
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-black tracking-wider text-white">
                GRAPHITE
              </span>
              <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] font-bold text-cyan-400 border border-cyan-500/30">
                3D DIGITAL TWIN
              </span>
            </div>
          </div>
        </div>

        {/* 3D LAYER TOGGLE CHIPS */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setLayers((l) => ({ ...l, blueprint: !l.blueprint }))}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              layers.blueprint
                ? "border border-cyan-500/40 bg-cyan-500/15 text-cyan-300 shadow-sm shadow-cyan-500/20"
                : "border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200"
            }`}
          >
            <ImageIcon className="h-3 w-3" />
            <span>Blueprint Plane</span>
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, equipment: !l.equipment }))}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              layers.equipment
                ? "border border-cyan-500/40 bg-cyan-500/15 text-cyan-300 shadow-sm shadow-cyan-500/20"
                : "border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200"
            }`}
          >
            <Box className="h-3 w-3" />
            <span>3D Equipment</span>
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, pipes: !l.pipes }))}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              layers.pipes
                ? "border border-cyan-500/40 bg-cyan-500/15 text-cyan-300 shadow-sm shadow-cyan-500/20"
                : "border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitBranch className="h-3 w-3" />
            <span>Flow Conduits</span>
          </button>
        </div>

        {/* PLANT TELEMETRY STATS */}
        <div className="flex items-center gap-3 font-mono text-xs text-slate-400">
          {topology && (
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                <span className="text-slate-200 font-semibold">
                  {topology.nodes.length}
                </span>{" "}
                Assets
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                <span className="text-slate-200 font-semibold">
                  {topology.edges.length}
                </span>{" "}
                Pipes
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span className="text-slate-200 font-semibold">
                  {Object.keys(topology.subsystems || {}).length}
                </span>{" "}
                Subsystems
              </span>
            </div>
          )}
        </div>
      </header>

      {/* MAIN 3D WORKSPACE & COPILOT */}
      <main className="relative flex flex-1 overflow-hidden">
        {loading && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-slate-950 gap-3 text-cyan-400">
            <Activity className="h-8 w-8 animate-spin" />
            <span className="font-mono text-sm font-semibold tracking-wider">
              INITIALIZING 3D DIGITAL TWIN & MMKG...
            </span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-slate-950 p-6 text-center text-red-400">
            <h2 className="text-lg font-bold">Failed to connect to Graphite Backend</h2>
            <p className="mt-1 text-sm text-slate-400">{error}</p>
            <p className="mt-4 text-xs text-slate-500">
              Ensure the Python backend is running: <code>uv run python examples/run_layer4_server.py</code>
            </p>
          </div>
        )}

        {/* 3D Blueprint Canvas */}
        <div className="relative flex-1 h-full w-full">
          {topology && (
            <BlueprintScene3D
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
