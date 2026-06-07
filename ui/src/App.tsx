import React, { Suspense } from 'react';
import { Sidebar } from './components/Sidebar';
import { Footer } from './components/Layout';
import Dashboard from './pages/Dashboard';
import NeuralLink from './pages/NeuralLink';
import LiveWire from './pages/LiveWire';

// Secondary pages — code split to keep main bundle lean
const PlanReview = React.lazy(() => import('./pages/PlanReview'));
const History = React.lazy(() => import('./pages/History'));
const Stress = React.lazy(() => import('./pages/Stress'));
const ModelRegistry = React.lazy(() => import('./pages/ModelRegistry'));
const KeyVault = React.lazy(() => import('./pages/KeyVault'));
const Striker = React.lazy(() => import('./pages/Striker'));
const Config = React.lazy(() => import('./pages/Config'));

import type { Tab } from './types';

const PageFallback: React.FC = () => (
  <div className="h-full w-full flex items-center justify-center text-outline text-sm">
    <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
    Loading...
  </div>
);

const App: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<Tab>('DASHBOARD');

  return (
    <div className="bg-background text-on-background font-body h-screen w-screen overflow-hidden flex">
      <Sidebar active={activeTab} onChange={setActiveTab} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-hidden">
          <Suspense fallback={<PageFallback />}>
            {activeTab === 'DASHBOARD' && <Dashboard />}
            {activeTab === 'NEURAL LINK' && <NeuralLink />}
            {activeTab === 'LIVE WIRE' && <LiveWire />}
            {activeTab === 'PLAN REVIEW' && <PlanReview />}
            {activeTab === 'HISTORY' && <History />}
            {activeTab === 'STRESS' && <Stress />}
            {activeTab === 'MODEL REGISTRY' && <ModelRegistry />}
            {activeTab === 'KEY VAULT' && <KeyVault />}
            {activeTab === 'STRIKER' && <Striker />}
            {activeTab === 'CONFIG' && <Config />}
          </Suspense>
        </div>
        <Footer />
      </div>
    </div>
  );
};

export default App;
