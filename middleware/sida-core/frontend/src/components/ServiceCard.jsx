import React from 'react'

export default function ServiceCard({ serviceId, telemetry, onClose }) {
  const styles = {
    overlay: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(5px)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center' },
    card: { backgroundColor: '#ffffff', padding: '30px', borderRadius: '12px', width: '100%', maxWidth: '600px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', maxHeight: '85vh', display: 'flex', flexDirection: 'column' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '15px', marginBottom: '20px' },
    title: { margin: 0, color: '#0f172a', fontSize: '18px', fontWeight: 'bold' },
    closeBtn: { background: 'transparent', border: 'none', fontSize: '24px', color: '#64748b', cursor: 'pointer' },
    content: { overflowY: 'auto', flex: 1, backgroundColor: '#f8fafc', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' },
    pre: { margin: 0, fontSize: '13px', fontFamily: 'monospace', color: '#0f172a', whiteSpace: 'pre-wrap' }
  }

  // Tenta converter a string que veio do Go (campo 'data') de volta para objeto JSON
  let displayData = telemetry;
  if (telemetry && typeof telemetry === 'string') {
    try {
      displayData = JSON.parse(telemetry);
    } catch (e) {
      // Se não for um JSON válido, mantém a string original
    }
  }

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.card} onClick={e => e.stopPropagation()}>
        <div style={styles.header}>
          <h2 style={styles.title}>📡 Telemetria: {serviceId.toUpperCase()}</h2>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>
        <div style={styles.content}>
          {displayData ? (
            <pre style={styles.pre}>
              {typeof displayData === 'object' ? JSON.stringify(displayData, null, 2) : displayData}
            </pre>
          ) : (
            <div style={{ color: '#94a3b8', fontStyle: 'italic', textAlign: 'center' }}>Sem dados no momento...</div>
          )}
        </div>
      </div>
    </div>
  )
}