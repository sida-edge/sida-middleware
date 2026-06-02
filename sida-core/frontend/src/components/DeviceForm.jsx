import { useState } from 'react'

export default function DeviceForm({ onSave, onCancel }) {
  const [deviceId, setDeviceId] = useState('')
  const [ip, setIp] = useState('')
  const [protocol, setProtocol] = useState('modbus_tcp')

  const handleSubmit = (e) => {
    e.preventDefault()
    
    // Constrói o objeto JSON por trás dos panos
    const novoDevice = {
      enabled: true,
      connection: { protocol, host: ip, port: 502, scan_rate_ms: 500 },
      asset_context: { path: [{ type: "equipment", id: deviceId }] },
      metrics_mapping: {} // Inicia vazio
    }
    onSave(deviceId, novoDevice)
  }

  const inputStyle = { width: '100%', padding: '10px', margin: '5px 0 15px 0', borderRadius: '6px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }

  return (
    <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <h2 style={{ marginTop: 0 }}>Adicionar Novo Equipamento</h2>
      <form onSubmit={handleSubmit}>
        <label>ID do Equipamento (Ex: clp_esteira_b):</label>
        <input style={inputStyle} required value={deviceId} onChange={e => setDeviceId(e.target.value.toLowerCase().replace(/\s/g, '_'))} />

        <label>Endereço IP:</label>
        <input style={inputStyle} required placeholder="192.168.0.X" value={ip} onChange={e => setIp(e.target.value)} />

        <label>Protocolo:</label>
        <select style={inputStyle} value={protocol} onChange={e => setProtocol(e.target.value)}>
          <option value="modbus_tcp">Modbus TCP</option>
          <option value="opc_ua">OPC-UA</option>
        </select>

        <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
          <button type="submit" style={{ padding: '10px 20px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Guardar Equipamento</button>
          <button type="button" onClick={onCancel} style={{ padding: '10px 20px', backgroundColor: '#e2e8f0', color: '#475569', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}