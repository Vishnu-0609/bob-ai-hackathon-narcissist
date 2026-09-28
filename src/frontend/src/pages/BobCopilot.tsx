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
} from 'lucide-react';
import { api } from '../services/api';
import { CopilotMessage, Incident } from '../types';

interface BobCopilotProps {
  activeIncident: Incident | null;
  onNavigateToReconciliation: (bodyNumber: string) => void;
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
        "I can help you analyze forensic candidate matches, explain deterministic scores, identify missing evidence, and safely query cases without executing raw SQL.\n\n" +
        "**How can I assist your team today?**"
      ),
      timestamp: new Date().toLocaleTimeString(),
      suggested_actions: [
        'Why is AM-042 ranked first for PM-017?',
        'Show top candidates for PM-017',
        'Show cases with conflicting scar or tattoo information',
        'Filter unidentified male bodies',
      ],
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (queryToSend = inputQuery) => {
    if (!queryToSend.trim() || !activeIncident) return;

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
              <div className="whitespace-pre-line">{msg.text}</div>

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
                  {msg.suggested_actions.map((act, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(act)}
                      className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-850 text-sky-300 border border-slate-800 hover:border-slate-700 text-[11px] font-medium transition flex items-center gap-1"
                    >
                      <Sparkles className="h-3 w-3 text-sky-400" />
                      <span>{act}</span>
                    </button>
                  ))}
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
            placeholder="Ask IBM Bob: 'Why is AM-042 ranked first?', 'Show candidates for PM-017', 'Explain contradictions'..."
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
    </div>
  );
};
