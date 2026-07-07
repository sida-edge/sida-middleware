export default function DeviceCard({
  deviceId,
  device, 
  isEngineeringMode = false,
  onToggle,
  onEdit,
  onDelete
}) {
  const styles = {
    card: { 
      backgroundColor: 'white', borderRadius: '12px', padding: '20px', 
      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderTop: '4px solid #3b82f6',
      cursor: isEngineeringMode ? 'pointer' : 'default',
      transition: 'transform 0.2s, box-shadow 0.2s',
      position: 'relative'
    },
    tagBadge: { display: 'inline-block', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: '600', color: '#475569', margin: '4px 4px 0 0' },
    toggleTrack: { display: 'flex', alignItems: 'center', cursor: 'pointer', width: '36px', height: '20px', backgroundColor: device.enabled ? '#22c55e' : '#cbd5e1', borderRadius: '20px', padding: '2px', transition: 'background-color 0.3s', boxSizing: 'border-box' },
    toggleThumb: { width: '16px', height: '16px', backgroundColor: 'white', borderRadius: '50%', transform: device.enabled ? 'translateX(16px)' : 'translateX(0)', transition: 'transform 0.3s', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' },
    deleteBtn: { background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', fontSize: '16px', padding: '4px', borderRadius: '4px' }
  }

  return (
    <div 
      style={styles.card} 
      onClick={isEngineeringMode ? onEdit : undefined}
      onMouseEnter={e => isEngineeringMode && (e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.1)')}
      onMouseLeave={e => isEngineeringMode && (e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.05)')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', color: '#0f172a' }}>{deviceId.replace(/_/g, ' ').toUpperCase()}</h2>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ backgroundColor: device.enabled ? '#dcfce7' : '#fee2e2', color: device.enabled ? '#166534' : '#991b1b', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
            {device.enabled ? 'ATIVO' : 'INATIVO'}
          </span>

          {isEngineeringMode && (
            <>
              <div 
                style={styles.toggleTrack} 
                onClick={(e) => {
                  e.stopPropagation(); 
                  if (onToggle) onToggle(deviceId, !device.enabled);
                }}
                title={device.enabled ? "Desativar" : "Ativar"}
              >
                <div style={styles.toggleThumb} />
              </div>

              <button 
                style={styles.deleteBtn}
                onClick={(e) => {
                  e.stopPropagation(); 
                  if (onDelete) onDelete();
                }}
                title="Excluir equipamento"
              >
                🗑️
              </button>
            </>
          )}
        </div>
      </div>

      <div style={{ marginBottom: '15px', backgroundColor: '#f8fafc', padding: '10px', borderRadius: '8px' }}>
        <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8', fontWeight: 'bold' }}>🔌 CONEXÃO ({device.connection?.protocol?.toUpperCase()})</p>
        <div style={{ display: 'flex', gap: '15px', marginTop: '5px' }}>
          <span style={{ fontSize: '13px' }}><strong>IP:</strong> {device.connection?.host}</span>
          <span style={{ fontSize: '13px' }}><strong>Porta:</strong> {device.connection?.port}</span>
          <span style={{ fontSize: '13px' }}><strong>Scan:</strong> {device.connection?.scan_rate_ms}ms</span>
        </div>
      </div>

      <div>
        <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: '#94a3b8', fontWeight: 'bold' }}>📡 SENSORES MAPEADOS</p>
        <div>
          {Object.entries(device.metrics_mapping || {}).map(([reg, metric]) => (
            <span key={reg} style={styles.tagBadge} title={`Escala: ${metric.scale_factor}`}>
              {metric.name} {metric.unit ? `(${metric.unit})` : ''}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}