import { useState } from 'react'

export default function ConnectorForm({ initialConnectorId, initialData, onSave, onCancel }) {
  const [name, setName] = useState(() => initialConnectorId || '')
  const [protocol, setProtocol] = useState(() => initialData?.protocol || 'http')
  const [host, setHost] = useState(() => initialData?.host || '')
  const [port, setPort] = useState(() => initialData?.port || (initialData?.protocol === 'mqtt' ? 1883 : 80))
  
  const [endpoint, setEndpoint] = useState(() => initialData?.endpoint || '/')
  const [username, setUsername] = useState(() => initialData?.username || '')
  const [password, setPassword] = useState(() => initialData?.password || '')

  const handleProtocolChange = (e) => {
    const newProto = e.target.value;
    setProtocol(newProto);
    setPort(newProto === 'mqtt' ? 1883 : 80);
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name.trim()) return alert("O nome da conexão é obrigatório.")
    if (!host.trim()) return alert("O host é obrigatório.")
    if (port < 1 || port > 65535) return alert("Porta inválida.")

    const connectorId = name.toLowerCase().trim().replace(/\s+/g, '_')

    const configFinal = {
      protocol,
      host,
      port: parseInt(port)
    }

    if (protocol === 'http') {
      if (!endpoint.trim()) return alert("O endpoint é obrigatório para HTTP.")
      configFinal.endpoint = endpoint
    } else {
      if (username.trim()) configFinal.username = username
      if (password.trim()) configFinal.password = password
    }

    onSave(connectorId, configFinal)
  }

  const styles = {
    overlay: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(15, 23, 42, 0.75)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center' },
    modal: { backgroundColor: 'white', borderRadius: '12px', width: '100%', maxWidth: '600px', padding: '30px' },
    input: { width: '100%', padding: '10px', marginTop: '5px', marginBottom: '15px', borderRadius: '6px', border: '1px solid #e2e8f0', boxSizing: 'border-box' },
    label: { fontSize: '13px', fontWeight: 'bold', color: '#475569' },
    grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' },
    buttons: { display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h2 style={{ marginTop: 0 }}>{initialConnectorId ? 'Editar Conexão' : 'Nova Conexão Externa'}</h2>
        
        <div style={styles.grid}>
          <div>
            <label style={styles.label}>ID / Nome da Conexão</label>
            <input style={styles.input} value={name} onChange={e => setName(e.target.value)} placeholder="Ex: nuvem_aws" disabled={!!initialConnectorId} />
          </div>
          <div>
            <label style={styles.label}>Protocolo</label>
            <select style={styles.input} value={protocol} onChange={handleProtocolChange}>
              <option value="http">HTTP / HTTPS</option>
              <option value="mqtt">MQTT</option>
            </select>
          </div>
        </div>

        <div style={styles.grid}>
          <div>
            <label style={styles.label}>Host / IP</label>
            <input style={styles.input} value={host} onChange={e => setHost(e.target.value)} placeholder="api.exemplo.com" />
          </div>
          <div>
            <label style={styles.label}>Porta</label>
            <input type="number" style={styles.input} value={port} onChange={e => setPort(e.target.value)} />
          </div>
        </div>

        {protocol === 'http' && (
          <div>
            <label style={styles.label}>Endpoint</label>
            <input style={styles.input} value={endpoint} onChange={e => setEndpoint(e.target.value)} placeholder="/api/v1/telemetry" />
          </div>
        )}

        {protocol === 'mqtt' && (
          <div style={styles.grid}>
            <div>
              <label style={styles.label}>Usuário (Opcional)</label>
              <input style={styles.input} value={username} onChange={e => setUsername(e.target.value)} placeholder="Deixe em branco se for anônimo" />
            </div>
            <div>
              <label style={styles.label}>Senha (Opcional)</label>
              <input type="password" style={styles.input} value={password} onChange={e => setPassword(e.target.value)} />
            </div>
          </div>
        )}

        <div style={styles.buttons}>
          <button onClick={onCancel} style={{ padding: '10px 20px', borderRadius: '6px', border: '1px solid #e2e8f0', backgroundColor: 'white', cursor: 'pointer' }}>Cancelar</button>
          <button onClick={handleSubmit} style={{ padding: '10px 20px', borderRadius: '6px', border: 'none', backgroundColor: '#2563eb', color: 'white', cursor: 'pointer', fontWeight: 'bold' }}>Salvar</button>
        </div>
      </div>
    </div>
  )
}