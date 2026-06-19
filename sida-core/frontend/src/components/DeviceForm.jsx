import { useState } from 'react'

export default function DeviceForm({ 
  plantModel, 
  targetArea, 
  targetLine, 
  initialDeviceId,
  initialDeviceData,
  onSave, 
  onCancel 
}) {
  const [deviceName, setDeviceName] = useState(() => initialDeviceId ? initialDeviceId.replace(/_/g, ' ') : '')
  const [protocol, setProtocol] = useState(() => initialDeviceData?.connection?.protocol || 'modbus_tcp')
  
  const [ip, setIp] = useState(() => initialDeviceData?.connection?.host || '')
  const [port, setPort] = useState(() => initialDeviceData?.connection?.port || 502)
  const [slaveId, setSlaveId] = useState(() => initialDeviceData?.connection?.unit_id || 1)
  const [byteOrder, setByteOrder] = useState(() => initialDeviceData?.connection?.byte_order || 'ABCD')
  
  const [endpointUrl, setEndpointUrl] = useState(() => initialDeviceData?.connection?.endpoint_url || '')

  // Comum
  const [pollingRate, setPollingRate] = useState(() => initialDeviceData?.connection?.scan_rate_ms || 1000)

  const [tags, setTags] = useState(() => {
    if (initialDeviceData && initialDeviceData.metrics_mapping) {
      return Object.entries(initialDeviceData.metrics_mapping).map(([key, metric]) => ({
        id: crypto.randomUUID().split('-')[0],
        name: metric.name ? metric.name.replace(/_/g, ' ') : '',
        address: metric.register_type ? key : '',
        nodeId: metric.node_id || '',
        regType: metric.register_type || 'holding',
        dataType: metric.data_type,
        scale: metric.scale_factor,
        unit: metric.unit || ''
      }))
    }
    return []
  })

  const handleAddTag = () => {
    setTags([...tags, { 
      id: crypto.randomUUID().split('-')[0], 
      name: '', 
      address: '', 
      nodeId: '',
      regType: 'holding', 
      dataType: protocol === 'opc_ua' ? 'float' : 'int16',
      scale: 1, 
      unit: '' 
    }])
  }

  const handleRemoveTag = (idToRemove) => {
    setTags(tags.filter(t => t.id !== idToRemove))
  }

  const handleTagChange = (id, field, value) => {
    setTags(tags.map(t => t.id === id ? { ...t, [field]: value } : t))
  }

  const handleProtocolChange = (e) => {
    const newProtocol = e.target.value;
    setProtocol(newProtocol);
    setTags([]);
  }

  const checkData = () => {
    if (!deviceName.trim()) return "O Nome do equipamento é obrigatório."
    if (pollingRate < 50) return "Polling Rate inválido. Use no mínimo 50ms."

    if (protocol.startsWith('modbus')) {
      const hostRegex = /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^host\.docker\.internal$|^localhost$/;
      if (!hostRegex.test(ip)) return "Endereço IP ou Hostname inválido.";
      if (port < 1 || port > 65535) return "Porta inválida (deve ser entre 1 e 65535)."
      if (slaveId < 0 || slaveId > 255) return "Slave ID inválido (0-255)."
    } else if (protocol === 'opc_ua') {
      if (!endpointUrl.trim().startsWith('opc.tcp://')) return "O Endpoint URL deve começar com opc.tcp://"
    }

    if (tags.length === 0) return "Adicione pelo menos uma Tag para leitura."

    const identificadoresUsados = new Set()
    for (let i = 0; i < tags.length; i++) {
      const t = tags[i]
      if (!t.name.trim()) return `A tag da linha ${i+1} não tem nome.`
      
      if (protocol.startsWith('modbus')) {
        if (!t.address) return `A tag '${t.name}' não tem endereço configurado.`
        if (identificadoresUsados.has(t.address)) {
          return `Conflito: O endereço ${t.address} está a ser usado mais de uma vez.`
        }
        identificadoresUsados.add(t.address)
      } else if (protocol === 'opc_ua') {
        if (!t.nodeId) return `A tag '${t.name}' não tem Node ID configurado.`
        if (identificadoresUsados.has(t.nodeId)) {
          return `Conflito: O Node ID ${t.nodeId} está a ser usado mais de uma vez.`
        }
        identificadoresUsados.add(t.nodeId)
      }
    }

    return null
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    const checkError = checkData()
    if (checkError) {
      alert(`Erro de Configuração:\n${checkError}`)
      return
    }

    const deviceId = deviceName.toLowerCase().trim().replace(/\s+/g, '_')

    const connectionConfig = {
      protocol: protocol,
      scan_rate_ms: parseInt(pollingRate)
    };

    if (protocol.startsWith('modbus')) {
      connectionConfig.host = ip;
      connectionConfig.port = parseInt(port);
      connectionConfig.unit_id = parseInt(slaveId);
      connectionConfig.byte_order = byteOrder;
    } else if (protocol === 'opc_ua') {
      connectionConfig.endpoint_url = endpointUrl;
    }

    const metricsMapping = {}
    tags.forEach(t => {
      const mapKey = protocol === 'opc_ua' ? t.nodeId : t.address.toString();
      
      const metricConfig = {
        name: t.name.toLowerCase().trim().replace(/\s+/g, '_'),
        scale_factor: parseFloat(t.scale),
        unit: t.unit || null,
        data_type: t.dataType
      };

      if (protocol.startsWith('modbus')) {
        metricConfig.register_type = t.regType;
      } else if (protocol === 'opc_ua') {
        metricConfig.node_id = t.nodeId;
      }

      metricsMapping[mapKey] = metricConfig;
    })

    const configFinal = {
      enabled: initialDeviceData ? initialDeviceData.enabled : true,
      connection: connectionConfig,
      asset_context: {
        standard: "ISA-95",
        path: [
          { type: 'area', id: targetArea },
          { type: 'line', id: targetLine },
          { type: 'equipment', id: deviceId }
        ]
      },
      metrics_mapping: metricsMapping
    }

    onSave(deviceId, configFinal)
  }

  const colors = { bg: '#f8fafc', card: '#ffffff', border: '#e2e8f0', primary: '#2563eb', textMain: '#0f172a', textMuted: '#64748b', danger: '#ef4444' }
  const styles = {
    overlay: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(4px)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center' },
    modal: { backgroundColor: colors.card, borderRadius: '12px', width: '100%', maxWidth: '900px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' },
    header: { padding: '20px 30px', borderBottom: `1px solid ${colors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
    content: { padding: '30px', overflowY: 'auto', flex: 1 },
    footer: { padding: '20px 30px', borderTop: `1px solid ${colors.border}`, display: 'flex', justifyContent: 'flex-end', gap: '10px', backgroundColor: '#f8fafc', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px' },
    sectionTitle: { fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase', color: colors.textMuted, marginBottom: '15px', letterSpacing: '1px' },
    grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' },
    grid4: { display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1.5fr', gap: '20px', marginBottom: '30px' },
    input: { width: '100%', padding: '10px', borderRadius: '6px', border: `1px solid ${colors.border}`, fontSize: '14px', boxSizing: 'border-box' },
    label: { display: 'block', fontSize: '13px', fontWeight: '600', color: colors.textMain, marginBottom: '6px' },
    btnPrimary: { padding: '10px 20px', backgroundColor: colors.primary, color: 'white', border: 'none', borderRadius: '6px', fontWeight: '600', cursor: 'pointer' },
    btnSecondary: { padding: '10px 20px', backgroundColor: 'white', color: colors.textMain, border: `1px solid ${colors.border}`, borderRadius: '6px', fontWeight: '600', cursor: 'pointer' }
  }

  const tagGridTemplate = protocol === 'opc_ua' 
    ? '2fr 2.5fr 1fr 1fr 1fr auto'
    : '2fr 1fr 1.5fr 1fr 1fr 1fr auto';

  const tagRowStyle = { 
    display: 'grid', 
    gridTemplateColumns: tagGridTemplate, 
    gap: '10px', 
    alignItems: 'center', 
    backgroundColor: colors.bg, 
    padding: '10px', 
    borderRadius: '8px', 
    marginBottom: '10px', 
    border: `1px solid ${colors.border}` 
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        
        <div style={styles.header}>
          <div>
            <h2 style={{ margin: 0, color: colors.textMain, fontSize: '20px' }}>
              {initialDeviceId ? 'Editar Equipamento' : 'Integrar Equipamento'}
            </h2>
            <div style={{ fontSize: '13px', color: colors.textMuted, marginTop: '4px' }}>
              Destino: <span style={{ fontWeight: 'bold' }}>{targetArea} ➔ {targetLine}</span>
            </div>
          </div>
          <button onClick={onCancel} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: colors.textMuted }}>&times;</button>
        </div>

        <div style={styles.content}>
          <div style={styles.sectionTitle}>1. Identificação e Rede</div>
          
          <div style={styles.grid2}>
            <div>
              <label style={styles.label}>Nome do Equipamento (Ex: Forno A)</label>
              <input style={styles.input} value={deviceName} onChange={e => setDeviceName(e.target.value)} autoFocus />
            </div>
            <div>
              <label style={styles.label}>Protocolo</label>
              <select style={styles.input} value={protocol} onChange={handleProtocolChange}>
                <option value="modbus_tcp">Modbus TCP/IP</option>
                <option value="opc_ua">OPC UA</option>
              </select>
            </div>
          </div>

          {protocol.startsWith('modbus') ? (
            <>
              <div style={styles.grid4}>
                <div>
                  <label style={styles.label}>Endereço IP</label>
                  <input style={styles.input} placeholder="192.168.1.50" value={ip} onChange={e => setIp(e.target.value)} />
                </div>
                <div>
                  <label style={styles.label}>Porta</label>
                  <input type="number" style={styles.input} value={port} onChange={e => setPort(e.target.value)} />
                </div>
                <div>
                  <label style={styles.label}>Slave ID</label>
                  <input type="number" style={styles.input} value={slaveId} onChange={e => setSlaveId(e.target.value)} />
                </div>
                <div>
                  <label style={styles.label}>Polling Rate (ms)</label>
                  <input type="number" style={styles.input} value={pollingRate} onChange={e => setPollingRate(e.target.value)} />
                </div>
              </div>

              <div style={{ marginBottom: '40px' }}>
                <label style={styles.label}>Ordem de Bytes (Endianness) - Crítico para Float32/Int32</label>
                <select style={{...styles.input, width: '50%'}} value={byteOrder} onChange={e => setByteOrder(e.target.value)}>
                  <option value="ABCD">Big Endian (ABCD) - Padrão Geral</option>
                  <option value="DCBA">Little Endian (DCBA)</option>
                  <option value="CDAB">Word Swap (CDAB) - Comum em Schneider/Siemens</option>
                  <option value="BADC">Byte Swap (BADC)</option>
                </select>
              </div>
            </>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px', marginBottom: '40px' }}>
              <div>
                <label style={styles.label}>Endpoint URL</label>
                <input style={styles.input} placeholder="opc.tcp://192.168.1.50:4840" value={endpointUrl} onChange={e => setEndpointUrl(e.target.value)} />
              </div>
              <div>
                <label style={styles.label}>Polling Rate (ms)</label>
                <input type="number" style={styles.input} value={pollingRate} onChange={e => setPollingRate(e.target.value)} />
              </div>
            </div>
          )}

          <div style={{...styles.sectionTitle, display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <span>2. Tabela de Variáveis (Tags)</span>
            <button type="button" onClick={handleAddTag} style={{ padding: '6px 12px', backgroundColor: '#dbeafe', color: colors.primary, border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}>
              + Nova Tag
            </button>
          </div>

          {tags.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', backgroundColor: colors.bg, borderRadius: '8px', border: `1px dashed ${colors.border}`, color: colors.textMuted }}>
              Nenhum dado configurado. Clique no botão para mapear a primeira variável.
            </div>
          ) : (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: tagGridTemplate, gap: '10px', padding: '0 10px', marginBottom: '8px', fontSize: '11px', fontWeight: 'bold', color: colors.textMuted }}>
                <div>NOME (KEY)</div>
                {protocol === 'opc_ua' ? (
                  <div>NODE ID</div>
                ) : (
                  <>
                    <div>ENDEREÇO</div>
                    <div>FUNÇÃO (TIPO)</div>
                  </>
                )}
                <div>DADO</div>
                <div>ESCALA</div>
                <div>UNIDADE</div>
                <div></div>
              </div>

              {tags.map((tag) => (
                <div key={tag.id} style={tagRowStyle}>
                  <input style={styles.input} placeholder="Ex: Temperatura" value={tag.name} onChange={e => handleTagChange(tag.id, 'name', e.target.value)} />
                  
                  {protocol === 'opc_ua' ? (
                    <input style={styles.input} placeholder="ns=3;s=Variable" value={tag.nodeId} onChange={e => handleTagChange(tag.id, 'nodeId', e.target.value)} />
                  ) : (
                    <>
                      <input style={styles.input} type="number" placeholder="40001" value={tag.address} onChange={e => handleTagChange(tag.id, 'address', e.target.value)} />
                      <select style={styles.input} value={tag.regType} onChange={e => handleTagChange(tag.id, 'regType', e.target.value)}>
                        <option value="holding">Holding Reg (4x)</option>
                        <option value="input">Input Reg (3x)</option>
                        <option value="coil">Coil (0x)</option>
                        <option value="discrete">Discrete Input (1x)</option>
                      </select>
                    </>
                  )}

                  <select style={styles.input} value={tag.dataType} onChange={e => handleTagChange(tag.id, 'dataType', e.target.value)}>
                    <option value="float">FLOAT 32</option>
                    <option value="int16">INT 16</option>
                    <option value="uint16">UINT 16</option>
                    <option value="int32">INT 32</option>
                    <option value="bool">BOOL</option>
                    {protocol === 'opc_ua' && <option value="string">STRING</option>}
                  </select>

                  <input style={styles.input} type="number" step="0.001" value={tag.scale} onChange={e => handleTagChange(tag.id, 'scale', e.target.value)} />
                  
                  <input style={styles.input} placeholder="Ex: °C" value={tag.unit} onChange={e => handleTagChange(tag.id, 'unit', e.target.value)} />
                  
                  <button onClick={() => handleRemoveTag(tag.id)} style={{ padding: '8px', backgroundColor: '#fee2e2', color: colors.danger, border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                    X
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={styles.footer}>
          <button onClick={onCancel} style={styles.btnSecondary}>Cancelar</button>
          <button onClick={handleSubmit} style={styles.btnPrimary}>
            {initialDeviceId ? 'Atualizar Equipamento' : 'Guardar Equipamento'}
          </button>
        </div>
        
      </div>
    </div>
  )
}