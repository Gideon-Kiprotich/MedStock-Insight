import { ScenarioAnalysisPage } from './pages/ScenarioAnalysisPage';
import { DecisionAnalyticsPage } from './pages/DecisionAnalyticsPage';
import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { MedicinesPage } from './pages/MedicinesPage';
import { MedicineDetailPage } from './pages/MedicineDetailPage';
import { StockoutRiskPage } from './pages/StockoutRiskPage';
import { RedistributionPage } from './pages/RedistributionPage';
import { TransferTrackingPage } from './pages/TransferTrackingPage';
import { InventoryPage } from './pages/InventoryPage';
import { ForecastsPage } from './pages/ForecastsPage';
import { FacilitiesPage } from './pages/FacilitiesPage';
import { UsersPage } from './pages/UsersPage';
import { AuditTrailPage } from './pages/AuditTrailPage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { DemonstrationBanner } from './components/common/DemonstrationBanner';

const MainApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [selectedMedicineId, setSelectedMedicineId] = useState<string | null>(null);
  const [transferTargetRecId, setTransferTargetRecId] = useState<string | undefined>(undefined);
  const [menuOpen, setMenuOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs text-slate-400 font-medium">Initializing MedStock Insight Authority Shell...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const handleNavigate = (tab: string, param?: string) => {
    setMenuOpen(false);
    if (tab === 'medicine-detail' && param) {
      setSelectedMedicineId(param);
      setCurrentTab('medicine-detail');
    } else if (tab === 'transfers' && param) {
      setTransferTargetRecId(param);
      setCurrentTab('transfers');
    } else {
      setCurrentTab(tab);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans antialiased">
      <DemonstrationBanner />
      <Navbar onMenuToggle={() => setMenuOpen((open) => !open)} />

      <div className="flex flex-1 min-h-0">
        {menuOpen && <button className="fixed inset-0 bg-slate-950/50 z-30 lg:hidden" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
        <div className={`${menuOpen ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 top-16 z-40 transition-transform lg:sticky lg:top-16 lg:translate-x-0 lg:h-[calc(100vh-4rem)]`}>
          <Sidebar currentTab={currentTab} onTabChange={handleNavigate} />
        </div>

        <main className="workspace min-w-0 flex-1 bg-slate-50">
          {currentTab === 'dashboard' && <DashboardPage onNavigate={handleNavigate} />}

          {currentTab === 'inventory' && <InventoryPage />}

          {currentTab === 'medicines' && (
            <MedicinesPage
              onSelectMedicine={(id) => {
                setSelectedMedicineId(id);
                setCurrentTab('medicine-detail');
              }}
            />
          )}

          {currentTab === 'medicine-detail' && selectedMedicineId && (
            <MedicineDetailPage
              medicineId={selectedMedicineId}
              onBack={() => setCurrentTab('medicines')}
            />
          )}

          {currentTab === 'forecasts' && <ForecastsPage />}

          {currentTab === 'scenario' && <ScenarioAnalysisPage />}

          {currentTab === 'risk' && <StockoutRiskPage />}

          {currentTab === 'redistribution' && (
            <RedistributionPage
              onNavigateToTransfer={(recId) => handleNavigate('transfers', recId)}
            />
          )}

          {currentTab === 'transfers' && (
            <TransferTrackingPage initialRecommendationId={transferTargetRecId} />
          )}

          {currentTab === 'facilities' && <FacilitiesPage />}

          {currentTab === 'audit' && <AuditTrailPage />}

          {currentTab === 'consumption' && (
            <PlaceholderPage
              title="Consumption Logging"
              description="Historical consumption logging and dispensing ledger module. Facility transaction records are accessible under the Inventory workspace."
            />
          )}

          {currentTab === 'reports' && <DecisionAnalyticsPage />}

          {currentTab === 'users' && <UsersPage />}

          {currentTab === 'settings' && (
            <PlaceholderPage
              title="System Settings"
              description="Global environment policies, security keys, and database connectivity settings."
            />
          )}
        </main>
      </div>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
