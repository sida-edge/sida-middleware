import { useState } from 'react'

export default function SetupWizard({ currentConfig, onSave }) {
  const [enterprise, setEnterprise] = useState('')
  const [site, setSite] = useState('')
  const [loading, setLoading] = useState(false)

  const handleFinishSetup = async (e) => {
    e.preventDefault()
    setLoading(true)

    const plantModel = {
      enterprise: enterprise.trim(),
      site: site.trim(),
      areas: {}
    }

    const newConfig = {
      ...currentConfig,
      plant_model: plantModel,
      devices: currentConfig.devices || {}
    }

    await onSave(newConfig)
    setLoading(false)
  }

  const styles = {
    wrapper: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' },
    card: { backgroundColor: 'white', padding: '40px', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)', width: '100%', maxWidth: '500px' },
    title: { margin: '0 0 10px 0', fontSize: '28px', color: '#0f172a' },
    subtitle: { margin: '0 0 30px 0', color: '#64748b', fontSize: '16px', lineHeight: '1.5' },
    input: { width: '100%', padding: '12px 16px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '16px', backgroundColor: '#f8fafc', marginBottom: '20px', boxSizing: 'border-box' },
    btn: { width: '100%', padding: '16px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '8px', fontSize: '18px', fontWeight: 'bold', cursor: 'pointer', transition: 'background 0.2s' }
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>Inicialização do Edge</h1>
        <p style={styles.subtitle}>
          Defina a identidade raiz deste Gateway. A estrutura interna (Áreas e Linhas) poderá ser construída gradualmente no Dashboard.
        </p>

        <form onSubmit={handleFinishSetup}>
          <label style={{ display: 'block', fontWeight: '600', marginBottom: '8px' }}>Empresa (Enterprise)</label>
          <input style={styles.input} required placeholder="Ex: Grupo SENAI" value={enterprise} onChange={e => setEnterprise(e.target.value)} />

          <label style={{ display: 'block', fontWeight: '600', marginBottom: '8px' }}>Fábrica (Site)</label>
          <input style={styles.input} required placeholder="Ex: Planta Recife" value={site} onChange={e => setSite(e.target.value)} />

          <button type="submit" style={styles.btn} disabled={loading}>
            {loading ? 'A inicializar...' : 'Criar Fundação'}
          </button>
        </form>
      </div>
    </div>
  )
}