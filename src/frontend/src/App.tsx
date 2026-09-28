import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { User, Incident } from './types';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Reconciliation } from './pages/Reconciliation';
import { AMRecords } from './pages/AMRecords';
import { PMRecords } from './pages/PMRecords';
import { EvidenceGraph } from './pages/EvidenceGraph';
import { BobCopilot } from './pages/BobCopilot';
import { Reports } from './pages/Reports';
import { AuditTrail } from './pages/AuditTrail';
import { Evaluation } from './pages/Evaluation';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);
  const [selectedPmNumber, setSelectedPmNumber] = useState<string>('PM-017');
  const [selectedMatchId, setSelectedMatchId] = useState<string>('');
  const [initializing, setInitializing] = useState<boolean>(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = api.getToken();
    if (token) {
      try {
        const user = await api.getMe();
        setCurrentUser(user);
        await loadIncidents();
      } catch (e) {
        api.setToken(null);
        setCurrentUser(null);
      }
    }
    setInitializing(false);
  };

  const loadIncidents = async () => {
    try {
      const incList = await api.getIncidents();
      setIncidents(incList);
      if (incList.length > 0) {
        setActiveIncident(incList[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLoginSuccess = async (user: User) => {
    setCurrentUser(user);
    await loadIncidents();
  };

  const handleLogout = () => {
    api.setToken(null);
    setCurrentUser(null);
  };

  const handleNavigate = (tab: string, param?: string) => {
    if (tab === 'reconciliation' && param) {
      setSelectedPmNumber(param);
    }
    setCurrentTab(tab);
  };

  const handleNavigateToGraph = (matchId: string) => {
    setSelectedMatchId(matchId);
    setCurrentTab('evidence');
  };

  if (initializing) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 font-mono text-sm">
        <div className="animate-spin h-6 w-6 border-2 border-sky-500 border-t-transparent rounded-full mr-3" />
        Initializing DVI-Bridge Command Platform...
      </div>
    );
  }

  if (!currentUser) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      {/* Top Command Navbar */}
      <Navbar
        currentUser={currentUser}
        onLogout={handleLogout}
        activeIncident={activeIncident}
        onSelectIncident={(inc) => setActiveIncident(inc)}
        incidents={incidents}
      />

      {/* Main App Body */}
      <div className="flex flex-1">
        {/* Left Navigation Sidebar */}
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

        {/* Content View Container */}
        <main className="flex-1 p-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
          <div className="max-w-7xl mx-auto">
            {currentTab === 'dashboard' && (
              <Dashboard
                activeIncident={activeIncident}
                onNavigate={handleNavigate}
              />
            )}
            {currentTab === 'reconciliation' && (
              <Reconciliation
                activeIncident={activeIncident}
                initialPmBodyNumber={selectedPmNumber}
                onNavigateToGraph={handleNavigateToGraph}
              />
            )}
            {currentTab === 'am' && (
              <AMRecords activeIncident={activeIncident} />
            )}
            {currentTab === 'pm' && (
              <PMRecords
                activeIncident={activeIncident}
                onNavigateToReconciliation={(pmNumber) => handleNavigate('reconciliation', pmNumber)}
              />
            )}
            {currentTab === 'evidence' && (
              <EvidenceGraph
                activeIncident={activeIncident}
                matchId={selectedMatchId}
              />
            )}
            {currentTab === 'copilot' && (
              <BobCopilot
                activeIncident={activeIncident}
                onNavigateToReconciliation={(pmNumber) => handleNavigate('reconciliation', pmNumber)}
              />
            )}
            {currentTab === 'reports' && (
              <Reports activeIncident={activeIncident} />
            )}
            {currentTab === 'audit' && <AuditTrail />}
            {currentTab === 'evaluation' && <Evaluation />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
