import React from 'react';
import { TopNav, Footer } from './components/Layout';
import Dashboard from './pages/Dashboard';
import NeuralLink from './pages/NeuralLink';
import ModelRegistry from './pages/ModelRegistry';
import KeyVault from './pages/KeyVault';
import Striker from './pages/Striker';
import LiveWire from './pages/LiveWire';

type Tab = 'DASHBOARD' | 'NEURAL LINK' | 'MODEL REGISTRY' | 'KEY VAULT' | 'STRIKER' | 'LIVE WIRE';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<Tab>('DASHBOARD');

  return (
    <div className="bg-background text-on-background font-body h-screen w-screen overflow-hidden flex flex-col">
      <TopNav active={activeTab} onChange={setActiveTab} />
      <div className="flex-1 overflow-hidden">
        {activeTab === 'DASHBOARD' && <Dashboard />}
        {activeTab === 'NEURAL LINK' && <NeuralLink />}
        {activeTab === 'MODEL REGISTRY' && <ModelRegistry />}
        {activeTab === 'KEY VAULT' && <KeyVault />}
        {activeTab === 'STRIKER' && <Striker />}
        {activeTab === 'LIVE WIRE' && <LiveWire />}
      </div>
      <Footer />
    </div>
  );
};

export default App;
