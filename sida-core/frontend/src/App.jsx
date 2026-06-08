import { useState, useEffect, useRef } from 'react'
import EdgeProvisioning from './components/EdgeProvisioning'
import SetupWizard from './components/SetupWizard'
import Dashboard from './components/Dashboard'

function App() {
  const [appState, setAppState] = useState('booting') 
  const [gatewayId, setGatewayId] = useState(null)
  const [config, setConfig] = useState(null)
  
  const [token, setToken] = useState(null)
  const tokenRef = useRef(null) 

  const updateToken = (newToken) => {
    setToken(newToken)
    tokenRef.current = newToken 
  }

  useEffect(() => {
    checkIdentity()
  }, [])

  const checkIdentity = async () => {
    try {
      const res = await fetch('/api/system/info')
      if (!res.ok) throw new Error('Servidor Go respondeu com erro.')
      const data = await res.json()
      if (data.provisioned) {
        setGatewayId(data.gateway_id)
        loadManifest(data.gateway_id)
      } else {
        setAppState('unprovisioned')
      }
    } catch (error) {
      setAppState('error')
    }
  }

  const loadManifest = async (id) => {
     try {
      const res = await fetch(`/api/config/manifest?gateway_id=${id}`)
      if (res.ok) {
        const data = await res.json()
        setConfig(data.config || {})
      } else {
        setConfig({})
      }
      setAppState('ready')
    } catch (error) {
      console.error("Erro ao carregar manifesto", error)
    }
  }

  const handleProvisioned = (newId, newToken) => {
    setGatewayId(newId)
    updateToken(newToken)
    loadManifest(newId)
  }

  const saveManifest = async (newConfig) => {
    const activeToken = tokenRef.current;
    
    if (!activeToken) {
      alert("Acesso negado.")
      return false
    }

    const authHeader = activeToken.startsWith('Bearer') ? activeToken : `Bearer ${activeToken}`;

    try {
      const res = await fetch('/api/config/manifest', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': authHeader
        },
        body: JSON.stringify({ gateway_id: gatewayId, config: newConfig })
      })

      if (res.ok) {
        setConfig(newConfig)
        return true
      } else {
        alert("Sessão expirada. Volte a inserir o PIN.")
        updateToken(null)
        return false
      }
    } catch (error) {
      return false
    }
  }

  if (appState === 'booting') return <div style={{ padding: '50px', textAlign: 'center' }}>A carregar...</div>
  if (appState === 'error') return <div style={{ padding: '50px', textAlign: 'center' }}>Falha na API.</div>
  if (appState === 'unprovisioned') return <EdgeProvisioning onProvisioned={handleProvisioned} />

  const isSetup = !config.plant_model;

  return (
    <div style={{ flex: 1, width: '100%', backgroundColor: '#f1f5f9', display: 'flex', flexDirection: 'column' }}>
      {isSetup ? (
        <SetupWizard currentConfig={config} onSave={saveManifest} />
      ) : (
        <Dashboard 
          config={config} 
          onSave={saveManifest} 
          gatewayId={gatewayId} 
          token={token} 
          setToken={updateToken}
        />
      )}
    </div>
  )
}

export default App