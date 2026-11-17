import { useState } from 'preact/hooks'
import { dataDoSnapshot } from '../../estado/colecao'
import { tamanhoLegivel } from '../../estado/manutencao'
import { textoDeFalha } from '../../estado/notificacoes'
import { confirmar } from '../ui/Confirmacao'

interface Props {
  id: number
  bloqueado: boolean
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

interface Ferramentas {
  saves: string[]
  snapshots: Array<{ nome: string; path: string; bytes: number }>
  screenshots: Array<{ nome: string; url: string; path: string }>
  pasta_screenshots: string
}

/**
 * Saves (origens, snapshots com restauração) e screenshots do jogo. Restaurar
 * guarda o estado atual antes e valida SHA-256 no núcleo; pede confirmação.
 */
export function PainelFerramentasJogo({ id, bloqueado, aoAvisar }: Props) {
  const [dados, setDados] = useState<Ferramentas | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [novasOrigens, setNovasOrigens] = useState('')

  const carregar = async () => {
    try {
      const r = await window.tucoteca.chamar<Partial<Ferramentas>>('ferramentas.jogo', { id })
      setDados({
        saves: Array.isArray(r?.saves) ? r.saves.map(String) : [],
        snapshots: Array.isArray(r?.snapshots) ? r.snapshots : [],
        screenshots: Array.isArray(r?.screenshots) ? r.screenshots : [],
        pasta_screenshots: String(r?.pasta_screenshots ?? ''),
      })
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  if (dados === null)
    return (
      <button type="button" class="acao" onClick={() => void carregar()}>
        Ver saves e screenshots
      </button>
    )

  const snapshotAgora = async () => {
    setOcupado(true)
    try {
      await window.tucoteca.chamar('saves.snapshot', { id })
      aoAvisar('Snapshot dos saves criado.')
      await carregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const restaurar = async (s: { nome: string; path: string }) => {
    const ok = await confirmar({
      titulo: 'Restaurar saves',
      texto: `Os saves atuais serão substituídos pelo snapshot de ${dataDoSnapshot(s.nome) || s.nome}. O estado atual é guardado antes, como snapshot novo.`,
      confirmar: 'Restaurar',
      perigo: true,
    })
    if (!ok) return
    setOcupado(true)
    try {
      await window.tucoteca.chamar('saves.restaurar', { id, caminho: s.path })
      aoAvisar('Saves restaurados.')
      await carregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const configurarSaves = async () => {
    const caminhos = novasOrigens.split(',').map((c) => c.trim()).filter(Boolean)
    if (caminhos.length === 0) return aoAvisar('Informe uma ou mais pastas de saves, separadas por vírgula.', 'atencao')
    setOcupado(true)
    try {
      await window.tucoteca.chamar('saves.configurar', { id, caminhos })
      setNovasOrigens('')
      aoAvisar('Pastas de saves configuradas.')
      await carregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const abrirPasta = async () => {
    try {
      await window.tucoteca.abrirPasta(dados.pasta_screenshots)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const travado = ocupado || bloqueado

  return (
    <div class="painel-paridade">
      <h4>Saves</h4>
      {dados.saves.length === 0 ? (
        <p class="sub">Nenhuma pasta de saves configurada ainda.</p>
      ) : (
        <ul class="lista-simples">
          {dados.saves.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      )}
      <div class="detalhe-linha">
        <input
          value={novasOrigens}
          placeholder="pastas de saves, separadas por vírgula"
          aria-label="Pastas de saves"
          onInput={(e) => setNovasOrigens((e.target as HTMLInputElement).value)}
        />
        <button type="button" class="acao" disabled={ocupado} onClick={() => void configurarSaves()}>
          Definir pastas
        </button>
      </div>
      <div class="detalhe-linha">
        <button type="button" class="acao" disabled={travado || dados.saves.length === 0} onClick={() => void snapshotAgora()}>
          Criar snapshot agora
        </button>
      </div>
      {dados.snapshots.length > 0 && (
        <ul class="lista-simples">
          {dados.snapshots.map((s) => (
            <li key={s.path}>
              <span>
                {dataDoSnapshot(s.nome) || s.nome} <span class="sub">{tamanhoLegivel(s.bytes)}</span>
              </span>
              <button type="button" class="acao" disabled={travado} onClick={() => void restaurar(s)}>
                Restaurar
              </button>
            </li>
          ))}
        </ul>
      )}

      <h4>Screenshots ({dados.screenshots.length})</h4>
      {dados.screenshots.length > 0 && (
        <div class="galeria">
          {dados.screenshots.slice(0, 24).map((s) => (
            <img key={s.path} src={window.tucoteca.imagemUrl(s.url)} alt={s.nome} title={s.nome} loading="lazy" />
          ))}
        </div>
      )}
      {dados.pasta_screenshots !== '' && (
        <button type="button" class="acao" onClick={() => void abrirPasta()}>
          Abrir pasta de screenshots
        </button>
      )}
      {bloqueado && <p class="sub">Feche o jogo para criar ou restaurar snapshots.</p>}
    </div>
  )
}
