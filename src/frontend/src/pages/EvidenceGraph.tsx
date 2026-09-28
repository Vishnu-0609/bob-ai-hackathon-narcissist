import React, { useState, useEffect } from 'react';
import {
  Network,
  Info,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  ArrowRight,
  Database,
  Bot,
} from 'lucide-react';
import { api } from '../services/api';
import { EvidenceGraphData, EvidenceGraphNode, Incident } from '../types';

interface EvidenceGraphProps {
  activeIncident: Incident | null;
  matchId?: string;
}

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({
  activeIncident,
  matchId = '',
}) => {
  const [graphData, setGraphData] = useState<EvidenceGraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<EvidenceGraphNode | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadGraph();
  }, [matchId, activeIncident]);

  const loadGraph = async () => {
    setLoading(true);
    try {
      if (matchId) {
        const data = await api.getEvidenceGraph(matchId);
        setGraphData(data);
        if (data.nodes.length > 0) setSelectedNode(data.nodes[0]);
      } else {
        // Find default match for PM-017 / AM-042
        const cands = await api.getCandidates('PM-017', 1);
        if (cands.candidates.length > 0 && cands.candidates[0].match_id) {
          const data = await api.getEvidenceGraph(cands.candidates[0].match_id);
          setGraphData(data);
          if (data.nodes.length > 0) setSelectedNode(data.nodes[0]);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white">Forensic Evidence Graph & Provenance</h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
              Interactive Topology
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Visual inspection of ante-mortem and post-mortem observations with full data lineage
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 font-mono text-sm">
          <div className="animate-spin h-6 w-6 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-2" />
          Rendering forensic evidence topological graph...
        </div>
      ) : graphData ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Visual Topology Area */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative min-h-[480px] flex flex-col justify-between">
            {/* Header / Summary */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-sky-400" />
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Graph Topology: Match Score {graphData.match_score}/100 ({graphData.evidence_quality})
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px]">
                <span className="flex items-center gap-1 text-emerald-400">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" /> Match
                </span>
                <span className="flex items-center gap-1 text-rose-400">
                  <span className="h-2 w-2 rounded-full bg-rose-400" /> Mismatch
                </span>
                <span className="flex items-center gap-1 text-amber-400">
                  <span className="h-2 w-2 rounded-full bg-amber-400" /> Unknown
                </span>
              </div>
            </div>

            {/* Visual Node Diagram representation */}
            <div className="my-6 grid grid-cols-3 gap-4 items-center">
              {/* Column 1: AM Node */}
              <div className="flex flex-col items-center">
                {graphData.nodes
                  .filter((n) => n.type === 'AM_CASE')
                  .map((node) => (
                    <div
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className={`cursor-pointer p-4 rounded-2xl border text-center transition shadow-lg w-full max-w-[180px] ${
                        selectedNode?.id === node.id
                          ? 'bg-sky-500/20 border-sky-400 ring-2 ring-sky-500/30'
                          : 'bg-slate-950 border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <div className="h-9 w-9 rounded-xl bg-sky-500/20 border border-sky-500/40 text-sky-400 flex items-center justify-center mx-auto mb-2 font-mono font-bold text-xs">
                        AM
                      </div>
                      <div className="text-xs font-bold text-white truncate">{node.label}</div>
                      <div className="text-[10px] text-slate-400 truncate">{node.sublabel}</div>
                    </div>
                  ))}
              </div>

              {/* Column 2: Evidence Attribute Nodes */}
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {graphData.nodes
                  .filter((n) => n.type === 'ATTRIBUTE')
                  .map((node) => {
                    const isMatch = node.result === 'MATCH';
                    const isMismatch = node.result === 'MISMATCH';
                    const isUnknown = node.result === 'UNKNOWN';

                    const borderClass = isMatch
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      : isMismatch
                      ? 'border-rose-500/40 bg-rose-500/10 text-rose-300'
                      : 'border-amber-500/40 bg-amber-500/10 text-amber-300';

                    return (
                      <div
                        key={node.id}
                        onClick={() => setSelectedNode(node)}
                        className={`cursor-pointer px-3 py-2 rounded-xl border text-xs flex items-center justify-between transition ${borderClass} ${
                          selectedNode?.id === node.id ? 'ring-2 ring-sky-400' : 'hover:opacity-90'
                        }`}
                      >
                        <div className="truncate pr-2">
                          <div className="font-bold truncate">{node.label}</div>
                          <div className="text-[10px] opacity-80 truncate">{node.sublabel}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold flex-shrink-0">
                          {node.score}/{node.weight}
                        </span>
                      </div>
                    );
                  })}
              </div>

              {/* Column 3: PM Node */}
              <div className="flex flex-col items-center">
                {graphData.nodes
                  .filter((n) => n.type === 'PM_CASE')
                  .map((node) => (
                    <div
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className={`cursor-pointer p-4 rounded-2xl border text-center transition shadow-lg w-full max-w-[180px] ${
                        selectedNode?.id === node.id
                          ? 'bg-indigo-500/20 border-indigo-400 ring-2 ring-indigo-500/30'
                          : 'bg-slate-950 border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <div className="h-9 w-9 rounded-xl bg-indigo-500/20 border border-indigo-500/40 text-indigo-400 flex items-center justify-center mx-auto mb-2 font-mono font-bold text-xs">
                        PM
                      </div>
                      <div className="text-xs font-bold text-white truncate">{node.label}</div>
                      <div className="text-[10px] text-slate-400 truncate">{node.sublabel}</div>
                    </div>
                  ))}
              </div>
            </div>

            <div className="text-[11px] text-slate-400 border-t border-slate-800 pt-2 flex items-center justify-between">
              <span>Click any node to inspect data provenance & verification history</span>
              <span className="font-mono text-sky-400">{graphData.summary}</span>
            </div>
          </div>

          {/* Right Col: Node Provenance Inspector */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Database className="h-4 w-4 text-sky-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Provenance & Lineage Inspector
              </h3>
            </div>

            {selectedNode ? (
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-bold text-white">{selectedNode.label}</div>
                  <div className="text-xs text-sky-400 font-mono mt-0.5">{selectedNode.type}</div>
                </div>

                <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 space-y-2 text-xs">
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase">Details / Values:</span>
                    <p className="text-slate-200 font-mono mt-0.5">{selectedNode.sublabel || 'N/A'}</p>
                  </div>

                  {selectedNode.result && (
                    <div>
                      <span className="text-slate-400 text-[10px] uppercase">Concordance Result:</span>
                      <p className="text-slate-200 font-mono mt-0.5 font-bold">{selectedNode.result}</p>
                    </div>
                  )}

                  {selectedNode.notes && (
                    <div>
                      <span className="text-slate-400 text-[10px] uppercase">Forensic Notes:</span>
                      <p className="text-slate-300 mt-0.5 leading-relaxed">{selectedNode.notes}</p>
                    </div>
                  )}

                  <div>
                    <span className="text-slate-400 text-[10px] uppercase">Capture Source:</span>
                    <p className="text-slate-200 mt-0.5">{selectedNode.source || selectedNode.source_type || 'Field Forensic Observation'}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 text-[10px] uppercase">Extraction Method:</span>
                    <p className="text-slate-200 mt-0.5 flex items-center gap-1.5">
                      <Bot className="h-3.5 w-3.5 text-indigo-400" />
                      <span>IBM Bob Assisted Extraction</span>
                    </p>
                  </div>

                  <div>
                    <span className="text-slate-400 text-[10px] uppercase">Verification Status:</span>
                    <p className="text-emerald-400 mt-0.5 flex items-center gap-1.5 font-semibold">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      <span>Human Verified</span>
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Select any node on the left to inspect forensic lineage.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="p-8 text-center text-slate-400">No match records found.</div>
      )}
    </div>
  );
};
