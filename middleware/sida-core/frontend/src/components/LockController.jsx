import { useState } from 'react'

export default function LockController({ isUnlocked, onUnlock, onLock }) {
  const [showModal, setShowModal] = useState(false)
  const [pin, setPin] = useState('')

  const handleUnlock = async () => {
    const res = await fetch('/api/auth/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin })
    })
    if (res.ok) {
      onUnlock()
      setShowModal(false)
      setPin('')
    } else {
      alert('PIN Inválido!')
    }
  }

  return (
    <>
      <button onClick={() => isUnlocked ? onLock() : setShowModal(true)} style={styles.lockBtn(isUnlocked)}>
        {isUnlocked ? 'Modo Edição Ativo' : 'Bloqueado (PIN)'}
      </button>

      {showModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <h3>Acesso de Engenharia</h3>
            <input type="password" placeholder="PIN" value={pin} onChange={e => setPin(e.target.value)} style={styles.input} />
            <button onClick={handleUnlock} style={styles.btn}>Desbloquear</button>
            <button onClick={() => setShowModal(false)} style={{...styles.btn, background: '#cbd5e1'}}>Cancelar</button>
          </div>
        </div>
      )}
    </>
  )
}

const styles = {
  lockBtn: (unlocked) => ({ padding: '8px 16px', borderRadius: '6px', border: 'none', background: unlocked ? '#f59e0b' : '#64748b', color: 'white', cursor: 'pointer', fontWeight: 'bold' }),
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  modal: { background: 'white', padding: '20px', borderRadius: '8px', width: '300px' },
  input: { width: '100%', padding: '10px', marginBottom: '10px', boxSizing: 'border-box' },
  btn: { width: '100%', padding: '10px', background: '#2563eb', color: 'white', border: 'none', cursor: 'pointer', marginBottom: '5px' }
}