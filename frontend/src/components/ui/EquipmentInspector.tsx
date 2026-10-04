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
    <div className="fixed bottom-6 left-6 z-40 w-88 rounded-2xl border border-[#123B3A]/20 bg-white/95 p-5 shadow-2xl backdrop-blur-2xl text-[#101516] transition-all duration-200">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-xl border border-[#123B3A]/15 bg-[#F7F6F2] p-1">
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
            <div className="type-technical font-medium text-[#123B3A] tracking-wide">
              {details?.tag || node.tag || node.id}
            </div>
            <h4 className="font-brand text-[20px] font-semibold leading-tight text-[#101516]">
              {node.label}
            </h4>
            <span className="font-body text-[14px] text-[#101516]/70">
              {details?.subsystem_name || node.subsystem_name || "Process Domain"}
            </span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-[#101516]/60 transition hover:bg-[#F7F6F2] hover:text-[#101516]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {loading ? (
        <div className="my-6 flex items-center justify-center gap-2 font-body text-xs text-[#123B3A]">
          <Activity className="h-4 w-4 animate-spin" />
          <span>Loading technical telemetry...</span>
        </div>
      ) : (
        <>
          {/* Engineering Specifications */}
          <div className="my-4 space-y-1.5 rounded-xl border border-[#123B3A]/15 bg-[#F7F6F2] p-3 text-xs">
            <div className="font-brand text-[11px] font-semibold uppercase tracking-wider text-[#101516]/60">
              Technical Specifications
            </div>
            {details?.specs && Object.keys(details.specs).length > 0 ? (
              Object.entries(details.specs).map(([k, v]) => (
                <div key={k} className="flex justify-between py-0.5">
                  <span className="font-mono text-[11px] capitalize text-[#101516]/65">{k}</span>
                  <span className="type-technical text-[#101516] font-medium">{String(v)}</span>
                </div>
              ))
            ) : (
              <div className="font-body text-[#101516]/50 italic">Standard Plant Rating</div>
            )}
          </div>

          {/* Safety & Isolation Cut-Valves in Warm Gold */}
          <div className="mb-4 rounded-xl border border-[#E5B93F]/40 bg-[#E5B93F]/15 p-3 text-xs">
            <div className="flex items-center gap-1.5 font-brand text-xs font-semibold text-[#B45309]">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>Containment Boundary Valves</span>
            </div>
            <div className="mt-1 font-mono text-[11px] font-medium text-[#101516]">
              {details?.isolation_valves && details.isolation_valves.length > 0
                ? details.isolation_valves.join(", ")
                : "No immediate boundary cut-valves required"}
            </div>
          </div>

          {/* Upstream & Downstream Flow Previews */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-[#123B3A]/15 bg-[#F7F6F2] p-2">
              <div className="flex items-center gap-1 font-body text-[11px] text-[#101516]/65">
                <ArrowUpLeft className="h-3 w-3 text-[#123B3A]" />
                <span>Upstream ({details?.upstream?.length ?? 0})</span>
              </div>
              <div className="mt-1 truncate font-mono text-[11px] text-[#101516]">
                {details?.upstream?.slice(0, 2).join(", ") || "None"}
              </div>
            </div>

            <div className="rounded-lg border border-[#123B3A]/15 bg-[#F7F6F2] p-2">
              <div className="flex items-center gap-1 font-body text-[11px] text-[#101516]/65">
                <ArrowDownRight className="h-3 w-3 text-[#123B3A]" />
                <span>Downstream ({details?.downstream?.length ?? 0})</span>
              </div>
              <div className="mt-1 truncate font-mono text-[11px] text-[#101516]">
                {details?.downstream?.slice(0, 2).join(", ") || "None"}
              </div>
            </div>
          </div>

          {/* Action Triggers */}
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => onAction("downstream", node)}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-[#123B3A] bg-[#123B3A] px-3 py-2 font-brand text-xs font-semibold text-white shadow-sm transition hover:bg-[#1D4F4D] active:scale-95"
            >
              <GitFork className="h-3.5 w-3.5 text-[#55D6BE]" />
              Trace Flow
            </button>
            <button
              onClick={() => onAction("isolate", node)}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-[#E5B93F] bg-[#E5B93F]/20 px-3 py-2 font-brand text-xs font-semibold text-[#B45309] transition hover:bg-[#E5B93F] hover:text-white active:scale-95"
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
