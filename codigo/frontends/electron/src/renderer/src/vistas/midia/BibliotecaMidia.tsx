import { useEffect, useState } from 'preact/hooks'
import { confirmar } from '../../componentes/ui/Confirmacao'
import { EmptyState, Modal } from '../../componentes/ui'
import { filtrarTitulos, type FiltroTipo, type TituloResumo } from '../../estado/midia'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { GradeTitulos } from './GradeTitulos'

interface Pasta {
  id: number
  caminho: string
  arquivos: number
}

interface ParaRevisar {
  id: number
  caminho: string
  nome_lido: string
  ano_lido: number | null
  tipo: 'movie' | 'series'
  temporada: number | null
  episodio: number | null
  sugestao: string
}

interface Biblioteca {
  titulos: TituloResumo[]
  revisar: ParaRevisar[]
  pastas: Pasta[]
}

interface Props {
  aoAvisar: AoAvisar
}

/** Minha biblioteca: pastas escolhidas, varredura, títulos no disco e correspondências a revisar. */
export function BibliotecaMidia({ aoAvisar }: Props) {
  const [dados, setDados] = useState<Biblioteca | null>(null)
  const [tipo, setTipo] = useState<FiltroTipo>('todos')
  const [termo, setTermo] = useState('')
  const [varrendo, setVarrendo] = useState<number | null>(null)
  const [corrigindo, setCorrigindo] = useState<ParaRevisar | null>(null)
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    window.tucoteca
      .chamar<Biblioteca>('midia.biblioteca')
      .then(setDados)
      .catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versao])

  useEffect(() => {
    if (varrendo === null) return
    return window.tucoteca.assinar('trabalho', (d) => {
      const e = d as { id?: number; motivo?: string } | null
      if (e?.id === varrendo && e.motivo === 'fim') {
        setVarrendo(null)
        setVersao((v) => v + 1)
      }
    })
  }, [varrendo])

  const adicionarPasta = async () => {
    try {
      const pasta = await window.tucoteca.escolherPasta()
      if (pasta === null || pasta === '') return
      await window.tucoteca.chamar('midia.pasta_adicionar', { caminho: pasta })
      await varrer()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const removerPasta = async (p: Pasta) => {
    if (!(await confirmar({ titulo: 'Tirar pasta', texto: `Tirar "${p.caminho}" de Filmes e Séries? Os arquivos no disco não são tocados.`, confirmar: 'Tirar' }))) return
    try {
      await window.tucoteca.chamar('midia.pasta_remover', { id: p.id })
      setVersao((v) => v + 1)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const varrer = async () => {
    try {
      const r = await window.tucoteca.chamar<{ trabalho?: { id?: number } }>('midia.varrer')
      const ident = Number(r?.trabalho?.id)
      if (Number.isInteger(ident)) setVarrendo(ident)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  if (dados === null) return <p class="sub">Carregando…</p>
  const lista = filtrarTitulos(dados.titulos, tipo, termo)
  return (
    <section class="midia-biblioteca">
      <div class="midia-barra">
        <div class="biblioteca-modos">
          {(['todos', 'movie', 'series'] as FiltroTipo[]).map((t) => (
            <button key={t} type="button" class={`chip${tipo === t ? ' ativo' : ''}`} onClick={() => setTipo(t)}>
              {t === 'todos' ? 'Tudo' : t === 'movie' ? 'Filmes' : 'Séries'}
            </button>
          ))}
        </div>
        <input class="busca" type="search" placeholder="Filtrar…" value={termo} onInput={(e) => setTermo((e.target as HTMLInputElement).value)} />
        <button type="button" class="acao" onClick={() => void varrer()} disabled={varrendo !== null || dados.pastas.length === 0}>
          {varrendo !== null ? 'Varrendo…' : '↻ Varrer pastas'}
        </button>
        <button type="button" class="acao" onClick={() => void adicionarPasta()}>
          + Adicionar pasta
        </button>
      </div>

      {dados.pastas.length === 0 ? (
        <EmptyState
          icone="🎬"
          titulo="Mostre onde estão seus filmes e séries."
          descricao="Escolha as pastas: o TucoTeca só lê os nomes (nada é copiado nem movido) e identifica cada título no catálogo Cinemeta."
          acao={{ rotulo: 'Adicionar pasta', onClick: () => void adicionarPasta() }}
        />
      ) : lista.length === 0 ? (
        <p class="sub">{dados.titulos.length === 0 ? 'Nenhum título identificado ainda. Use “Varrer pastas”.' : 'Nada com esse filtro.'}</p>
      ) : (
        <GradeTitulos
          itens={lista.map((t) => ({
            ...t,
            selo: t.tipo === 'movie' ? (t.assistido ? '✓' : '') : `${t.arquivos ?? 0} ep.`,
          }))}
        />
      )}

      {dados.revisar.length > 0 && (
        <section class="bloco-jogo">
          <h3>Revisar correspondência ({dados.revisar.length})</h3>
          <p class="sub">Arquivos que não foram identificados com segurança. Escolha o título certo.</p>
          <ul class="lista-revisar">
            {dados.revisar.map((r) => (
              <li key={r.id}>
                <span class="revisar-nome" title={r.caminho}>
                  {r.caminho.split(/[\\/]/).pop()}
                </span>
                <span class="sub">
                  lido como “{r.nome_lido}”{r.ano_lido ? ` (${r.ano_lido})` : ''}
                  {r.temporada !== null ? ` · T${r.temporada}E${r.episodio}` : ''}
                </span>
                <button type="button" class="acao" onClick={() => setCorrigindo(r)}>
                  Escolher título
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {dados.pastas.length > 0 && (
        <section class="bloco-jogo">
          <h3>Pastas</h3>
          <ul class="lista-revisar">
            {dados.pastas.map((p) => (
              <li key={p.id}>
                <span class="revisar-nome">{p.caminho}</span>
                <span class="sub">{p.arquivos} arquivo(s)</span>
                <button type="button" class="acao" onClick={() => void removerPasta(p)}>
                  Tirar
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {corrigindo !== null && (
        <CorrigirTitulo
          item={corrigindo}
          aoFechar={() => setCorrigindo(null)}
          aoCorrigiu={() => {
            setCorrigindo(null)
            setVersao((v) => v + 1)
          }}
          aoAvisar={aoAvisar}
        />
      )}
    </section>
  )
}

interface Candidato {
  imdb_id: string
  nome: string
  ano: string
  poster: string
}

function CorrigirTitulo({ item, aoFechar, aoCorrigiu, aoAvisar }: { item: ParaRevisar; aoFechar: () => void; aoCorrigiu: () => void; aoAvisar: Props['aoAvisar'] }) {
  const [tipo, setTipo] = useState<'movie' | 'series'>(item.tipo)
  const [termo, setTermo] = useState(item.nome_lido)
  const [temporada, setTemporada] = useState(String(item.temporada ?? 1))
  const [episodio, setEpisodio] = useState(String(item.episodio ?? 1))
  const [resultados, setResultados] = useState<Candidato[] | null>(null)

  const buscar = async (e?: Event) => {
    e?.preventDefault()
    try {
      setResultados(await window.tucoteca.chamar<Candidato[]>('midia.descobrir', { tipo, termo: termo.trim() }))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }
  useEffect(() => {
    void buscar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- busca inicial com o nome lido
  }, [tipo])

  const escolher = async (c: Candidato) => {
    try {
      await window.tucoteca.chamar('midia.corrigir', {
        arquivo: item.id,
        imdb: c.imdb_id,
        tipo,
        ...(tipo === 'series' ? { temporada: Number(temporada) || 0, episodio: Number(episodio) || 0 } : {}),
      })
      aoAvisar(`${item.caminho.split(/[\\/]/).pop()} → ${c.nome}.`)
      aoCorrigiu()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <Modal aberto aoFechar={aoFechar} titulo="Escolher o título certo" largura="720px">
      <p class="sub">{item.caminho}</p>
      <form class="detalhe-linha" onSubmit={(e) => void buscar(e)}>
        <select value={tipo} onChange={(e) => setTipo((e.target as HTMLSelectElement).value as 'movie' | 'series')}>
          <option value="movie">Filme</option>
          <option value="series">Série</option>
        </select>
        <input class="busca" value={termo} onInput={(e) => setTermo((e.target as HTMLInputElement).value)} />
        {tipo === 'series' && (
          <>
            <input class="campo-curto" value={temporada} inputMode="numeric" aria-label="Temporada" onInput={(e) => setTemporada((e.target as HTMLInputElement).value)} />
            <input class="campo-curto" value={episodio} inputMode="numeric" aria-label="Episódio" onInput={(e) => setEpisodio((e.target as HTMLInputElement).value)} />
          </>
        )}
        <button type="submit" class="acao">
          Buscar
        </button>
      </form>
      {resultados === null ? (
        <p class="sub">Buscando…</p>
      ) : resultados.length === 0 ? (
        <p class="sub">Nada encontrado. Tente outro nome.</p>
      ) : (
        <GradeTitulos itens={resultados.map((c) => ({ ...c, tipo, aoClicar: () => void escolher(c) }))} />
      )}
    </Modal>
  )
}
