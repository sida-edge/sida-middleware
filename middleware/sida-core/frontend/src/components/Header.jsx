import React from 'react';

export default function Header() {
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'flex-end', 
      alignItems: 'center', 
      height: '100%', 
      padding: '0 32px',
      gap: '20px'
    }}>
      
      <div>
        <input 
          type="text" 
          placeholder="🔍 Search system..." 
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: '1px solid #e5e7eb',
            backgroundColor: '#f9fafb',
            width: '250px'
          }}
        />
      </div>

      <button style={{ 
        border: 'none', 
        background: 'transparent', 
        cursor: 'pointer', 
        fontSize: '1.2rem' 
      }}>
        🔔
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#111827' }}>Operator 04</div>
          <div style={{ fontSize: '0.7rem', color: '#6b7280' }}>ROLE: ADMIN</div>
        </div>
        <div style={{ 
          width: '35px', 
          height: '35px', 
          backgroundColor: '#374151', 
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: '0.8rem'
        }}>
          OP
        </div>
      </div>

    </div>
  );
}