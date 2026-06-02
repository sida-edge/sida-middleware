export default function DeviceCard({ deviceId, device }) {
  const renderizarCaminhoISA95 = (pathArray) => {
    if (!pathArray) return "Caminho não definido"
    return pathArray.map(node => node.id.replace(/_/g, ' ').toUpperCase()).join(' ➔ ')
  }

  const styles = {
    card: { backgroundColor: 'white', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderTop: '4px solid #3b82f6' },
    tagBadge: { display: 'inline-block', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: '600', color: '#475569', margin: '4px 4px 0 0' }
  }

  return (
    <div style={styles.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', color: '#0f172a' }}>{deviceId.replace(/_/g, ' ').toUpperCase()}</h2>
        <span style={{ backgroundColor: device.enabled ? '#dcfce7' : '#fee2e2', color: device.enabled ? '#166534' : '#991b1b', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
          {device.enabled ? 'ATIVO' : 'INATIVO'}
        </span>
      </div>

      <div style={{ marginBottom: '15px' }}>
        <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8', fontWeight: 'bold' }}>📍 LOCALIZAÇÃO (ISA-95)</p>
        <p style={{ margin: '4px 0', fontSize: '13px', color: '#334155' }}>{renderizarCaminhoISA95(device.asset_context?.path)}</p>
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