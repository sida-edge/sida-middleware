import React from 'react'

export default function ServiceCard({ serviceId, telemetry, timestamp, onClose }) {
  const styles = {
    card: { 
      backgroundColor: '#ffffff', 
      padding: '20px', 
      borderRadius: '12px', 
      width: '100%', 
      minWidth: '300px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', 
      display: 'flex', 
      flexDirection: 'column',
      height: '350px'
    },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '15px', marginBottom: '15px' },
    title: { margin: 0, color: '#0f172a', fontSize: '16px', fontWeight: 'bold' },
    closeBtn: { background: 'transparent', border: 'none', fontSize: '20px', color: '#64748b', cursor: 'pointer' },
    content: { overflowY: 'auto', flex: 1, backgroundColor: '#f8fafc', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' },
    pre: { margin: 0, fontSize: '13px', fontFamily: 'monospace', color: '#0f172a', whiteSpace: 'pre-wrap' },
    timestamp: { fontSize: '12px', color: '#94a3b8', marginTop: '10px', textAlign: 'right' }
  }

  let displayData = telemetry;
  if (telemetry && typeof telemetry === 'string') {
    try {
      displayData = JSON.parse(telemetry);
    } catch (e) {
      // Mantém a string original se falhar
    }
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.title}>📡 {serviceId.toUpperCase()}</h2>
        <button style={styles.closeBtn} onClick={() => onClose(serviceId)}>&times;</button>
      </div>
      <div style={styles.content}>
        {displayData ? (
          <><pre style={styles.pre}>
            {typeof displayData === 'object' ? JSON.stringify(displayData, null, 2) : displayData}
          </pre>
            <div style={styles.timestamp}>
              {timestamp ? `Última atualização: ${timestamp}` : 'Sem atualizações recentes'}
            </div></>
        ) : (
          <div style={{ color: '#94a3b8', fontStyle: 'italic', textAlign: 'center' }}>Sem dados...</div>
        )}
      </div>
    </div>
  )
}