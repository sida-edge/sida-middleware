export default function AdvancedEditor({ configJson, setConfigJson, isEditing, setIsEditing, guardarManifesto, mensagem }) {
  return (
    <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <p style={{ margin: '0 0 15px 0', color: '#64748b' }}>Atenção: Modificações manuais afetam diretamente o Motor de Regras.</p>
      <textarea
        style={{ width: '100%', height: '400px', fontFamily: 'monospace', padding: '15px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#1e293b', color: '#38bdf8', boxSizing: 'border-box' }}
        value={configJson}
        onChange={(e) => {
          setConfigJson(e.target.value)
          setIsEditing(true)
        }}
        spellCheck="false"
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '15px' }}>
        <span style={{ color: mensagem.type === 'error' ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>{mensagem.text}</span>
        <button 
          onClick={guardarManifesto}
          disabled={!isEditing}
          style={{ padding: '10px 20px', backgroundColor: isEditing ? '#2563eb' : '#94a3b8', color: 'white', border: 'none', borderRadius: '8px', cursor: isEditing ? 'pointer' : 'not-allowed', fontWeight: 'bold' }}
        >
          Gravar Alterações
        </button>
      </div>
    </div>
  )
}