import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Search,
  Lock,
  Clock,
  User,
  Activity,
  CheckCircle,
  Hash,
} from 'lucide-react';
import { api } from '../services/api';
import { AuditLogItem, AuditVerifyResponse } from '../types';

export const AuditTrail: React.FC = () => {
  const [events, setEvents] = useState<AuditLogItem[]>([]);
  const [verification, setVerification] = useState<AuditVerifyResponse | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<AuditLogItem | null>(null);

  useEffect(() => {
    loadAuditTrail();
  }, []);

  const loadAuditTrail = async () => {
    setLoading(true);
    try {
      const [logs, verifyRes] = await Promise.all([
        api.listAuditEvents(100),
        api.verifyAuditChain(),
      ]);
      setEvents(logs);
      setVerification(verifyRes);
      if (logs.length > 0) setSelectedEvent(logs[0]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const verifyRes = await api.verifyAuditChain();
      setVerification(verifyRes);
    } catch (e) {
      console.error(e);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Verification Status Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                TAMPER-EVIDENT AUDIT TRAIL
              </span>
              <span className="text-xs text-slate-400 font-mono">
                SHA-256 Merkle/Hash Chain
              </span>
            </div>
            <h1 className="text-xl font-bold text-white mt-1">Cryptographic Audit History</h1>
            <p className="text-xs text-slate-400">
              Every match calculation, Bob extraction, and human reconciliation decision is immutably chained
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs font-semibold text-slate-300">
                {verification?.valid ? (
                  <span className="text-emerald-400 font-mono flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4" />
                    Chain Integrity: VALID
                  </span>
                ) : (
                  <span className="text-rose-400 font-mono flex items-center gap-1.5">
                    <ShieldAlert className="h-4 w-4" />
                    Chain Broken: {verification?.broken_at}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                {verification?.events_checked} Events Verified in {verification?.verification_time_ms} ms
              </div>
            </div>

            <button
              onClick={handleVerify}
              disabled={verifying}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold shadow-md shadow-sky-500/20 transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${verifying ? 'animate-spin' : ''}`} />
              <span>Verify Cryptographic Chain</span>
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 font-mono text-sm">
          <div className="animate-spin h-6 w-6 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-2" />
          Loading audit trail and verifying hash continuity...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Cols: Events Table */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
            <div className="p-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Event Log History ({events.length} Entries)
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                Hash: SHA-256(canonical_payload + prev_hash)
              </span>
            </div>

            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 sticky top-0">
                  <tr>
                    <th className="py-2.5 px-3">Event ID</th>
                    <th className="py-2.5 px-3">Action</th>
                    <th className="py-2.5 px-3">Entity</th>
                    <th className="py-2.5 px-3">User & Role</th>
                    <th className="py-2.5 px-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {events.map((ev) => {
                    const isSelected = selectedEvent?.id === ev.id;
                    return (
                      <tr
                        key={ev.id}
                        onClick={() => setSelectedEvent(ev)}
                        className={`cursor-pointer transition ${
                          isSelected ? 'bg-sky-500/10 text-sky-300' : 'hover:bg-slate-800/40 text-slate-300'
                        }`}
                      >
                        <td className="py-2.5 px-3 font-bold text-sky-400">{ev.event_id}</td>
                        <td className="py-2.5 px-3 font-sans font-medium text-slate-200">{ev.action}</td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {ev.entity_type}: {ev.entity_id}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 font-sans text-[11px]">
                          {ev.user_id} ({ev.role})
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                          {new Date(ev.timestamp).toLocaleTimeString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Col: Selected Event Hash & Payload Inspector */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Hash className="h-4 w-4 text-sky-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Cryptographic Block Inspector
              </h3>
            </div>

            {selectedEvent ? (
              <div className="space-y-3 text-xs">
                <div>
                  <div className="text-sm font-bold text-white font-mono">{selectedEvent.event_id}</div>
                  <div className="text-xs text-sky-400 font-medium mt-0.5">{selectedEvent.action}</div>
                </div>

                <div className="space-y-2 bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-mono">Current Event Hash:</span>
                    <p className="font-mono text-[10px] text-emerald-400 break-all bg-slate-900 p-1.5 rounded mt-1 border border-slate-800">
                      {selectedEvent.event_hash}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-mono">Previous Linked Hash:</span>
                    <p className="font-mono text-[10px] text-slate-400 break-all bg-slate-900 p-1.5 rounded mt-1 border border-slate-800">
                      {selectedEvent.previous_event_hash}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-mono">Payload Details:</span>
                    <pre className="font-mono text-[10px] text-slate-300 bg-slate-900 p-2 rounded mt-1 border border-slate-800 overflow-x-auto max-h-48">
                      {JSON.stringify(selectedEvent.details, null, 2)}
                    </pre>
                  </div>

                  <div className="text-[10px] text-slate-400 pt-1 flex justify-between">
                    <span>User: {selectedEvent.user_id}</span>
                    <span>{new Date(selectedEvent.timestamp).toUTCString()}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Select any event on the left to inspect its cryptographic link.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
