import { useEffect, useState } from 'preact/hooks'
import {
  FILTROS_PACOTE,
  normalizarEmulacao,
  resumoTextura,
  validarCheat,
  type EstadoEmulacao,
} from '../estado/emulacao'
import { textoDeFalha } from '../estado/notificacoes'
import { confirmar } from './Confirmacao'

interface Props {
  id: number
  /** Jogo aberto: a ponte recusa mudanças; os botões ficam desabilitados. */
  bloqueado: boolean
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

/**
 * Mods, cheats, texturas HD e presets do Azahar para um jogo 3DS (o antigo
 * `qt_emulacao`). Remover e aplicar preset pedem confirmação antes de chamar.
 */
export function PainelEmulacao({ id, bloqueado, aoAvisar }: Props) {
  const [estado, setEstado] = useState<EstadoEmulacao | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [cheatNome, setCheatNome] = useState('')
  const [cheatCodigo, setCheatCodigo] = useState('')
  const [preset, setPreset] = useState('')
  const [novoPreset, setNovoPreset] = useState('')

  useEffect(() => {
    let vivo = true
    void (async () => {
      try {
        const r = normalizarEmulacao(await window.tucoteca.chamar('emulacao.jogo', { id }))
        if (vivo) {
          setEstado(r)
          setPreset(r.presets[0] ?? '')
        }
      } catch (falha) {
        if (vivo) aoAvisar(`Emulação: ${textoDeFalha(falha)}`, 'atencao')
      }
    })()
    return () => {
      vivo = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- aoAvisar é inline no App
  }, [id])

  /** Chama a ponte, aplica o estado novo e avisa; erros viram aviso. */
  const agir = async (metodo: string, params: Record<string, unknown>, sucesso: string) => {
    setOcupado(true)
    try {
      const r = await window.tucoteca.chamar(metodo, params)
      if (metodo !== 'emulacao.preset') setEstado(normalizarEmulacao(r))
      aoAvisar(sucesso)
      return true
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
      return false
    } finally {
      setOcupado(false)
    }
  }

  if (estado === null) return <p class="sub">Lendo mods, cheats e texturas…</p>
  if (estado.erro !== '') return <p class="sub">{estado.erro}</p>

  const travado = ocupado || bloqueado

  const importarMod = async (pasta: boolean) => {
    const arquivo = pasta
      ? await window.tucoteca.escolherPasta()
      : await window.tucoteca.escolherArquivo(FILTROS_PACOTE)
    if (arquivo) await agir('emulacao.mod', { id, acao: 'importar', arquivo }, 'Mod importado.')
  }

  const removerMod = async (nome: string) => {
    if (!(await confirmar({ titulo: 'Remover mod', texto: `O mod "${nome}" será apagado da biblioteca. Não há desfazer.`, confirmar: 'Remover', perigo: true }))) return
    await agir('emulacao.mod', { id, acao: 'remover', nome }, `Mod "${nome}" removido.`)
  }

  const adicionarCheat = async () => {
    const erro = validarCheat(cheatNome, cheatCodigo)
    if (erro !== null) return aoAvisar(erro, 'atencao')
    const ok = await agir(
      'emulacao.cheat',
      { id, acao: 'adicionar', nome: cheatNome.trim(), codigo: cheatCodigo },
      'Cheat salvo (desligado — ligue quando quiser).',
    )
    if (ok) {
      setCheatNome('')
      setCheatCodigo('')
    }
  }

  const removerCheat = async (nome: string) => {
    if (!(await confirmar({ titulo: 'Remover cheat', texto: `O cheat "${nome}" será removido deste jogo. Não há desfazer.`, confirmar: 'Remover', perigo: true }))) return
    await agir('emulacao.cheat', { id, acao: 'remover', nome }, `Cheat "${nome}" removido.`)
  }

  const instalarTextura = async () => {
    const arquivo = await window.tucoteca.escolherArquivo(FILTROS_PACOTE)
    if (arquivo) await agir('emulacao.textura', { id, acao: 'instalar', arquivo }, 'Texturas instaladas.')
  }

  const aplicarPreset = async () => {
    if (preset === '') return
    const texto = `O preset "${preset}" sobrescreve a configuração atual do Azahar. Feche o emulador antes.`
    if (!(await confirmar({ titulo: 'Aplicar preset', texto, confirmar: 'Aplicar' }))) return
    await agir('emulacao.preset', { acao: 'aplicar', nome: preset }, `Preset "${preset}" aplicado.`)
  }

  const salvarPreset = async () => {
    const nome = novoPreset.trim()
    if (nome === '') return aoAvisar('Dê um nome ao preset.', 'atencao')
    setOcupado(true)
    try {
      const r = await window.tucoteca.chamar<{ presets?: string[] }>('emulacao.preset', { acao: 'salvar', nome })
      setEstado((atual) => (atual === null ? atual : { ...atual, presets: Array.isArray(r?.presets) ? r.presets : atual.presets }))
      setPreset(nome)
      setNovoPreset('')
      aoAvisar(`Preset "${nome}" salvo a partir da configuração atual.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div class="painel-emulacao">
      {bloqueado && <p class="aviso">Feche o jogo para mudar mods, cheats, texturas ou presets.</p>}
      <p class="sub">Title ID {estado.tid}</p>

      <h4>Mods</h4>
      {estado.mods.length === 0 ? (
        <p class="sub">Nenhum mod na biblioteca deste jogo.</p>
      ) : (
        <ul class="lista-simples">
          {estado.mods.map((m) => (
            <li key={m.nome}>
              <label>
                <input
                  type="checkbox"
                  checked={m.ativo}
                  disabled={travado}
                  onChange={() => void agir('emulacao.mod', { id, acao: 'alternar', nome: m.nome }, m.ativo ? `Mod "${m.nome}" desligado.` : `Mod "${m.nome}" ligado.`)}
                />
                {m.nome}
              </label>
              <button type="button" class="acao perigo" disabled={travado} onClick={() => void removerMod(m.nome)}>
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
      <div class="detalhe-linha">
        <label>
          <input
            type="checkbox"
            checked={estado.mods_off}
            disabled={travado}
            onChange={() => void agir('emulacao.mod', { id, acao: 'desligar_todos' }, estado.mods_off ? 'Mods voltam a valer ao jogar.' : 'Mods desligados para este jogo.')}
          />
          Jogar sem mods
        </label>
        <button type="button" class="acao" disabled={travado} onClick={() => void importarMod(false)}>
          Importar mod (.zip)
        </button>
        <button type="button" class="acao" disabled={travado} onClick={() => void importarMod(true)}>
          Importar pasta
        </button>
      </div>

      <h4>Cheats</h4>
      {estado.cheats.length === 0 ? (
        <p class="sub">Nenhum cheat cadastrado.</p>
      ) : (
        <ul class="lista-simples">
          {estado.cheats.map((c) => (
            <li key={c.nome}>
              <label>
                <input
                  type="checkbox"
                  checked={c.ativo}
                  disabled={travado}
                  onChange={() => void agir('emulacao.cheat', { id, acao: 'alternar', nome: c.nome }, c.ativo ? `Cheat "${c.nome}" desligado.` : `Cheat "${c.nome}" ligado.`)}
                />
                {c.nome}
              </label>
              <button type="button" class="acao perigo" disabled={travado} onClick={() => void removerCheat(c.nome)}>
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
      <div class="detalhe-form">
        <label>
          Nome do cheat
          <input value={cheatNome} onInput={(e) => setCheatNome((e.target as HTMLInputElement).value)} />
        </label>
        <label>
          Código
          <textarea
            value={cheatCodigo}
            placeholder="00112233 44556677"
            onInput={(e) => setCheatCodigo((e.target as HTMLTextAreaElement).value)}
          />
        </label>
      </div>
      <button type="button" class="acao" disabled={travado} onClick={() => void adicionarCheat()}>
        Adicionar cheat
      </button>

      <h4>Texturas HD</h4>
      <div class="detalhe-linha">
        <span>{resumoTextura(estado.textura)}</span>
        {estado.textura.instalado && (
          <button type="button" class="acao" disabled={travado} onClick={() => void agir('emulacao.textura', { id, acao: 'alternar' }, estado.textura.ativo ? 'Texturas desligadas.' : 'Texturas ligadas.')}>
            {estado.textura.ativo ? 'Desligar' : 'Ligar'}
          </button>
        )}
        <button type="button" class="acao" disabled={travado} onClick={() => void instalarTextura()}>
          Instalar pacote
        </button>
      </div>

      <h4>Presets do Azahar</h4>
      <div class="detalhe-linha">
        <select value={preset} disabled={travado || estado.presets.length === 0} onChange={(e) => setPreset((e.target as HTMLSelectElement).value)}>
          {estado.presets.length === 0 && <option value="">Nenhum preset salvo</option>}
          {estado.presets.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button type="button" class="acao" disabled={travado || preset === ''} onClick={() => void aplicarPreset()}>
          Aplicar
        </button>
      </div>
      <div class="detalhe-linha">
        <input value={novoPreset} placeholder="nome do novo preset" onInput={(e) => setNovoPreset((e.target as HTMLInputElement).value)} />
        <button type="button" class="acao" disabled={travado} onClick={() => void salvarPreset()}>
          Salvar configuração atual
        </button>
      </div>
    </div>
  )
}
