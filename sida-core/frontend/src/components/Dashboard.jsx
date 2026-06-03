import { useState } from 'react'
import DeviceForm from './DeviceForm'
import DeviceCard from './DeviceCard' 

export default function Dashboard({ config, onSave, gatewayId, token, setToken }) {
  // Estado para saber exatamente EM QUE linha clicámos para adicionar o equipamento
  const [deviceTarget, setDeviceTarget] = useState(null) // { areaId, lineId } ou null
  
  const [showPinPrompt, setShowPinPrompt] = useState(false)
  const [pinInput, setPinInput] = useState('')
  const [activeTab, setActiveTab] = useState('all') 

  // --- ESTADOS DO NOVO MODAL ---
  const [modalConfig, setModalConfig] = useState({ isOpen: false, type: null }) // type: 'area' ou 'line'
  const [modalInput, setModalInput] = useState('')
  const [modalSelectArea, setModalSelectArea] = useState('')

  const plantModel = config.plant_model || { areas: {} }
  const devices = config.devices || {}
  const isEngineeringMode = token !== null

  const handleUnlock = async () => {
    try {
      const res = await fetch('/api/auth/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pinInput })
      })
      if (res.ok) {
        const data = await res.json()
        setToken(data.token)
        setShowPinPrompt(false)
        setPinInput('')
      } else {
        alert("PIN Incorreto.")
      }
    } catch (error) {
      alert("Erro na comunicação com o Edge.")
    }
  }

  const handleLock = () => {
    setToken(null)
    setDeviceTarget(null)
    setModalConfig({ isOpen: false, type: null })
  }

  // --- ABRIR MODAIS ---
  const openAreaModal = () => {
    setModalInput('')
    setModalConfig({ isOpen: true, type: 'area' })
  }

  const openLineModal = () => {
    setModalInput('')
    setModalSelectArea(activeTab === 'all' ? '' : activeTab)
    setModalConfig({ isOpen: true, type: 'line' })
  }

  const closeModal = () => {
    setModalConfig({ isOpen: false, type: null })
  }

  // --- GRAVAR DADOS DOS MODAIS ---
  const handleModalSubmit = async () => {
    if (!modalInput.trim()) {
      alert("O nome não pode estar vazio.")
      return
    }

    const idFormatado = modalInput.toLowerCase().trim().replace(/\s+/g, '_')
    const novaConfig = { ...config }

    if (modalConfig.type === 'area') {
      if (!novaConfig.plant_model.areas) novaConfig.plant_model.areas = {}
      if (novaConfig.plant_model.areas[idFormatado]) {
        alert("Já existe uma área com este nome.")
        return
      }
      novaConfig.plant_model.areas[idFormatado] = { name: modalInput, lines: [] }

    } else if (modalConfig.type === 'line') {
      const targetArea = modalSelectArea
      if (!targetArea) {
        alert("Selecione uma Área para esta linha.")
        return
      }
      if (!novaConfig.plant_model.areas[targetArea].lines) novaConfig.plant_model.areas[targetArea].lines = []
      if (novaConfig.plant_model.areas[targetArea].lines.includes(idFormatado)) {
        alert("Esta linha já existe nesta área.")
        return
      }
      novaConfig.plant_model.areas[targetArea].lines.push(idFormatado)
    }

    await onSave(novaConfig)
    closeModal()
  }

  // --- DESIGN SYSTEM ---
  const colors = {
    sidebarBg: '#0f172a', sidebarHover: '#1e293b', bg: '#f8fafc', card: '#ffffff',
    border: '#e2e8f0', primary: '#2563eb', warning: '#f59e0b', success: '#10b981',
    textMain: '#0f172a', textMuted: '#64748b'
  }

  const styles = {
    layout: { display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', fontFamily: 'system-ui, -apple-system, sans-serif' },
    sidebar: { width: '280px', backgroundColor: colors.sidebarBg, color: 'white', display: 'flex', flexDirection: 'column', borderRight: `1px solid ${colors.sidebarHover}` },
    sidebarHeader: { padding: '24px', borderBottom: `1px solid ${colors.sidebarHover}` },
    navItem: (isActive) => ({ padding: '12px 24px', cursor: 'pointer', backgroundColor: isActive ? colors.sidebarHover : 'transparent', borderLeft: isActive ? `4px solid ${colors.primary}` : '4px solid transparent', transition: 'all 0.2s', fontSize: '14px', color: isActive ? 'white' : '#94a3b8' }),
    main: { flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: colors.bg, overflowY: 'auto' },
    topbar: { minHeight: '70px', backgroundColor: colors.card, borderBottom: `1px solid ${colors.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 30px' },
    content: { padding: '30px', maxWidth: '1200px', margin: '0 auto', width: '100%', boxSizing: 'border-box' },
    badge: { display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: '600', backgroundColor: '#dcfce7', color: '#166534' },
    badgeWarning: { display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: '600', backgroundColor: '#fef3c7', color: '#92400e' },
    btnPrimary: { padding: '10px 20px', backgroundColor: colors.primary, color: 'white', border: 'none', borderRadius: '6px', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 6px -1px rgba(37, 99, 235, 0.2)' },
    btnSecondary: { padding: '10px 20px', backgroundColor: 'white', color: colors.textMain, border: `1px solid ${colors.border}`, borderRadius: '6px', fontWeight: '600', cursor: 'pointer' },
    btnOutline: { padding: '6px 12px', backgroundColor: 'transparent', color: colors.primary, border: `1px solid ${colors.primary}`, borderRadius: '4px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' },
    // ESTILOS DO MODAL
    modalOverlay: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(5px)', zIndex: 999, display: 'flex', justifyContent: 'center', alignItems: 'center' },
    modalCard: { backgroundColor: 'white', padding: '30px', borderRadius: '12px', width: '100%', maxWidth: '400px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' },
    input: { width: '100%', padding: '12px', marginTop: '8px', borderRadius: '6px', border: `1px solid ${colors.border}`, boxSizing: 'border-box', fontSize: '15px' }
  }

  return (
    <div style={styles.layout}>
      
      {/* OVERLAY DOS MODAIS DE CONSTRUÇÃO */}
      {modalConfig.isOpen && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalCard}>
            <h2 style={{ margin: '0 0 20px 0', color: colors.textMain }}>
              {modalConfig.type === 'area' ? 'Nova Área Operacional' : 'Adicionar Nova Linha'}
            </h2>
            
            {/* Se for criar uma Linha a partir da Visão Global, pede para escolher a Área */}
            {modalConfig.type === 'line' && activeTab === 'all' && (
              <div style={{ marginBottom: '15px' }}>
                <label style={{ fontSize: '14px', fontWeight: 'bold', color: colors.textMuted }}>Pertence a qual Área?</label>
                <select value={modalSelectArea} onChange={e => setModalSelectArea(e.target.value)} style={styles.input}>
                  <option value="">-- Selecione uma Área --</option>
                  {Object.entries(plantModel.areas).map(([id, a]) => (
                    <option key={id} value={id}>{a.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div style={{ marginBottom: '25px' }}>
               <label style={{ fontSize: '14px', fontWeight: 'bold', color: colors.textMuted }}>Nome {modalConfig.type === 'area' ? 'da Área' : 'da Linha'}:</label>
               <input autoFocus placeholder={modalConfig.type === 'area' ? 'Ex: Embalagem' : 'Ex: Linha 1'} value={modalInput} onChange={e => setModalInput(e.target.value)} style={styles.input} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={closeModal} style={styles.btnSecondary}>Cancelar</button>
              <button onClick={handleModalSubmit} style={styles.btnPrimary}>Guardar</button>
            </div>
          </div>
        </div>
      )}

      {/* --- RENDERIZAÇÃO DA SIDEBAR E MAIN APP (IGUAL AO ANTERIOR) --- */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <div style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 'bold', letterSpacing: '1px', marginBottom: '4px' }}>SIDA EDGE CORE</div>
          <div style={{ fontSize: '18px', fontWeight: '600' }}>{plantModel.site || 'Site Não Definido'}</div>
          <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>{plantModel.enterprise}</div>
        </div>

        <div style={{ padding: '20px 0', flex: 1, overflowY: 'auto' }}>
          <div style={{ padding: '0 24px', fontSize: '11px', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '10px' }}>Visão Geral</div>
          <div style={styles.navItem(activeTab === 'all')} onClick={() => setActiveTab('all')}>🏭 Planta Completa</div>

          <div style={{ padding: '20px 24px 10px', fontSize: '11px', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase' }}>Áreas Operacionais</div>
          {Object.entries(plantModel.areas || {}).map(([areaId, areaData]) => (
            <div key={areaId} style={styles.navItem(activeTab === areaId)} onClick={() => setActiveTab(areaId)}>📍 {areaData.name}</div>
          ))}
        </div>
      </div>

      <div style={styles.main}>
        <div style={styles.topbar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
             {isEngineeringMode 
                ? <div style={styles.badgeWarning}><span style={{width:'8px',height:'8px',borderRadius:'50%',backgroundColor:colors.warning}}></span> MODO ENGENHARIA</div>
                : <div style={styles.badge}><span style={{width:'8px',height:'8px',borderRadius:'50%',backgroundColor:colors.success}}></span> OPERACIONAL</div>
             }
          </div>

          <div>
             {isEngineeringMode ? (
               <button onClick={handleLock} style={{ padding: '8px 16px', backgroundColor: '#fef3c7', color: '#b45309', border: '1px solid #fde68a', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>🔓 Trancar Edição</button>
             ) : (
               <button onClick={() => setShowPinPrompt(!showPinPrompt)} style={{ padding: '8px 16px', backgroundColor: 'transparent', color: colors.textMuted, border: `1px solid ${colors.border}`, borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>🔒 Desbloquear</button>
             )}
          </div>
        </div>

        {showPinPrompt && !isEngineeringMode && (
          <div style={{ position: 'absolute', top: '80px', right: '30px', backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', border: `1px solid ${colors.border}`, zIndex: 10 }}>
            <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '10px', color: colors.textMain }}>Acesso Restrito</div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input autoFocus type="password" placeholder="PIN" value={pinInput} onChange={e => setPinInput(e.target.value)} style={{ padding: '8px', borderRadius: '4px', border: `1px solid ${colors.border}`, width: '100px', textAlign: 'center', letterSpacing: '4px' }} />
              <button onClick={handleUnlock} style={{ padding: '8px 16px', backgroundColor: colors.textMain, color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>OK</button>
            </div>
          </div>
        )}

        <div style={styles.content}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '30px' }}>
             <div>
               <h1 style={{ margin: '0 0 5px 0', fontSize: '28px', color: colors.textMain }}>{activeTab === 'all' ? 'Planta Completa' : plantModel.areas[activeTab]?.name}</h1>
               <p style={{ margin: 0, color: colors.textMuted, fontSize: '14px' }}>Gestão e monitorização de ativos na camada de Edge.</p>
             </div>
             
             {isEngineeringMode && (
               <div style={{ display: 'flex', gap: '12px' }}>
                 {activeTab === 'all' && (
                   <button onClick={openAreaModal} style={styles.btnSecondary}>+ Nova Área</button>
                 )}
                 <button onClick={openLineModal} style={styles.btnPrimary}>+ Adicionar Linha</button>
               </div>
             )}
          </div>

          {Object.entries(plantModel.areas || {}).filter(([areaId]) => activeTab === 'all' || activeTab === areaId).map(([areaId, areaData]) => (
            <div key={areaId} style={{ marginBottom: '50px' }}>
              <div style={{ borderBottom: `2px solid ${colors.border}`, paddingBottom: '10px', marginBottom: '20px' }}>
                <h3 style={{ margin: 0, color: colors.textMain, fontSize: '20px' }}>{activeTab === 'all' ? `📍 ${areaData.name}` : 'Linhas de Produção'}</h3>
              </div>
              
              {areaData.lines.map(linha => {
                 const equipamentos = Object.entries(devices).filter(([_, d]) => d.asset_context?.path?.find(n => n.type === 'line')?.id === linha)
                 return (
                   <div key={linha} style={{ marginTop: '20px', padding: '20px', backgroundColor: 'white', borderRadius: '12px', border: `1px solid ${colors.border}`, boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                     
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                       <h4 style={{ margin: 0, color: colors.textMuted, textTransform: 'uppercase', fontSize: '13px', letterSpacing: '1px' }}>⚙️ {linha.replace(/_/g, ' ')}</h4>
                       
                       {/* BOTAO ATUALIZADO: Salva o contexto de Área e Linha */}
                       {isEngineeringMode && (
                         <button onClick={() => setDeviceTarget({ areaId, lineId: linha })} style={styles.btnOutline}>
                           + Integrar Equipamento
                         </button>
                       )}
                     </div>
                     
                     <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
                       {equipamentos.length > 0 ? (
                          equipamentos.map(([id, device]) => <DeviceCard key={id} deviceId={id} device={device} />)
                       ) : (
                          <div style={{ padding: '15px', backgroundColor: colors.bg, border: `1px dashed ${colors.border}`, borderRadius: '8px', color: colors.textMuted, fontSize: '13px', gridColumn: '1 / -1', textAlign: 'center' }}>Nenhum equipamento alocado a esta linha.</div>
                       )}
                     </div>
                   </div>
                 )
              })}
              
              {areaData.lines.length === 0 && (
                <div style={{ padding: '30px', textAlign: 'center', color: colors.textMuted, backgroundColor: 'white', borderRadius: '12px', border: `1px dashed ${colors.border}` }}>Esta área ainda não possui linhas de produção.</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* DEVICE FORM ATUALIZADO (Recebe o target injetado) */}
      {deviceTarget && (
        <DeviceForm 
          plantModel={plantModel} 
          targetArea={deviceTarget.areaId} 
          targetLine={deviceTarget.lineId} 
          onSave={(id, data) => { 
            const novaConfig = {...config}; 
            if(!novaConfig.devices) novaConfig.devices = {}; 
            novaConfig.devices[id] = data; 
            onSave(novaConfig); 
            setDeviceTarget(null);
          }} 
          onCancel={() => setDeviceTarget(null)} 
        />
      )}
    </div>
  )
}