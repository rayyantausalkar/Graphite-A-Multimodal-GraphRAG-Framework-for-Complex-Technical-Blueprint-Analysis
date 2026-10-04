"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, Sparkles, Image as ImageIcon } from "lucide-react";
import { sendChatMessage } from "@/lib/api";
import { VisualCitation } from "@/lib/types";

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
        "### Welcome to Graphite Blueprint Intelligence\nI have ingested the master Multimodal Knowledge Graph (MMKG). You can ask flow routing queries, safety isolation questions, or plant-wide architectural inquiries.",
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
          <h4 key={i} className="mb-1 font-brand text-sm font-semibold text-[#123B3A]">
            {trimmed.substring(4)}
          </h4>
        );
      }
      if (trimmed.startsWith("#### ")) {
        return (
          <h5 key={i} className="mb-1 font-brand text-xs font-semibold text-[#B45309]">
            {trimmed.substring(5)}
          </h5>
        );
      }
      if (trimmed.startsWith("- ")) {
        return (
          <li key={i} className="ml-4 list-disc font-body text-[14px] text-[#101516] py-0.5">
            <span
              dangerouslySetInnerHTML={{
                __html: trimmed
                  .substring(2)
                  .replace(/\*\*(.*?)\*\*/g, '<strong class="text-[#123B3A] font-semibold">$1</strong>'),
              }}
            />
          </li>
        );
      }
      if (trimmed.length === 0) return <div key={i} className="h-1.5" />;
      return (
        <p
          key={i}
          className="font-body text-[14px] text-[#101516] py-0.5 leading-relaxed"
          dangerouslySetInnerHTML={{
            __html: trimmed.replace(
              /\*\*(.*?)\*\*/g,
              '<strong class="text-[#123B3A] font-semibold">$1</strong>'
            ),
          }}
        />
      );
    });
  };

  return (
    <div className="flex h-full w-96 flex-col border-l border-[#123B3A]/15 bg-white/95 text-[#101516] backdrop-blur-2xl">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-[#123B3A]/15 p-4">
        <div className="flex items-center gap-2.5">
          <img
            src="/logo-emblem.png"
            alt="Graphite Copilot"
            className="h-8 w-8 rounded-lg border border-[#123B3A]/15 object-contain shadow-xs"
          />
          <div>
            <h2 className="font-brand text-[20px] font-semibold leading-tight text-[#101516]">
              Grounded GraphRAG
            </h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[#55D6BE]" />
              <span className="type-technical text-[#101516]/60">MMKG Blueprint Copilot</span>
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
              className={`max-w-[92%] rounded-2xl p-3.5 shadow-sm ${
                m.role === "user"
                  ? "bg-[#123B3A] border border-[#123B3A] text-white"
                  : "border border-[#123B3A]/15 bg-[#F7F6F2] text-[#101516]"
              }`}
            >
              <div className="space-y-0.5">{parseSimpleMarkdown(m.content)}</div>

              {/* Visual Citations Shelf */}
              {m.visualCitations && m.visualCitations.length > 0 && (
                <div className="mt-3 border-t border-[#123B3A]/15 pt-2.5">
                  <div className="mb-1.5 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-[#B45309]">
                    <ImageIcon className="h-3 w-3 text-[#B45309]" />
                    <span>Visual Evidence Citations ({m.visualCitations.length})</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.visualCitations.map((cit, idx) => (
                      <button
                        key={idx}
                        onClick={() => onSelectNodeById(cit.node_id)}
                        className="flex items-center gap-1.5 rounded-md border border-[#123B3A]/15 bg-white px-2 py-1 text-[10px] font-medium text-[#101516] transition hover:border-[#123B3A] hover:bg-[#F7F6F2]"
                      >
                        <img
                          src={cit.crop_url}
                          alt={cit.node_id}
                          className="h-3.5 w-3.5 object-contain rounded"
                          onError={(e) => {
                            (e.currentTarget as HTMLElement).style.display = "none";
                          }}
                        />
                        <span className="font-mono text-[11px] font-semibold">{cit.tag || cit.node_id}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 rounded-xl border border-[#123B3A]/15 bg-[#F7F6F2] p-3 text-xs text-[#123B3A]">
            <Sparkles className="h-4 w-4 animate-spin text-[#123B3A]" />
            <span>Topological reasoning & multimodal search...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Shelf */}
      <div className="flex gap-1.5 overflow-x-auto border-t border-[#123B3A]/15 bg-[#F7F6F2] p-2.5">
        <button
          onClick={() => handleSend("What is downstream from pump P-101 (general13)?")}
          className="whitespace-nowrap rounded-full border border-[#123B3A]/20 bg-white px-2.5 py-1 text-[10px] font-medium text-[#101516] transition hover:border-[#123B3A] hover:bg-[#123B3A] hover:text-white"
        >
          ⚡ Downstream P-101
        </button>
        <button
          onClick={() => handleSend("How to isolate valve99 safely?")}
          className="whitespace-nowrap rounded-full border border-[#E5B93F] bg-white px-2.5 py-1 text-[10px] font-medium text-[#B45309] transition hover:bg-[#E5B93F] hover:text-white"
        >
          🛡️ Isolate Valve
        </button>
        <button
          onClick={() => handleSend("Give an overview of functional subsystems in this plant.")}
          className="whitespace-nowrap rounded-full border border-[#123B3A]/20 bg-white px-2.5 py-1 text-[10px] font-medium text-[#101516] transition hover:border-[#123B3A] hover:bg-[#123B3A] hover:text-white"
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
        className="flex items-center gap-2 border-t border-[#123B3A]/15 bg-white p-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about flow routes, valves, or components..."
          className="flex-1 rounded-xl border border-[#123B3A]/20 bg-[#F7F6F2] px-3.5 py-2 text-xs text-[#101516] placeholder-[#101516]/45 outline-none transition focus:border-[#123B3A]"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#123B3A] text-white font-bold transition hover:bg-[#1D4F4D] active:scale-95 disabled:opacity-40"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </form>
    </div>
  );
}
