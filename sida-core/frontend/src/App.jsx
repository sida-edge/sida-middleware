import { useState, useEffect } from 'react'
import DeviceCard from './components/DeviceCard'
import AdvancedEditor from './components/AdvancedEditor'
import DeviceForm from './components/DeviceForm'

const LOCAL_GATEWAY_ID = "sida_edge_001";

function App() {
  const [status, setStatus] = useState({ text: 'A ligar...', ok: false })
  const [config, setConfig] = useState({ devices: {} })
  const [configJson, setConfigJson] = useState('')
  const [mensagem, setMensagem] = useState({ text: '', type: '' })
  
  const [activeTab, setActiveTab] = useState('planta') 
  const [isEditing, setIsEditing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  
  // NOVO ESTADO: Controla qual linha estamos a visualizar no momento. 
  // Se for null, mostra o ecrã de todas as linhas.
  const [linhaSelecionada, setLinhaSelecionada] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.ok ? setStatus({ text: 'Online', ok: true }) : setStatus({ text: 'Falha', ok: false }))
      .catch(() => setStatus({ text: 'Offline', ok: false }))
    carregarManifesto();
  }, [])

  const carregarManifesto = async () => {
    try {
      const res = await fetch(`/api/config/manifest?gateway_id=${LOCAL_GATEWAY_ID}`)
      if (res.ok) {
        const data = await res.json()
        setConfig(data.config)
        setConfigJson(JSON.stringify(data.config, null, 2))
        setIsEditing(false)
      }
    } catch (error) {
      setMensagem({ text: 'Erro ao carregar dados.', type: 'error' })
    }
  }

  const guardarManifesto = async (novoJsonStr = configJson) => {
    try {
      const configParseada = JSON.parse(novoJsonStr)
      const res = await fetch('/api/config/manifest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gateway_id: LOCAL_GATEWAY_ID, config: configParseada })
      })

      if (res.ok) {
        setConfig(configParseada)
        setConfigJson(JSON.stringify(configParseada, null, 2))
        setMensagem({ text: 'Implantação concluída!', type: 'success' })
        setIsEditing(false)
        setShowForm(false)
      }
    } catch (error) {
      setMensagem({ text: 'Erro de sintaxe no JSON.', type: 'error' })
    }
  }

  const handleAddDevice = (deviceId, newDeviceData) => {
    const novaConfig = { ...config }
    if (!novaConfig.devices) novaConfig.devices = {}
    novaConfig.devices[deviceId] = newDeviceData
    guardarManifesto(JSON.stringify(novaConfig, null, 2))
  }

  // --- LÓGICA DE AGRUPAMENTO POR LINHA ---
  const getLinhasAgrupadas = () => {
    const linhas = {}
    
    Object.entries(config.devices || {}).forEach(([id, device]) => {
      // Procura o nó "line" no array de contexto ISA-95
      const lineNode = device.asset_context?.path?.find(node => node.type === 'line')
      const lineId = lineNode ? lineNode.id : 'nao_atribuida'
      
      if (!linhas[lineId]) {
        linhas[lineId] = { id: lineId, equipamentos: [] }
      }
      linhas[lineId].equipamentos.push({ id, ...device })
    })
    
    return linhas
  }

  const linhasAgrupadas = getLinhasAgrupadas()

  // --- ESTILOS ---
  const styles = {
    container: { flex: 1, width: '100%', backgroundColor: '#f1f5f9', color: '#0f172a', padding: '2rem' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
    tabs: { display: 'flex', gap: '10px', marginBottom: '20px' },
    tabBtn: (active) => ({ padding: '10px 20px', cursor: 'pointer', fontWeight: 'bold', border: 'none', borderRadius: '8px', backgroundColor: active ? '#2563eb' : '#e2e8f0', color: active ? 'white' : '#64748b', transition: '0.2s' }),
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '20px' },
    lineCard: { backgroundColor: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderLeft: '6px solid #2563eb', cursor: 'pointer', transition: 'transform 0.2s, box-shadow 0.2s' }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', color: '#1e293b' }}>🏭 SIDA-Core | Visão Operacional</h1>
          <p style={{ margin: '5px 0 0 0', color: '#64748b', fontSize: '14px' }}>Edge Node: <strong>{LOCAL_GATEWAY_ID}</strong></p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ height: '12px', width: '12px', borderRadius: '50%', backgroundColor: status.ok ? '#10b981' : '#ef4444' }}></span>
          <span style={{ fontWeight: '600', color: status.ok ? '#10b981' : '#ef4444' }}>Serviço {status.text}</span>
        </div>
      </div>

      <div style={styles.tabs}>
        <button style={styles.tabBtn(activeTab === 'planta')} onClick={() => {setActiveTab('planta'); setShowForm(false); setLinhaSelecionada(null)}}>📊 Topologia</button>
        <button style={styles.tabBtn(activeTab === 'avancado')} onClick={() => {setActiveTab('avancado'); setShowForm(false)}}>⚙️ Manifesto Bruto</button>
      </div>

      {/* ABA: TOPOLOGIA (PLANTA) */}
      {activeTab === 'planta' && !showForm && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            {/* Breadcrumb de Navegação */}
            <h2 style={{ fontSize: '20px', color: '#334155', margin: 0 }}>
              {linhaSelecionada 
                ? <span style={{ cursor: 'pointer', color: '#2563eb' }} onClick={() => setLinhaSelecionada(null)}>Fábrica</span> 
                : 'Visão Geral das Linhas'}
              {linhaSelecionada && ` > ${linhaSelecionada.replace(/_/g, ' ').toUpperCase()}`}
            </h2>
            
            <button 
              onClick={() => setShowForm(true)} 
              style={{ padding: '10px 20px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              + Adicionar Equipamento
            </button>
          </div>

          {/* VISÃO 1: LISTA DE LINHAS */}
          {!linhaSelecionada && (
            <div style={styles.grid}>
              {Object.values(linhasAgrupadas).length === 0 ? (
                <p style={{ color: '#64748b' }}>Nenhum equipamento registado neste Gateway.</p>
              ) : (
                Object.values(linhasAgrupadas).map(linha => (
                  <div 
                    key={linha.id} 
                    style={styles.lineCard} 
                    onClick={() => setLinhaSelecionada(linha.id)}
                    onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.1)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.05)'; }}
                  >
                    <h3 style={{ margin: '0 0 10px 0', color: '#0f172a', fontSize: '22px' }}>
                      {linha.id === 'nao_atribuida' ? 'Equipamentos Soltos' : linha.id.replace(/_/g, ' ').toUpperCase()}
                    </h3>
                    <p style={{ margin: 0, color: '#64748b', fontSize: '15px' }}>
                      <strong>{linha.equipamentos.length}</strong> equipamento(s) a operar
                    </p>
                    
                    {/* Conta quantos estão ativos/inativos dentro da linha */}
                    <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                      <span style={{ backgroundColor: '#dcfce7', color: '#166534', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
                        {linha.equipamentos.filter(e => e.enabled).length} Ativos
                      </span>
                      {linha.equipamentos.filter(e => !e.enabled).length > 0 && (
                        <span style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
                          {linha.equipamentos.filter(e => !e.enabled).length} Inativos
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* VISÃO 2: EQUIPAMENTOS DENTRO DA LINHA SELECIONADA */}
          {linhaSelecionada && (
            <div style={styles.grid}>
              {linhasAgrupadas[linhaSelecionada].equipamentos.map(device => (
                <DeviceCard key={device.id} deviceId={device.id} device={device} />
              ))}
            </div>
          )}
        </>
      )}

      {/* COMPONENTES SECUNDÁRIOS */}
      {showForm && <DeviceForm onSave={handleAddDevice} onCancel={() => setShowForm(false)} />}

      {activeTab === 'avancado' && (
         <AdvancedEditor configJson={configJson} setConfigJson={setConfigJson} isEditing={isEditing} setIsEditing={setIsEditing} guardarManifesto={() => guardarManifesto(configJson)} mensagem={mensagem} />
      )}
    </div>
  )
}

export default App