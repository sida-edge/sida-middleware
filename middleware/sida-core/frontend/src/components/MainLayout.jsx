import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function MainLayout({ children, activeView, onNavigate, stats }) {
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#133326' }}>
      
      <div style={{ width: '260px', display: 'flex', flexDirection: 'column' }}>
         <Sidebar activeView={activeView} onNavigate={onNavigate} stats={stats} />
      </div>

      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column', 
        backgroundColor: '#F4F4F5', 
        borderTopLeftRadius: '16px',
        overflow: 'hidden' 
      }}>
        
        <header style={{ height: '70px', backgroundColor: '#FFFFFF' }}>
           <Header />
        </header>

        <main style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
          {children}
        </main>

      </div>
    </div>
    );
}