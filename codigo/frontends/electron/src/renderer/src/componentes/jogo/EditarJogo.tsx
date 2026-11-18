import { useState } from 'preact/hooks'
import { candidatosDeCapa, errosDeCapa, type CandidatoCapa } from '../../estado/capas'
import { STATUS_JOGOS, normalizarEtiquetas, validarHoras, validarNota, type JogoDaLista } from '../../estado/jogos'
import { textoDeFalha } from '../../estado/notificacoes'
import type { PaginaJogo } from '../../estado/paginaJogo'
import { ehMac } from '../../plataforma'

type Avisar = (texto: string, tom?: 'info' | 'atencao') => void

interface Props {
  id: number
  pagina: PaginaJogo
  aoMudou: () => void
  aoAvisar: Avisar
}

interface Formulario {
  titulo: string
  executable_path: string
  launch_options: string
  status: string
  nota: string
  etiquetas: string
}

function deJogo(jogo: JogoDaLista): Formulario {
  const status = String(jogo.status ?? '')
  return {
    titulo: String(jogo.titulo ?? ''),
    executable_path: String(jogo.executable_path ?? ''),
    launch_options: String(jogo.launch_options ?? ''),
    status: STATUS_JOGOS.some((chave) => chave === status) ? status : 'backlog',
    nota: jogo.nota === null || jogo.nota === undefined ? '' : String(jogo.nota),
    etiquetas: String(jogo.etiquetas ?? ''),
  }
}

/** Aba Editar: dados do jogo, horas, observações, capa, arte e os dados dos provedores. */
export function EditarJogo({ id, pagina, aoMudou, aoAvisar }: Props) {
  return (
    <div class="editar-jogo">
      <DadosDoJogo id={id} jogo={pagina.jogo} aoMudou={aoMudou} aoAvisar={aoAvisar} />
      <CapaEArte id={id} pagina={pagina} aoMudou={aoMudou} aoAvisar={aoAvisar} />
      <DadosDosProvedores id={id} pagina={pagina} aoMudou={aoMudou} aoAvisar={aoAvisar} />
    </div>
  )
}

function DadosDoJogo({ id, jogo, aoMudou, aoAvisar }: { id: number; jogo: JogoDaLista; aoMudou: () => void; aoAvisar: Avisar }) {
  const [form, setForm] = useState<Formulario>(() => deJogo(jogo))
  const [horas, setHoras] = useState('')
  const [observacoes, setObservacoes] = useState(String(jogo.observacoes ?? ''))
  const campo = (chave: keyof Formulario) => (evento: { target: EventTarget | null }) => {
    const valor = (evento.target as HTMLInputElement | HTMLSelectElement).value
    setForm((atual) => ({ ...atual, [chave]: valor }))
  }

  const salvar = async () => {
    const titulo = form.titulo.trim()
    if (titulo === '') return aoAvisar('O título não pode ficar vazio.', 'atencao')
    const nota = validarNota(form.nota)
    if (form.nota.trim() !== '' && nota === null) return aoAvisar('Nota deve ser um número inteiro de 0 a 10.', 'atencao')
    try {
      await window.tucoteca.chamar('jogo.salvar', {
        id,
        dados: {
          titulo,
          executable_path: form.executable_path.trim(),
          launch_options: form.launch_options.trim(),
          status: form.status,
          nota,
          etiquetas: normalizarEtiquetas(form.etiquetas),
        },
      })
      aoAvisar('Jogo salvo.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const registrarHoras = async () => {
    const valor = validarHoras(horas)
    if (valor === null) return aoAvisar('Informe horas maior que zero (ex.: 1,5).', 'atencao')
    try {
      await window.tucoteca.chamar('jogo.registrar_horas', { id, horas: valor })
      setHoras('')
      aoAvisar(`${valor} h registradas.`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const salvarObservacoes = async () => {
    try {
      await window.tucoteca.chamar('jogo.observacoes', { id, texto: observacoes })
      aoAvisar('Observações salvas.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <>
      <section class="bloco-jogo">
        <h3>Jogo</h3>
        <div class="detalhe-form grade-2">
          <label>
            Título
            <input value={form.titulo} onInput={campo('titulo')} />
          </label>
          <label>
            Status
            <select value={form.status} onChange={campo('status')}>
              {STATUS_JOGOS.map((chave) => (
                <option key={chave} value={chave}>
                  {chave}
                </option>
              ))}
            </select>
          </label>
          <label>
            Executável
            <input value={form.executable_path} onInput={campo('executable_path')} placeholder={ehMac() ? '/Applications/Jogo.app' : 'C:\\caminho\\jogo.exe'} />
          </label>
          <label>
            Argumentos
            <input value={form.launch_options} onInput={campo('launch_options')} />
          </label>
          <label>
            Nota (0–10)
            <input value={form.nota} onInput={campo('nota')} placeholder="ex.: 7" />
          </label>
          <label>
            Etiquetas
            <input value={form.etiquetas} onInput={campo('etiquetas')} placeholder="rpg, canon" />
          </label>
        </div>
        <button type="button" class="acao primaria" onClick={() => void salvar()}>
          Salvar
        </button>
      </section>
      <section class="bloco-jogo">
        <h3>Registrar horas</h3>
        <div class="detalhe-linha">
          <input value={horas} onInput={(e) => setHoras((e.target as HTMLInputElement).value)} placeholder="ex.: 1,5" />
          <button type="button" class="acao" onClick={() => void registrarHoras()}>
            Registrar
          </button>
        </div>
      </section>
      <section class="bloco-jogo">
        <h3>Observações</h3>
        <textarea value={observacoes} onInput={(e) => setObservacoes((e.target as HTMLTextAreaElement).value)} />
        <button type="button" class="acao" onClick={() => void salvarObservacoes()}>
          Salvar observações
        </button>
      </section>
    </>
  )
}

const TIPOS_ARTE: Array<{ tipo: 'hero' | 'logo' | 'icone'; nome: string }> = [
  { tipo: 'hero', nome: 'Fundo (hero)' },
  { tipo: 'logo', nome: 'Logo' },
  { tipo: 'icone', nome: 'Ícone' },
]

interface CandidatoArte {
  url: string
  preview: string
  fonte: string
}

function CapaEArte({ id, pagina, aoMudou, aoAvisar }: Props) {
  const [capas, setCapas] = useState<CandidatoCapa[]>([])
  const [arte, setArte] = useState<{ tipo: string; itens: CandidatoArte[] } | null>(null)
  const [ocupado, setOcupado] = useState(false)

  const comTrava = async (fn: () => Promise<void>) => {
    setOcupado(true)
    try {
      await fn()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const buscarCapas = () =>
    comTrava(async () => {
      const r = await window.tucoteca.chamar('capas.buscar', { categoria: 'jogos', id, provedor: '', atualizar: false })
      const lista = candidatosDeCapa(r)
      setCapas(lista)
      const erros = errosDeCapa(r)
      if (lista.length > 0) aoAvisar(`${lista.length} capa(s) encontrada(s). Clique em uma para aplicar.`)
      else aoAvisar(erros[0] ? `Nenhuma capa encontrada (${erros[0]}).` : 'Nenhuma capa encontrada.', 'atencao')
    })

  const aplicarCapa = (candidato: Record<string, unknown>) =>
    comTrava(async () => {
      await window.tucoteca.chamar('capas.aplicar', { categoria: 'jogos', id, candidato })
      aoAvisar('Capa aplicada.')
      setCapas([])
      aoMudou()
    })

  const capaLibretro = () =>
    comTrava(async () => {
      await window.tucoteca.chamar('capas.libretro', { id })
      aoAvisar('Capa do acervo libretro aplicada.')
      aoMudou()
    })

  const buscarArte = (tipo: string) =>
    comTrava(async () => {
      const r = await window.tucoteca.chamar<{ itens?: CandidatoArte[]; erros?: string[] }>('jogo.artes_buscar', { id, tipo })
      const itens = Array.isArray(r?.itens) ? r.itens : []
      setArte({ tipo, itens })
      if (itens.length === 0) aoAvisar(r?.erros?.[0] ?? 'Nenhuma arte encontrada.', 'atencao')
    })

  const aplicarArte = (tipo: string, url: string) =>
    comTrava(async () => {
      await window.tucoteca.chamar('jogo.arte_aplicar', { id, tipo, url })
      aoAvisar('Arte aplicada (os provedores não trocam mais esta).')
      setArte(null)
      aoMudou()
    })

  return (
    <section class="bloco-jogo">
      <h3>Capa e arte</h3>
      <div class="detalhe-linha">
        <button type="button" class="acao" onClick={() => void buscarCapas()} disabled={ocupado}>
          Buscar capas
        </button>
        {String(pagina.jogo.launch_options ?? '').trim() !== '' && (
          <button type="button" class="acao" onClick={() => void capaLibretro()} disabled={ocupado} title="Capa de ROM pelo acervo libretro-thumbnails">
            Capa libretro
          </button>
        )}
        {TIPOS_ARTE.map((t) => (
          <button key={t.tipo} type="button" class="acao" onClick={() => void buscarArte(t.tipo)} disabled={ocupado}>
            Trocar {t.nome.toLowerCase()}
          </button>
        ))}
      </div>
      {capas.length > 0 && (
        <div class="capas-candidatas">
          {capas.map((c, i) => {
            const url = window.tucoteca.imagemUrl(c.preview)
            return (
              <button key={i} type="button" class="capa-candidata" title={`Aplicar capa${c.fonte ? ` de ${c.fonte}` : ''}`} onClick={() => void aplicarCapa(c.original)}>
                {url !== '' ? <img src={url} alt="" loading="lazy" /> : <span class="capa-vazia">{i + 1}</span>}
                <span>{c.fonte || `Capa ${i + 1}`}</span>
              </button>
            )
          })}
        </div>
      )}
      {arte !== null && arte.itens.length > 0 && (
        <div class={`artes-candidatas tipo-${arte.tipo}`}>
          {arte.itens.map((a) => (
            <button key={a.url} type="button" class="arte-candidata" onClick={() => void aplicarArte(arte.tipo, a.url)} title={`Aplicar (${a.fonte})`}>
              <img src={a.preview} alt="" loading="lazy" onError={(e) => ((e.target as HTMLImageElement).style.visibility = 'hidden')} />
              <span>{a.fonte}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

interface FormMeta {
  descricao: string
  generos: string
  desenvolvedora: string
  publicadora: string
  lancamento: string
  steam_appid: string
  retro_id: string
}

function DadosDosProvedores({ id, pagina, aoMudou, aoAvisar }: Props) {
  const m = pagina.meta
  const inicial: FormMeta = {
    descricao: m.descricao,
    generos: m.generos.join(', '),
    desenvolvedora: m.desenvolvedora,
    publicadora: m.publicadora,
    lancamento: m.lancamento,
    steam_appid: m.steam_appid,
    retro_id: m.retro_id,
  }
  const [form, setForm] = useState<FormMeta>(inicial)
  const campo = (chave: keyof FormMeta) => (e: { target: EventTarget | null }) =>
    setForm((atual) => ({ ...atual, [chave]: (e.target as HTMLInputElement).value }))

  const salvar = async () => {
    const mudados = Object.fromEntries(
      (Object.keys(form) as Array<keyof FormMeta>).filter((k) => form[k].trim() !== inicial[k].trim()).map((k) => [k, form[k].trim()]),
    )
    if (Object.keys(mudados).length === 0) return aoAvisar('Nada mudou.')
    try {
      await window.tucoteca.chamar('jogo.meta_salvar', { id, campos: mudados })
      aoAvisar('Dados salvos. Campos editados à mão não são trocados pelos provedores.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const travado = (k: string) => (m.travado.includes(k) ? ' 🔒' : '')
  return (
    <section class="bloco-jogo">
      <h3>Dados dos provedores</h3>
      <p class="sub">Corrija o que veio errado. O que você editar fica travado (🔒); apagar o campo destrava.</p>
      <div class="detalhe-form grade-2">
        <label>
          Desenvolvedora{travado('desenvolvedora')}
          <input value={form.desenvolvedora} onInput={campo('desenvolvedora')} />
        </label>
        <label>
          Publicadora{travado('publicadora')}
          <input value={form.publicadora} onInput={campo('publicadora')} />
        </label>
        <label>
          Lançamento{travado('lancamento')}
          <input value={form.lancamento} onInput={campo('lancamento')} />
        </label>
        <label>
          Gêneros{travado('generos')}
          <input value={form.generos} onInput={campo('generos')} placeholder="RPG, Ação" />
        </label>
        <label>
          App ID Steam{travado('steam_appid')}
          <input value={form.steam_appid} onInput={campo('steam_appid')} inputMode="numeric" />
        </label>
        <label>
          Id RetroAchievements{travado('retro_id')}
          <input value={form.retro_id} onInput={campo('retro_id')} inputMode="numeric" placeholder="número na URL do jogo" />
        </label>
      </div>
      <label class="campo-largo">
        Descrição{travado('descricao')}
        <textarea value={form.descricao} onInput={campo('descricao')} />
      </label>
      <button type="button" class="acao" onClick={() => void salvar()}>
        Salvar dados
      </button>
    </section>
  )
}
