import { useState, useEffect, useRef } from 'react' // 1. Adicione o useRef aqui!
import EdgeProvisioning from './components/EdgeProvisioning'
import SetupWizard from './components/SetupWizard'
import Dashboard from './components/Dashboard'

function App() {
  const [appState, setAppState] = useState('booting') 
  const [gatewayId, setGatewayId] = useState(null)
  const [config, setConfig] = useState(null)
  
  // 2. O Estado visual (para o React desenhar a tela) começa SEMPRE trancado (null)
  const [token, setToken] = useState(null)
  // 3. O Cofre de RAM (para resolver o bug do Go sem usar disco local)
  const tokenRef = useRef(null) 

  // Função centralizada para atualizar a chave com segurança
  const atualizarToken = (novoToken) => {
    setToken(novoToken)
    tokenRef.current = novoToken 
  }

  useEffect(() => {
    verificarIdentidade()
  }, [])

  const verificarIdentidade = async () => {
    // ... (Mantenha o seu código verificarIdentidade igual)
    try {
      const res = await fetch('/api/system/info')
      if (!res.ok) throw new Error('Servidor Go respondeu com erro.')
      const data = await res.json()
      if (data.provisioned) {
        setGatewayId(data.gateway_id)
        carregarManifesto(data.gateway_id)
      } else {
        setAppState('unprovisioned')
      }
    } catch (error) {
      setAppState('error')
    }
  }

  const carregarManifesto = async (id) => {
     // ... (Mantenha o seu código carregarManifesto igual)
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

  const handleProvisioned = (novoId, novoToken) => {
    setGatewayId(novoId)
    atualizarToken(novoToken) // Usa a nova função!
    carregarManifesto(novoId)
  }

  const guardarManifesto = async (novaConfig) => {
    // 4. Lê o token diretamente do cofre em tempo real (Nunca falha!)
    const activeToken = tokenRef.current;
    
    if (!activeToken) {
      alert("Acesso negado. O Modo de Engenharia está trancado.")
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
        body: JSON.stringify({ gateway_id: gatewayId, config: novaConfig })
      })

      if (res.ok) {
        setConfig(novaConfig)
        return true
      } else {
        alert("Sessão expirada. Volte a inserir o PIN.")
        atualizarToken(null) // Tranca o sistema
        return false
      }
    } catch (error) {
      return false
    }
  }

  if (appState === 'booting') return <div style={{ padding: '50px', textAlign: 'center' }}>A carregar...</div>
  if (appState === 'error') return <div style={{ padding: '50px', textAlign: 'center' }}>Falha na API.</div>
  if (appState === 'unprovisioned') return <EdgeProvisioning onProvisioned={handleProvisioned} />

  const isDiaUm = !config.plant_model;

  return (
    <div style={{ flex: 1, width: '100%', backgroundColor: '#f1f5f9', display: 'flex', flexDirection: 'column' }}>
      {isDiaUm ? (
        <SetupWizard configAtual={config} onSave={guardarManifesto} />
      ) : (
        <Dashboard 
          config={config} 
          onSave={guardarManifesto} 
          gatewayId={gatewayId} 
          token={token} 
          setToken={atualizarToken} // Passa a nova função para o Dashboard
        />
      )}
    </div>
  )
}

export default App