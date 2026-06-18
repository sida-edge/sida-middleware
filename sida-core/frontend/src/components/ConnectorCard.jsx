export default function ConnectorCard({ 
  connectorId, 
  connector, 
  isEngineeringMode = false,
  onEdit,
  onDelete
}) {
  const isHttp = connector.protocol === 'http';

  const styles = {
    card: { backgroundColor: 'white', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderTop: `4px solid ${isHttp ? '#8b5cf6' : '#f59e0b'}`, cursor: isEngineeringMode ? 'pointer' : 'default', position: 'relative' },
    badge: { backgroundColor: isHttp ? '#ede9fe' : '#fef3c7', color: isHttp ? '#5b21b6' : '#b45309', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase' },
    deleteBtn: { background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', fontSize: '16px', padding: '4px' }
  }

  return (
    <div style={styles.card} onClick={isEngineeringMode ? onEdit : undefined}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', color: '#0f172a' }}>{connectorId.toUpperCase()}</h2>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={styles.badge}>{connector.protocol}</span>
          {isEngineeringMode && (
            <button style={styles.deleteBtn} onClick={(e) => { e.stopPropagation(); onDelete(); }} title="Excluir">🗑️</button>
          )}
        </div>
      </div>

      <div style={{ backgroundColor: '#f8fafc', padding: '12px', borderRadius: '8px', fontSize: '13px', color: '#475569' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div><strong>Host:</strong> {connector.host}</div>
          <div><strong>Porta:</strong> {connector.port}</div>
          
          {isHttp && (
            <div style={{ gridColumn: '1 / -1' }}><strong>Endpoint:</strong> {connector.endpoint}</div>
          )}
          
          {!isHttp && (
            <>
              <div><strong>User:</strong> {connector.username}</div>
              <div><strong>Pass:</strong> ••••••••</div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}