"use client";

import React from "react";
import { BlueprintNode } from "@/lib/types";

interface HoverTooltipHUDProps {
  node: BlueprintNode | null;
  pointerPos: { x: number; y: number };
}

export function HoverTooltipHUD({ node, pointerPos }: HoverTooltipHUDProps) {
  if (!node) return null;

  return (
    <div
      style={{
        left: `${pointerPos.x + 18}px`,
        top: `${pointerPos.y + 18}px`,
      }}
      className="pointer-events-none fixed z-50 min-w-[280px] max-w-[340px] rounded-xl border border-cyan-500/40 bg-slate-950/90 p-3.5 shadow-2xl backdrop-blur-xl transition-all duration-75"
    >
      <div className="flex items-start gap-3">
        {/* Symbol Crop Preview */}
        <div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-lg border border-slate-800 bg-black/80">
          <img
            src={node.crop_url}
            alt={node.id}
            className="h-full w-full object-contain"
            onError={(e) => {
              (e.currentTarget as HTMLElement).style.display = "none";
            }}
          />
        </div>

        <div className="flex-1 overflow-hidden">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-mono text-sm font-bold text-slate-100">
              {node.tag || node.id}
            </span>
            <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-cyan-400">
              {node.label.toUpperCase()}
            </span>
          </div>

          <div className="mt-0.5 text-xs text-slate-400 font-medium truncate">
            {node.subsystem_name || `Subsystem #${node.subsystem_id ?? 0}`}
          </div>
        </div>
      </div>

      {/* Specifications Grid */}
      {node.specs && Object.keys(node.specs).length > 0 && (
        <div className="mt-2.5 border-t border-slate-800/80 pt-2 text-[11px] text-slate-300">
          {Object.entries(node.specs).slice(0, 3).map(([key, val]) => (
            <div key={key} className="flex justify-between py-0.5">
              <span className="capitalize text-slate-400">{key}:</span>
              <span className="font-mono font-medium text-cyan-200">{String(val)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between border-t border-slate-800/80 pt-1.5 text-[10px] text-slate-400">
        <span>Click to lock inspector</span>
        <span className="font-mono text-cyan-400">3D Digital Twin</span>
      </div>
    </div>
  );
}
