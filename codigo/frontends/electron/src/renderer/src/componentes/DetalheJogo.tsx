import { useEffect, useRef, useState } from 'preact/hooks'
import {
  STATUS_JOGOS,
  normalizarEtiquetas,
  validarHoras,
  validarNota,
  type JogoDaLista,
} from '../estado/jogos'
import { textoDeFalha } from '../estado/notificacoes'
import { jogoEmAndamento, listaTrabalhos } from '../estado/trabalhos'
import { iniciais } from './PosterCard'

interface Props {
  id: number
  revisao: number
  aoFechar: () => void
  aoMudou: () => void
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

interface Formulario {
  titulo: string
  executable_path: string
  launch_options: string
  status: string
  nota: string
  etiquetas: string
}

/** Formulário a partir do jogo lido (status inválido cai em `backlog`). */
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

/**
 * Detalhe do jogo em gaveta: capa/títulos, jogar, favoritar, editar, registrar
 * horas, observações e remover (com desfazer na barra de status do app).
 */
export function DetalheJogo({ id, revisao, aoFechar, aoMudou, aoAvisar }: Props) {
  const [jogo, setJogo] = useState<JogoDaLista | null>(null)
  const [form, setForm] = useState<Formulario | null>(null)
  const [observacoes, setObservacoes] = useState('')
  const [horas, setHoras] = useState('')
  const modalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (modalRef.current !== null) {
      const focavel = modalRef.current.querySelector<HTMLElement>('button, input, select, textarea, [tabindex]:not([tabindex="-1"])')
      focavel?.focus()
    }
  }, [jogo])
  const [conquistas, setConquistas] = useState<Array<Record<string, unknown>>>([])
  const [appidConquistas, setAppidConquistas] = useState('')
  const [regrasConquistas, setRegrasConquistas] = useState('')
  const [mostrarRegras, setMostrarRegras] = useState(false)
  const [capasCandidatas, setCapasCandidatas] = useState<Array<Record<string, unknown>>>([])
  const [savesInput, setSavesInput] = useState('')

  useEffect(() => {
    let vivo = true
    void (async () => {
      try {
        const dados = await window.tucoteca.chamar<JogoDaLista>('jogo.ler', { id })
        if (!vivo) return
        setJogo(dados)
        setForm(deJogo(dados))
        setObservacoes(String(dados.observacoes ?? ''))
      } catch (falha) {
        if (vivo) aoAvisar(`Não abri o jogo: ${textoDeFalha(falha)}`, 'atencao')
      }
    })()
    return () => {
      vivo = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- aoAvisar é inline no App
  }, [id, revisao])

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') {
        evento.stopPropagation()
        aoFechar()
      }
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [aoFechar])

  const aplicar = (dados: JogoDaLista) => {
    setJogo(dados)
    setForm(deJogo(dados))
    setObservacoes(String(dados.observacoes ?? ''))
    aoMudou()
  }

  const campo =
    (chave: keyof Formulario) => (evento: { target: EventTarget | null }) => {
      const valor = (evento.target as HTMLInputElement | HTMLSelectElement).value
      setForm((atual) => (atual === null ? atual : { ...atual, [chave]: valor }))
    }

  const salvar = async () => {
    if (form === null) return
    const titulo = form.titulo.trim()
    if (titulo === '') return aoAvisar('O título não pode ficar vazio.', 'atencao')
    const nota = validarNota(form.nota)
    if (form.nota.trim() !== '' && nota === null) {
      return aoAvisar('Nota deve ser um número inteiro de 0 a 10.', 'atencao')
    }
    try {
      const atualizado = await window.tucoteca.chamar<JogoDaLista>('jogo.salvar', {
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
      aplicar(atualizado)
      aoAvisar('Jogo salvo.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const favoritar = async () => {
    try {
      const atualizado = await window.tucoteca.chamar<JogoDaLista>('jogo.favoritar', { id })
      aplicar(atualizado)
      aoAvisar(atualizado.favorito === true ? 'Marcado como favorito.' : 'Favorito removido.')
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
      const atualizado = await window.tucoteca.chamar<JogoDaLista>('jogo.ler', { id })
      setJogo(atualizado)
      aoMudou()
      aoAvisar(`${valor} h registradas.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const salvarObservacoes = async () => {
    try {
      const atualizado = await window.tucoteca.chamar<JogoDaLista>('jogo.observacoes', {
        id,
        texto: observacoes,
      })
      setJogo(atualizado)
      aoAvisar('Observações salvas.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const avaliarConquistas = async () => {
    try {
      const r = await window.tucoteca.chamar<{ itens?: Array<Record<string, unknown>>; desbloqueadas?: number; total?: number }>(
        'conquistas.avaliar',
        { id },
      )
      setConquistas(Array.isArray(r?.itens) ? r.itens : [])
      aoAvisar(`Conquistas: ${r?.desbloqueadas ?? 0}/${r?.total ?? 0} desbloqueadas.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const sincronizarConquistas = async () => {
    try {
      await window.tucoteca.chamar('conquistas.sincronizar', { id, appid: appidConquistas.trim(), save: '' })
      aoAvisar('Catalogo de conquistas sincronizado.')
      await avaliarConquistas()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const salvarRegras = async () => {
    try {
      await window.tucoteca.chamar('conquistas.regras', { id, texto: regrasConquistas })
      aoAvisar('Regras salvas.')
      await avaliarConquistas()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const buscarCapas = async () => {
    try {
      const r = await window.tucoteca.chamar<{ candidatos?: Array<Record<string, unknown>> }>('capas.buscar', {
        categoria: 'jogos',
        id,
        provedor: '',
        atualizar: false,
      })
      const lista = Array.isArray(r?.candidatos) ? r.candidatos : []
      setCapasCandidatas(lista)
      aoAvisar(lista.length > 0 ? `${lista.length} capa(s) encontrada(s).` : 'Nenhuma capa encontrada.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const aplicarCapa = async (candidato: Record<string, unknown>) => {
    try {
      await window.tucoteca.chamar('capas.aplicar', { categoria: 'jogos', id, candidato })
      aoAvisar('Capa aplicada.')
      const atualizado = await window.tucoteca.chamar<JogoDaLista>('jogo.ler', { id })
      setJogo(atualizado)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const configurarSaves = async () => {
    const caminhos = savesInput.split(',').map((c) => c.trim()).filter(Boolean)
    try {
      await window.tucoteca.chamar('saves.configurar', { id, caminhos })
      setSavesInput('')
      aoAvisar('Saves configurados.')
      const atualizado = await window.tucoteca.chamar<JogoDaLista>('jogo.ler', { id })
      setJogo(atualizado)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const ferramentasJogo = async () => {
    try {
      const r = await window.tucoteca.chamar<{ saves?: unknown[]; snapshots?: unknown[] }>('ferramentas.jogo', { id })
      const saves = Array.isArray(r?.saves) ? r.saves.length : 0
      const snaps = Array.isArray(r?.snapshots) ? r.snapshots.length : 0
      aoAvisar(`Ferramentas: ${saves} save(s), ${snaps} snapshot(s).`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const diagnosticar = async () => {
    try {
      const r = await window.tucoteca.chamar<{ exe?: { estado?: string } }>('jogo.diagnosticar', { id })
      const estado = r?.exe?.estado ?? 'ok'
      aoAvisar(`Diagnóstico: executável ${estado}.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const remover = async () => {
    if (jogo === null) return
    const titulo = String(jogo.titulo ?? 'o jogo')
    if (!window.confirm(`Remover "${titulo}" da biblioteca? Dá para desfazer.`)) return
    try {
      await window.tucoteca.chamar('item.excluir', { categoria: 'jogos', id })
      aoAvisar(`${titulo} foi removido. Use Desfazer na barra de status.`)
      aoFechar()
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const jogar = async () => {
    if (jogo === null) return
    try {
      await window.tucoteca.chamar('jogo.jogar', { id })
      aoAvisar(`Iniciando ${String(jogo.titulo ?? 'o jogo')}…`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const jogando = jogoEmAndamento(listaTrabalhos.value)
  const url = jogo === null ? '' : window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))

  const linha: string[] = []
  if (jogo !== null) {
    if (jogo.plataforma) linha.push(String(jogo.plataforma))
    if (jogo.status) linha.push(String(jogo.status))
    linha.push(`${Number(jogo.horas ?? 0).toLocaleString('pt-BR')} h`)
    if (jogo.nota !== null && jogo.nota !== undefined && String(jogo.nota) !== '') {
      linha.push(`nota ${String(jogo.nota)}`)
    }
    if (jogo.favorito === true) linha.push('favorito')
  }

  return (
    <div
      class="detalhe-fundo"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) aoFechar()
      }}
    >
      <div class="detalhe" role="dialog" aria-modal="true" aria-label="Detalhe do jogo" ref={modalRef}>
        {jogo === null || form === null ? (
          <p class="detalhe-carregando">Abrindo o jogo…</p>
        ) : (
          <>
            <header class="detalhe-topo">
              <div class="detalhe-capa">
                {url !== '' ? (
                  <img src={url} alt="" />
                ) : (
                  <div class="capa-vazia">{iniciais(jogo.titulo)}</div>
                )}
              </div>
              <div class="detalhe-titulos">
                <h2>{jogo.titulo}</h2>
                <p>{linha.join(' · ')}</p>
                {jogando !== null && (
                  <p class="detalhe-jogando">● {jogando.rotulo}… aguarde a sessão fechar</p>
                )}
              </div>
              <button type="button" class="fechar" title="Fechar" aria-label="Fechar detalhe" onClick={aoFechar}>
                ✕
              </button>
            </header>

            <div class="detalhe-acoes">
              <button
                type="button"
                class="acao primaria"
                onClick={() => void jogar()}
                disabled={jogando !== null}
              >
                ▶ Jogar
              </button>
              <button type="button" class="acao" onClick={() => void favoritar()}>
                {jogo.favorito === true ? '★ Favorito' : '☆ Favoritar'}
              </button>
              <button type="button" class="acao perigo" onClick={() => void remover()}>
                Remover
              </button>
            </div>

            <section>
              <h3>Editar</h3>
              <div class="detalhe-form">
                <label>
                  Título
                  <input value={form.titulo} onInput={campo('titulo')} />
                </label>
                <label>
                  Executável
                  <input
                    value={form.executable_path}
                    onInput={campo('executable_path')}
                    placeholder="C:\\caminho\\jogo.exe"
                  />
                </label>
                <label>
                  Argumentos
                  <input value={form.launch_options} onInput={campo('launch_options')} />
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
                  Nota (0–10)
                  <input value={form.nota} onInput={campo('nota')} placeholder="ex.: 7" />
                </label>
                <label>
                  Etiquetas
                  <input
                    value={form.etiquetas}
                    onInput={campo('etiquetas')}
                    placeholder="rpg, canon"
                  />
                </label>
              </div>
              <button type="button" class="acao" onClick={() => void salvar()}>
                Salvar
              </button>
            </section>

            <section>
              <h3>Registrar horas</h3>
              <div class="detalhe-linha">
                <input
                  value={horas}
                  onInput={(evento) => setHoras((evento.target as HTMLInputElement).value)}
                  placeholder="ex.: 1,5"
                />
                <button type="button" class="acao" onClick={() => void registrarHoras()}>
                  Registrar
                </button>
              </div>
            </section>

            <section>
              <h3>Conquistas e capas</h3>
              <div class="detalhe-linha">
                <button type="button" class="acao" onClick={() => void avaliarConquistas()}>
                  Avaliar conquistas
                </button>
                <button type="button" class="acao" onClick={() => void buscarCapas()}>
                  Buscar capas
                </button>
                <button type="button" class="acao" onClick={() => void ferramentasJogo()}>
                  Ferramentas
                </button>
                <button type="button" class="acao" onClick={() => void diagnosticar()}>
                  Diagnosticar
                </button>
              </div>
              {capasCandidatas.length > 0 && (
                <div class="capas-candidatas">
                  {capasCandidatas.map((c: Record<string, unknown>, i: number) => (
                    <button
                      key={i}
                      type="button"
                      class="acao"
                      onClick={() => void aplicarCapa(c)}
                    >
                      Aplicar capa {i + 1}
                    </button>
                  ))}
                </div>
              )}

              <div class="conquistas-painel">
                <div class="detalhe-linha">
                  <input
                    value={appidConquistas}
                    onInput={(e) => setAppidConquistas((e.target as HTMLInputElement).value)}
                    placeholder="App ID Steam (referência)"
                  />
                  <button type="button" class="acao" onClick={() => void sincronizarConquistas()}>
                    Sincronizar catálogo
                  </button>
                  <button type="button" class="acao" onClick={() => void avaliarConquistas()}>
                    Avaliar
                  </button>
                  <button type="button" class="acao" onClick={() => setMostrarRegras((v) => !v)}>
                    {mostrarRegras ? 'Ocultar regras' : 'Regras'}
                  </button>
                </div>
                {mostrarRegras && (
                  <div class="detalhe-linha">
                    <textarea
                      value={regrasConquistas}
                      onInput={(e) => setRegrasConquistas((e.target as HTMLTextAreaElement).value)}
                      placeholder='{"CODIGO": {"campo": "valor"}}'
                    />
                    <button type="button" class="acao" onClick={() => void salvarRegras()}>
                      Salvar regras
                    </button>
                  </div>
                )}
                {conquistas.length > 0 && (
                  <>
                    <div class="conquistas-progresso">
                      <progress max={conquistas.length} value={conquistas.filter((c) => c.desbloqueada === true).length} />
                      <span>
                        {conquistas.filter((c) => c.desbloqueada === true).length}/{conquistas.length} desbloqueadas
                      </span>
                    </div>
                    <div class="conquistas-grid">
                      {conquistas.map((c, i) => (
                        <div key={i} class={`conquista-card${c.desbloqueada === true ? ' desbloqueada' : ''}`}>
                          {c.icon_url ? (
                            <img class="conquista-icone" src={String(c.icon_url)} alt="" />
                          ) : (
                            <div class="conquista-icone capa-vazia">🏆</div>
                          )}
                          <strong>{String(c.titulo ?? c.id ?? '')}</strong>
                          <span>{String(c.status ?? '')}</span>
                          {c.percent ? <span class="badge">{String(c.percent)}%</span> : null}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </section>

            <section>
              <h3>Saves</h3>
              <div class="detalhe-linha">
                <input
                  value={savesInput}
                  onInput={(e) => setSavesInput((e.target as HTMLInputElement).value)}
                  placeholder="caminhos separados por vírgula"
                />
                <button type="button" class="acao" onClick={() => void configurarSaves()}>
                  Configurar saves
                </button>
              </div>
            </section>

            <section>
              <h3>Observações</h3>
              <textarea
                value={observacoes}
                onInput={(evento) => setObservacoes((evento.target as HTMLTextAreaElement).value)}
              />
              <button type="button" class="acao" onClick={() => void salvarObservacoes()}>
                Salvar observações
              </button>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
