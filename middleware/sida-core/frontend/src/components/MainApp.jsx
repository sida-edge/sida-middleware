import { useEffect, useState } from 'react';
import MainLayout from './MainLayout';

import Dashboard from './Dashboard';

import { useSystemStats } from '../hooks/useSystemStats';

export default function MainApp({ config, saveManifest, gatewayId, token, updateToken }) {
  const [activeView, setActiveView] = useState('dashboard');

  const { stats } = useSystemStats();

  const renderContent = () => {
    switch (activeView) {
      case 'dashboard':
        return <Dashboard config={config} saveManifest={saveManifest} gatewayId={gatewayId} token={token} updateToken={updateToken} />;
    //   case 'assets':
    //     return <AssetsView />;
    //   case 'services':
    //     return <ServicesView />;
    //   // Adicione os outros casos (Alarms, Settings)
      default:
        return <Dashboard config={config} saveManifest={saveManifest} gatewayId={gatewayId} token={token} updateToken={updateToken} />;
    }
  };

  return (
    <MainLayout 
      activeView={activeView} 
      onNavigate={(view) => setActiveView(view)}
      stats={stats}
    >
      {renderContent()}
    </MainLayout>
  );
}