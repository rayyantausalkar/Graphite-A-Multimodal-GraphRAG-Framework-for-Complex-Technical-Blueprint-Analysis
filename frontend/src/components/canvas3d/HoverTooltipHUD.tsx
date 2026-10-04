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
      className="pointer-events-none fixed z-50 min-w-[280px] max-w-[340px] rounded-xl border border-[#123B3A]/20 bg-white/95 p-3.5 shadow-2xl backdrop-blur-xl text-[#101516] transition-all duration-75"
    >
      <div className="flex items-start gap-3">
        {/* Symbol Crop Preview */}
        <div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-lg border border-[#123B3A]/15 bg-[#F7F6F2] p-0.5">
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
            <span className="truncate font-mono text-sm font-bold text-[#101516]">
              {node.tag || node.id}
            </span>
            <span className="rounded bg-[#123B3A] px-1.5 py-0.5 font-mono text-[10px] font-semibold text-[#55D6BE]">
              {node.label.toUpperCase()}
            </span>
          </div>

          <div className="mt-0.5 text-xs text-[#101516]/70 font-medium truncate">
            {node.subsystem_name || `Subsystem #${node.subsystem_id ?? 0}`}
          </div>
        </div>
      </div>

      {/* Specifications Grid */}
      {node.specs && Object.keys(node.specs).length > 0 && (
        <div className="mt-2.5 border-t border-[#123B3A]/15 pt-2 text-[11px] text-[#101516]">
          {Object.entries(node.specs).slice(0, 3).map(([key, val]) => (
            <div key={key} className="flex justify-between py-0.5">
              <span className="capitalize text-[#101516]/65">{key}:</span>
              <span className="type-technical text-[#123B3A]">{String(val)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between border-t border-[#123B3A]/15 pt-1.5 text-[10px] text-[#101516]/60">
        <span>Click to lock inspector</span>
        <span className="font-mono text-[#B45309] font-semibold">2D Blueprint Twin</span>
      </div>
    </div>
  );
}
