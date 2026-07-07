import { useState } from 'react'

export default function EdgeProvisioning({ onProvisioned }) {
  const [gatewayId, setGatewayId] = useState('')
  const [pin, setPin] = useState('')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  const handleSetup = async (e) => {
    e.preventDefault()
    setLoading(true)
    setErro('')

    try {
      const resSetup = await fetch('/api/system/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gateway_id: gatewayId || `sida_edge_${Math.floor(100000 + Math.random() * 900000)}`, pin })
      })

      if (!resSetup.ok) throw new Error('Falha ao registar identidade no Edge.')
      const setupData = await resSetup.json()

      const resAuth = await fetch('/api/auth/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
      })

      if (!resAuth.ok) throw new Error('Falha na autenticação automática.')
      const authData = await resAuth.json()

      onProvisioned(setupData.gateway_id, authData.token)
      
    } catch (error) {
      setErro(error.message)
    } finally {
      setLoading(false)
    }
  }

  const styles = {
    wrapper: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0f172a', padding: '20px' },
    card: { backgroundColor: 'white', padding: '40px', borderRadius: '16px', width: '100%', maxWidth: '500px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' },
    input: { width: '100%', padding: '14px', borderRadius: '8px', border: '2px solid #e2e8f0', fontSize: '16px', marginBottom: '20px', boxSizing: 'border-box' },
    btn: { width: '100%', padding: '16px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '8px', fontSize: '18px', fontWeight: 'bold', cursor: 'pointer' }
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={{ margin: '0 0 10px 0', color: '#0f172a', fontSize: '28px' }}>Provisionamento SIDA</h1>
        <p style={{ margin: '0 0 30px 0', color: '#64748b' }}>Este equipamento encontra-se em modo de fábrica. Defina a identidade do nó Edge e a chave de segurança local.</p>
        
        {erro && <div style={{ padding: '10px', backgroundColor: '#fee2e2', color: '#991b1b', borderRadius: '8px', marginBottom: '20px' }}>{erro}</div>}

        <form onSubmit={handleSetup}>
          <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>ID do Gateway (Opcional)</label>
          <input style={styles.input} placeholder="Ex: sida_edge_recife_01" value={gatewayId} onChange={e => setGatewayId(e.target.value.toLowerCase().replace(/\s/g, '_'))} />

          <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>PIN de Engenharia (Acesso SCADA)</label>
          <input style={styles.input} type="password" required pattern="[0-9]*" inputMode="numeric" placeholder="Apenas números (ex: 8520)" value={pin} onChange={e => setPin(e.target.value)} />

          <button type="submit" style={styles.btn} disabled={loading}>
            {loading ? 'A inicializar Hardware...' : 'Gravar Identidade Segura'}
          </button>
        </form>
      </div>
    </div>
  )
}