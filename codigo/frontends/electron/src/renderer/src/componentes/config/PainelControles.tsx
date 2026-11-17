import { useEffect, useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { jogoEmAndamento, listaTrabalhos } from '../../estado/trabalhos'
import { confirmar } from '../ui/Confirmacao'

interface Props {
  aoAvisar: AoAvisar
}

interface Pad {
  nome?: string
  familia?: string
  xinput?: boolean
}

interface ListaControles {
  pads?: Pad[]
  presets?: string[]
  tipos?: Array<{ tipo: string; nome: string }>
}

/**
 * Perfis de controle do Azahar: pads conectados, presets do Hub (fotografar o
 * perfil atual / aplicar com confirmação), mapa gerado por tipo e teste ao vivo.
 */
export function PainelControles({ aoAvisar }: Props) {
  const [pads, setPads] = useState<Pad[]>([])
  const [presets, setPresets] = useState<string[]>([])
  const [tipos, setTipos] = useState<Array<{ tipo: string; nome: string }>>([])
  const [preset, setPreset] = useState('')
  const [tipo, setTipo] = useState('')
  const [novo, setNovo] = useState('')
  const [leitura, setLeitura] = useState('')
  const [ocupado, setOcupado] = useState(false)

  const aplicarLista = (r: ListaControles) => {
    if (Array.isArray(r.pads)) setPads(r.pads)
    if (Array.isArray(r.presets)) {
      const lista = r.presets
      setPresets(lista)
      setPreset((atual) => (lista.includes(atual) ? atual : (lista[0] ?? '')))
    }
    if (Array.isArray(r.tipos)) {
      const lista = r.tipos
      setTipos(lista)
      setTipo((atual) => atual || (lista[0]?.tipo ?? ''))
    }
  }

  const carregar = async () => {
    try {
      aplicarLista(await window.tucoteca.chamar<ListaControles>('controles.listar'))
    } catch (falha) {
      aoAvisar(`Controles: ${textoDeFalha(falha)}`, 'atencao')
    }
  }

  useEffect(() => {
    void carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga única
  }, [])

  const agir = async (metodo: string, params: Record<string, unknown>, sucesso: string) => {
    setOcupado(true)
    try {
      aplicarLista(await window.tucoteca.chamar<ListaControles>(metodo, params))
      aoAvisar(sucesso)
      return true
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
      return false
    } finally {
      setOcupado(false)
    }
  }

  const fotografar = async () => {
    const nome = novo.trim()
    if (nome === '') return aoAvisar('Dê um nome ao preset.', 'atencao')
    if (await agir('controles.fotografar', { nome }, `Perfil atual salvo como "${nome}".`)) setNovo('')
  }

  const aplicar = async () => {
    if (preset === '') return
    if (!(await confirmar({ titulo: 'Aplicar perfil de controles', texto: `O preset "${preset}" sobrescreve o perfil de controles atual do Azahar.`, confirmar: 'Aplicar' }))) return
    await agir('controles.aplicar', { nome: preset }, `Preset "${preset}" aplicado.`)
  }

  const ler = async () => {
    try {
      const r = await window.tucoteca.chamar<{ resumo?: string }>('controles.estado')
      setLeitura(String(r?.resumo ?? '—'))
    } catch (falha) {
      setLeitura('')
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const jogando = jogoEmAndamento(listaTrabalhos.value) !== null

  return (
    <div class="form-config painel-paridade">
      <h2>Controles</h2>
      <p class="sub">
        {pads.length === 0
          ? 'Nenhum controle detectado.'
          : `Conectado(s): ${pads.map((p) => p.nome ?? 'controle').join(', ')}.`}{' '}
        <button type="button" class="acao" onClick={() => void carregar()}>
          Detectar de novo
        </button>
      </p>

      <h4>Presets de perfil</h4>
      <div class="detalhe-linha">
        <select value={preset} disabled={ocupado || presets.length === 0} onChange={(e) => setPreset((e.target as HTMLSelectElement).value)}>
          {presets.length === 0 && <option value="">Nenhum preset salvo</option>}
          {presets.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button type="button" class="acao" disabled={ocupado || jogando || preset === ''} onClick={() => void aplicar()}>
          Aplicar no Azahar
        </button>
      </div>
      <div class="detalhe-linha">
        <input value={novo} placeholder="nome do preset" onInput={(e) => setNovo((e.target as HTMLInputElement).value)} />
        <button type="button" class="acao" disabled={ocupado} onClick={() => void fotografar()}>
          Salvar perfil atual
        </button>
      </div>

      <h4>Gerar mapa padrão</h4>
      <div class="detalhe-linha">
        <select value={tipo} disabled={ocupado || tipos.length === 0} onChange={(e) => setTipo((e.target as HTMLSelectElement).value)}>
          {tipos.map((t) => (
            <option key={t.tipo} value={t.tipo}>
              {t.nome}
            </option>
          ))}
        </select>
        <button
          type="button"
          class="acao"
          disabled={ocupado || tipo === ''}
          onClick={() => void agir('controles.gerar', { tipo }, 'Mapa gerado e salvo como preset (o perfil atual não muda).')}
        >
          Gerar
        </button>
      </div>

      <h4>Testar controle</h4>
      <div class="detalhe-linha">
        <button type="button" class="acao" onClick={() => void ler()}>
          Ler agora
        </button>
        {leitura !== '' && <code>{leitura}</code>}
      </div>
      {jogando && <p class="sub">Feche o jogo aberto para aplicar presets.</p>}
    </div>
  )
}
