"use client";

import React, { useEffect, useState } from "react";
import { X, ShieldAlert, GitFork, ArrowDownRight, ArrowUpLeft, Activity } from "lucide-react";
import { BlueprintNode, NodeDetail } from "@/lib/types";
import { fetchNodeDetails } from "@/lib/api";

interface EquipmentInspectorProps {
  node: BlueprintNode | null;
  onClose: () => void;
  onAction: (action: "downstream" | "isolate" | "simulate", node: BlueprintNode) => void;
}

export function EquipmentInspector({
  node,
  onClose,
  onAction,
}: EquipmentInspectorProps) {
  const [details, setDetails] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!node) {
      setDetails(null);
      return;
    }
    setLoading(true);
    fetchNodeDetails(node.id)
      .then((data) => setDetails(data))
      .catch((err) => console.error("Error loading node details:", err))
      .finally(() => setLoading(false));
  }, [node]);

  if (!node) return null;

  return (
    <div className="fixed bottom-6 left-6 z-40 w-88 rounded-2xl border border-cyan-500/30 bg-slate-950/85 p-5 shadow-2xl backdrop-blur-2xl transition-all duration-200">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-xl border border-cyan-500/30 bg-black/90 p-1">
            <img
              src={details?.visual_crop_url || node.crop_url}
              alt={node.id}
              className="h-full w-full object-contain"
              onError={(e) => {
                (e.currentTarget as HTMLElement).style.display = "none";
              }}
            />
          </div>
          <div>
            <h3 className="font-mono text-base font-bold text-slate-100">
              {details?.tag || node.tag || node.id}
            </h3>
            <p className="font-mono text-xs font-semibold uppercase tracking-wider text-cyan-400">
              {node.label}
            </p>
            <span className="text-[11px] text-slate-400">
              {details?.subsystem_name || node.subsystem_name || "Process Domain"}
            </span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white/10 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {loading ? (
        <div className="my-6 flex items-center justify-center gap-2 text-xs text-cyan-400">
          <Activity className="h-4 w-4 animate-spin" />
          <span>Loading technical telemetry...</span>
        </div>
      ) : (
        <>
          {/* Engineering Specifications */}
          <div className="my-4 space-y-1.5 rounded-xl border border-slate-800/80 bg-slate-900/50 p-3 text-xs">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Technical Specifications
            </div>
            {details?.specs && Object.keys(details.specs).length > 0 ? (
              Object.entries(details.specs).map(([k, v]) => (
                <div key={k} className="flex justify-between py-0.5">
                  <span className="capitalize text-slate-400">{k}</span>
                  <span className="font-mono font-medium text-slate-200">{String(v)}</span>
                </div>
              ))
            ) : (
              <div className="text-slate-400 italic">Standard Plant Rating</div>
            )}
          </div>

          {/* Safety & Isolation Cut-Valves */}
          <div className="mb-4 rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-emerald-400">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>Containment Boundary Valves</span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-slate-300">
              {details?.isolation_valves && details.isolation_valves.length > 0
                ? details.isolation_valves.join(", ")
                : "No immediate boundary cut-valves required"}
            </div>
          </div>

          {/* Upstream & Downstream Flow Previews */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2">
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <ArrowUpLeft className="h-3 w-3 text-sky-400" />
                <span>Upstream ({details?.upstream?.length ?? 0})</span>
              </div>
              <div className="mt-1 truncate font-mono text-[11px] text-slate-300">
                {details?.upstream?.slice(0, 2).join(", ") || "None"}
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2">
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <ArrowDownRight className="h-3 w-3 text-cyan-400" />
                <span>Downstream ({details?.downstream?.length ?? 0})</span>
              </div>
              <div className="mt-1 truncate font-mono text-[11px] text-slate-300">
                {details?.downstream?.slice(0, 2).join(", ") || "None"}
              </div>
            </div>
          </div>

          {/* Action Triggers */}
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => onAction("downstream", node)}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-300 transition hover:bg-cyan-500/20 active:scale-95"
            >
              <GitFork className="h-3.5 w-3.5" />
              Trace Flow
            </button>
            <button
              onClick={() => onAction("isolate", node)}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20 active:scale-95"
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              Isolate
            </button>
          </div>
        </>
      )}
    </div>
  );
}
