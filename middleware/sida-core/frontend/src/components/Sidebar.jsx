import React from 'react';

export default function Sidebar({ 
  activeView, 
  onNavigate, 
  stats = { cpu: '0.0', ram: '0.0', isConnected: false },  
}) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'assets', label: 'Assets' },
    { id: 'services', label: 'Services' },
    { id: 'alarms', label: 'Alarms' },
    { id: 'settings', label: 'Settings' }
  ];

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      justifyContent: 'space-between',
      height: '100%', 
      paddingTop: '24px'
    }}>
      
      <div>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '0 20px', marginBottom: '40px' }}>
          <div style={{ 
            width: '32px', height: '32px', 
            border: '2px solid #2d6a4f', 
            borderRadius: '6px', 
            display: 'flex', alignItems: 'center', justifyContent: 'center' 
          }}>
            <div style={{ width: '12px', height: '12px', border: '2px solid #2d6a4f', borderRadius: '3px' }}></div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#ffffff', lineHeight: '1' }}>
              SIDA
            </span>
            <span style={{ fontSize: '0.65rem', color: '#74c69d', marginTop: '4px', letterSpacing: '1px', fontWeight: '500' }}>
              MIDDLEWARE
            </span>
          </div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '0 16px' }}>
          {menuItems.map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '15px',
                  padding: '12px 16px',
                  width: '100%',
                  backgroundColor: isActive ? '#2d6a4f' : 'transparent',
                  color: isActive ? '#ffffff' : '#9ca3af',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.95rem',
                  fontWeight: isActive ? '600' : '400',
                  transition: 'all 0.2s',
                  position: 'relative',
                  overflow: 'hidden'
                }}
              >
                {item.label}

                {isActive && (
                  <div style={{
                    position: 'absolute',
                    right: '0',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: '4px',
                    height: '60%',
                    backgroundColor: '#74c69d',
                    borderRadius: '2px'
                  }}></div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div style={{ backgroundColor: '#f8fafc', borderRadius: '8px', padding: '16px', margin: '20px', color: '#1e293b' }}>
        <div style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 'bold', letterSpacing: '0.5px', marginBottom: '12px' }}>
          MIDDLEWARE STATS
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '8px' }}>
          <span style={{ color: '#64748b' }}>CPU Load</span>
          <span style={{ fontWeight: '600', color: '#0f172a' }}>{stats.cpu}%</span>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '16px' }}>
          <span style={{ color: '#64748b' }}>RAM Usage</span>
          <span style={{ fontWeight: '600', color: '#0f172a' }}>{stats.ram} GB</span>
        </div>
        
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '6px', 
          fontSize: '0.7rem', 
          color: stats.isConnected ? '#10b981' : '#ef4444', 
          fontWeight: 'bold' 
        }}>
          <div style={{ 
            width: '6px', 
            height: '6px', 
            backgroundColor: stats.isConnected ? '#10b981' : '#ef4444', 
            borderRadius: '50%' 
          }}></div>
          {stats.isConnected ? 'NODE CONNECTED' : 'NODE OFFLINE'}
        </div>
      </div>

    </div>
  );
}