"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Sparkles, Image as ImageIcon } from "lucide-react";
import { sendChatMessage } from "@/lib/api";
import { VisualCitation, BlueprintNode } from "@/lib/types";

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  visualCitations?: VisualCitation[];
  topologicalCitations?: string[];
}

interface GroundedDialoguePanelProps {
  onHighlightElements: (nodeIds: string[], edgeIds: [string, string][]) => void;
  onSelectNodeById: (nodeId: string) => void;
  quickPromptText: string | null;
  onClearQuickPrompt: () => void;
}

export function GroundedDialoguePanel({
  onHighlightElements,
  onSelectNodeById,
  quickPromptText,
  onClearQuickPrompt,
}: GroundedDialoguePanelProps) {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "### Welcome to Graphite 3D Digital Twin\nI have ingested the master Multimodal Knowledge Graph (MMKG). You can ask flow routing queries, safety isolation questions, or plant-wide architectural inquiries.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => "session_" + Math.random().toString(36).substring(2, 9));
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Handle external quick action prompts
  useEffect(() => {
    if (quickPromptText) {
      handleSend(quickPromptText);
      onClearQuickPrompt();
    }
  }, [quickPromptText]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsg: MessageItem = {
      id: `user_${Date.now()}`,
      role: "user",
      content: query,
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);

    try {
      const res = await sendChatMessage(query, sessionId);

      const assistantMsg: MessageItem = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: res.reply,
        visualCitations: res.visual_citations,
        topologicalCitations: res.topological_citations,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Highlight nodes & flow paths in 3D scene!
      if (res.highlighted_node_ids || res.highlighted_edge_ids) {
        onHighlightElements(res.highlighted_node_ids || [], res.highlighted_edge_ids || []);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: "assistant",
          content: `⚠️ Error contacting GraphRAG service: ${err.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const parseSimpleMarkdown = (md: string) => {
    const lines = md.split("\n");
    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (trimmed.startsWith("### ")) {
        return (
          <h4 key={i} className="mb-1 text-sm font-bold text-cyan-400">
            {trimmed.substring(4)}
          </h4>
        );
      }
      if (trimmed.startsWith("#### ")) {
        return (
          <h5 key={i} className="mb-1 text-xs font-semibold text-slate-300">
            {trimmed.substring(5)}
          </h5>
        );
      }
      if (trimmed.startsWith("- ")) {
        return (
          <li key={i} className="ml-4 list-disc text-xs text-slate-300 py-0.5">
            <span
              dangerouslySetInnerHTML={{
                __html: trimmed
                  .substring(2)
                  .replace(/\*\*(.*?)\*\*/g, '<strong class="text-cyan-300">$1</strong>'),
              }}
            />
          </li>
        );
      }
      if (trimmed.length === 0) return <div key={i} className="h-1.5" />;
      return (
        <p
          key={i}
          className="text-xs text-slate-200 py-0.5 leading-relaxed"
          dangerouslySetInnerHTML={{
            __html: trimmed.replace(
              /\*\*(.*?)\*\*/g,
              '<strong class="text-cyan-300">$1</strong>'
            ),
          }}
        />
      );
    });
  };

  return (
    <div className="flex h-full w-96 flex-col border-l border-slate-800/80 bg-slate-950/85 backdrop-blur-2xl">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 p-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold text-slate-100">Grounded GraphRAG</h2>
            <div className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-slate-400">MMKG 3D Copilot</span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${
              m.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`max-w-[92%] rounded-2xl p-3.5 shadow-lg ${
                m.role === "user"
                  ? "bg-gradient-to-r from-sky-600 to-cyan-600 text-white"
                  : "border border-slate-800/90 bg-slate-900/70 text-slate-200"
              }`}
            >
              <div className="space-y-0.5">{parseSimpleMarkdown(m.content)}</div>

              {/* Visual Citations Shelf */}
              {m.visualCitations && m.visualCitations.length > 0 && (
                <div className="mt-3 border-t border-slate-700/60 pt-2.5">
                  <div className="mb-1.5 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    <ImageIcon className="h-3 w-3 text-cyan-400" />
                    <span>Visual Evidence Citations ({m.visualCitations.length})</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.visualCitations.map((cit, idx) => (
                      <button
                        key={idx}
                        onClick={() => onSelectNodeById(cit.node_id)}
                        className="flex items-center gap-1.5 rounded-md border border-cyan-500/30 bg-black/50 px-2 py-1 text-[10px] font-medium text-slate-200 transition hover:border-cyan-400 hover:bg-cyan-500/10"
                      >
                        <img
                          src={cit.crop_url}
                          alt={cit.node_id}
                          className="h-3.5 w-3.5 object-contain rounded"
                          onError={(e) => {
                            (e.currentTarget as HTMLElement).style.display = "none";
                          }}
                        />
                        <span>{cit.tag || cit.node_id}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-xs text-cyan-400">
            <Sparkles className="h-4 w-4 animate-spin text-cyan-400" />
            <span>Topological reasoning & multimodal search...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Shelf */}
      <div className="flex gap-1.5 overflow-x-auto border-t border-slate-800/60 bg-slate-900/30 p-2.5">
        <button
          onClick={() => handleSend("What is downstream from pump P-101 (general13)?")}
          className="whitespace-nowrap rounded-full border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-[10px] text-slate-300 transition hover:border-cyan-400 hover:text-white"
        >
          ⚡ Downstream P-101
        </button>
        <button
          onClick={() => handleSend("How to isolate valve99 safely?")}
          className="whitespace-nowrap rounded-full border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-[10px] text-slate-300 transition hover:border-cyan-400 hover:text-white"
        >
          🛡️ Isolate Valve
        </button>
        <button
          onClick={() => handleSend("Give an overview of functional subsystems in this plant.")}
          className="whitespace-nowrap rounded-full border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-[10px] text-slate-300 transition hover:border-cyan-400 hover:text-white"
        >
          🏭 Plant Hierarchy
        </button>
      </div>

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-2 border-t border-slate-800/80 bg-slate-950 p-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about flow routes, valves, or components..."
          className="flex-1 rounded-xl border border-slate-800 bg-slate-900/90 px-3.5 py-2 text-xs text-white placeholder-slate-500 outline-none transition focus:border-cyan-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-sky-500 text-slate-950 font-bold transition hover:brightness-110 active:scale-95 disabled:opacity-40"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </form>
    </div>
  );
}
