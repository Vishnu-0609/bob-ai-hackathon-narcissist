import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Terminal,
  ArrowRight,
  User,
  ShieldCheck,
  HelpCircle,
  Clock,
  ExternalLink,
  Eye,
} from 'lucide-react';
import { api } from '../services/api';
import { CopilotMessage, Incident } from '../types';
import { CaseDetailsModal } from '../components/CaseDetailsModal';

interface BobCopilotProps {
  activeIncident: Incident | null;
  onNavigateToReconciliation: (bodyNumber: string, amId?: string) => void;
}

export const BobCopilot: React.FC<BobCopilotProps> = ({
  activeIncident,
  onNavigateToReconciliation,
}) => {
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      id: 'welcome',
      sender: 'bob',
      text: (
        "Hello Coordinator. I am your **IBM Bob DVI Coordinator Copilot**.\n\n" +
        "I can help you analyze forensic candidate matches, explain deterministic scores, identify missing evidence, and search cases by visual descriptions (clothing, jewellery, watches, tattoos, scars).\n\n" +
        "**How can I assist your team today?**"
      ),
      timestamp: new Date().toLocaleTimeString(),
      suggested_actions: [
        'a person with Analog wristwatch with a gold-colored circular case with grey shoe',
        'Why is AM-042 ranked first for PM-017?',
        'Show top candidates for PM-017',
        'Show cases with conflicting scar or tattoo information',
      ],
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [inspectedCaseId, setInspectedCaseId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (queryToSend = inputQuery) => {
    if (!queryToSend.trim() || !activeIncident) return;

    // Check if the user clicked an 'Open AM-xxx' or 'Open PM-xxx' action
    const openMatch = queryToSend.match(/^Open\s+(AM-\d+|PM-\d+|[a-f0-9\-]{36})/i);
    if (openMatch) {
      setInspectedCaseId(openMatch[1]);
      return;
    }

    const userMsg: CopilotMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: queryToSend,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await api.chatCopilot({
        query: queryToSend,
        incident_id: activeIncident.id,
      });

      const bobMsg: CopilotMessage = {
        id: `bob-${Date.now()}`,
        sender: 'bob',
        text: res.response,
        timestamp: new Date().toLocaleTimeString(),
        tools_used: res.tools_used,
        suggested_actions: res.suggested_actions,
      };
      setMessages((prev) => [...prev, bobMsg]);
    } catch (err: any) {
      const errorMsg: CopilotMessage = {
        id: `err-${Date.now()}`,
        sender: 'bob',
        text: `Error processing query: ${err.message}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Parses Markdown content into interactive components with clickable Case IDs,
   * tables, bold highlights, and action buttons.
   */
  const renderMessageContent = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];

    const flushTable = (key: string) => {
      if (tableRows.length > 0) {
        const [header, , ...body] = tableRows;
        elements.push(
          <div key={key} className="overflow-x-auto my-2 rounded-xl border border-slate-800 bg-slate-950/80 shadow-md">
            <table className="w-full text-left text-[11px] border-collapse">
              <thead>
                <tr className="bg-slate-900 border-b border-slate-800 text-slate-300 font-bold uppercase tracking-wider">
                  {header?.map((h, hi) => (
                    <th key={hi} className="p-2.5 font-semibold">
                      {h.trim()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {body.map((row, ri) => (
                  <tr key={ri} className="hover:bg-slate-900/60 transition">
                    {row.map((cell, ci) => {
                      const trimmed = cell.trim();
                      const caseMatch = trimmed.match(/\*\*(AM-\d+|PM-\d+|[a-f0-9\-]{36})\*\*/i) || trimmed.match(/^(AM-\d+|PM-\d+|[a-f0-9\-]{36})$/i);
                      return (
                        <td key={ci} className="p-2.5 font-mono text-slate-200">
                          {caseMatch ? (
                            <button
                              type="button"
                              onClick={() => setInspectedCaseId(caseMatch[1])}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 font-bold text-xs transition shadow-sm"
                              title={`Inspect full forensic record for ${caseMatch[1]}`}
                            >
                              <span>{caseMatch[1]}</span>
                              <Eye className="h-3 w-3" />
                            </button>
                          ) : (
                            formatInlineText(trimmed)
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
      }
      inTable = false;
    };

    lines.forEach((line, idx) => {
      const isTableRow = line.trim().startsWith('|') && line.trim().endsWith('|');

      if (isTableRow) {
        inTable = true;
        const cells = line
          .trim()
          .slice(1, -1)
          .split('|');
        tableRows.push(cells);
      } else {
        if (inTable) {
          flushTable(`table-${idx}`);
        }

        if (line.startsWith('### ')) {
          elements.push(
            <h4 key={idx} className="text-xs font-bold text-sky-400 uppercase tracking-wider mt-3 mb-1">
              {line.replace('### ', '')}
            </h4>
          );
        } else if (line.startsWith('> ')) {
          elements.push(
            <div key={idx} className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-[11px] text-sky-300 italic my-1">
              {formatInlineText(line.replace('> ', ''))}
            </div>
          );
        } else if (line.trim()) {
          elements.push(
            <p key={idx} className="leading-relaxed">
              {formatInlineText(line)}
            </p>
          );
        } else {
          elements.push(<div key={idx} className="h-1" />);
        }
      }
    });

    if (inTable) {
      flushTable(`table-end`);
    }

    return elements;
  };

  /**
   * Highlights bold words and makes Case Identifiers directly clickable.
   */
  const formatInlineText = (str: string) => {
    const parts = str.split(/(\*\*[^*]+\*\*|`(?:AM-\d+|PM-\d+|[a-f0-9\-]{36})`|AM-\d+|PM-\d+)/g);
    return parts.map((part, i) => {
      const cleanCase = part.replace(/\*\*|`/g, '').trim();
      if (/^(AM-\d+|PM-\d+|[a-f0-9\-]{36})$/i.test(cleanCase)) {
        const isAM = cleanCase.toUpperCase().startsWith('AM');
        return (
          <button
            key={i}
            type="button"
            onClick={() => setInspectedCaseId(cleanCase)}
            className={`inline-flex items-center gap-1 font-mono font-bold px-1.5 py-0.5 rounded text-[11px] mx-0.5 border transition cursor-pointer ${
              isAM
                ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-500/40'
                : 'bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border-sky-500/40'
            }`}
            title={`Click to inspect case details for ${cleanCase}`}
          >
            <span>{cleanCase}</span>
            <ExternalLink className="h-2.5 w-2.5 opacity-80" />
          </button>
        );
      }

      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-bold text-white">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={i} className="font-mono text-sky-300 bg-slate-900 px-1 py-0.5 rounded">{part.slice(1, -1)}</code>;
      }
      if (part.startsWith('*') && part.endsWith('*')) {
        return <em key={i} className="text-slate-300">{part.slice(1, -1)}</em>;
      }
      return part;
    });
  };

  return (
    <div className="h-[calc(100vh-7.5rem)] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
      {/* Copilot Header */}
      <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-sky-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white">IBM Bob DVI Coordinator Copilot</h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Safe Tool Execution
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Strictly grounded in factual comparison data · Zero Raw SQL Execution</p>
          </div>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 max-w-3xl ${
              msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
            }`}
          >
            {/* Avatar */}
            <div
              className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 font-mono text-xs font-bold ${
                msg.sender === 'user'
                  ? 'bg-sky-600 text-white'
                  : 'bg-indigo-600 text-white'
              }`}
            >
              {msg.sender === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`rounded-2xl p-4 text-xs leading-relaxed space-y-2 shadow-lg ${
                msg.sender === 'user'
                  ? 'bg-sky-600 text-white font-medium'
                  : 'bg-slate-950 border border-slate-800 text-slate-200'
              }`}
            >
              {msg.sender === 'user' ? (
                <div className="whitespace-pre-line">{msg.text}</div>
              ) : (
                <div className="space-y-1.5">{renderMessageContent(msg.text)}</div>
              )}

              {/* Tools execution pill */}
              {msg.tools_used && msg.tools_used.length > 0 && (
                <div className="pt-2 border-t border-slate-800 space-y-1">
                  <div className="text-[10px] font-mono font-bold text-sky-400 flex items-center gap-1">
                    <Terminal className="h-3 w-3" />
                    <span>FastAPI Controlled Tool Executed:</span>
                  </div>
                  {msg.tools_used.map((t, idx) => (
                    <div key={idx} className="bg-slate-900 p-2 rounded border border-slate-800 font-mono text-[10px] text-slate-300">
                      <code>{t.tool}({JSON.stringify(t.parameters)})</code>
                    </div>
                  ))}
                </div>
              )}

              {/* Suggested Follow-ups */}
              {msg.suggested_actions && (
                <div className="pt-2 flex flex-wrap gap-1.5">
                  {msg.suggested_actions.map((act, idx) => {
                    const openCaseMatch = act.match(/^Open\s+(AM-\d+|PM-\d+|[a-f0-9\-]{36})/i);
                    return (
                      <button
                        key={idx}
                        onClick={() => {
                          if (openCaseMatch) {
                            setInspectedCaseId(openCaseMatch[1]);
                          } else {
                            handleSend(act);
                          }
                        }}
                        className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-850 text-sky-300 border border-slate-800 hover:border-slate-700 text-[11px] font-medium transition flex items-center gap-1"
                      >
                        {openCaseMatch ? <Eye className="h-3 w-3 text-sky-400" /> : <Sparkles className="h-3 w-3 text-sky-400" />}
                        <span>{act}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="text-[9px] text-slate-400 text-right">{msg.timestamp}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 max-w-xl mr-auto">
            <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 text-xs text-slate-400 flex items-center gap-2">
              <div className="animate-spin h-3.5 w-3.5 border-2 border-indigo-500 border-t-transparent rounded-full" />
              <span>IBM Bob Agent querying case data and synthesizing rationale...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-3 bg-slate-950 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask IBM Bob: 'a person with Analog wristwatch with gold case', 'Why is AM-042 ranked first?', 'Show PM-017 candidates'..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          <button
            type="submit"
            disabled={loading || !inputQuery.trim()}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-sky-500/20 disabled:opacity-50 transition flex items-center gap-1.5"
          >
            <Send className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Ask Copilot</span>
          </button>
        </form>
      </div>

      {/* Detailed Case Inspector Modal */}
      {inspectedCaseId && (
        <CaseDetailsModal
          caseId={inspectedCaseId}
          onClose={() => setInspectedCaseId(null)}
          onNavigateToReconciliation={onNavigateToReconciliation}
        />
      )}
    </div>
  );
};
