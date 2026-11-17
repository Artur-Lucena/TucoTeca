import { useEffect, useState } from 'preact/hooks'
import { EmptyState } from '../../componentes/ui'
import { chavesDaTemporada, fracao, proximoParaAssistir, reproduzindo, rotuloEpisodio, type Episodio, type TituloCompleto } from '../../estado/midia'
import { data, hojeISO } from '../../estado/formato'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'

interface Props {
  imdb: string
  aoAvisar: AoAvisar
}

/** Página de filme/série (`#/titulo/:imdb`): ficha do Cinemeta + o que você tem no disco. */
export function PaginaTitulo({ imdb, aoAvisar }: Props) {
  const [t, setT] = useState<TituloCompleto | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [temporada, setTemporada] = useState<number | null>(null)
  const [versao, setVersao] = useState(0)
  const [semFundo, setSemFundo] = useState(false)

  useEffect(() => {
    let vivo = true
    window.tucoteca
      .chamar<TituloCompleto>('midia.titulo', { imdb })
      .then((r) => {
        if (!vivo) return
        setT(r)
        setErro(null)
      })
      .catch((falha) => vivo && setErro(textoDeFalha(falha)))
    return () => {
      vivo = false
    }
  }, [imdb, versao, reproduzindo.value])

  const recarregar = () => setVersao((v) => v + 1)

  const alternarLista = async () => {
    if (t === null) return
    try {
      const r = await window.tucoteca.chamar<{ na_lista: boolean }>('midia.lista_alternar', { imdb, tipo: t.tipo })
      aoAvisar(r.na_lista ? `${t.nome} entrou na sua lista.` : `${t.nome} saiu da sua lista.`)
      recarregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const seguir = async () => {
    if (t === null) return
    try {
      await window.tucoteca.chamar('midia.seguir', { imdb, seguir: !t.seguindo })
      aoAvisar(t.seguindo ? `Você não segue mais ${t.nome}.` : `Seguindo ${t.nome}: episódios novos aparecem no Calendário.`)
      recarregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const marcar = async (chaves: string[], assistido: boolean) => {
    if (chaves.length === 0) return
    try {
      await window.tucoteca.chamar('midia.marcar', { chaves, assistido })
      recarregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  if (erro !== null) {
    return <EmptyState icone="⚠" titulo="Não abri este título." descricao={erro} acao={{ rotulo: 'Voltar', onClick: () => ir('#/midia') }} />
  }
  if (t === null) return <p class="sub">Abrindo…</p>

  const serie = t.tipo === 'series'
  const temporadas = t.temporadas ?? []
  const atual = temporadas.find((s) => s.numero === temporada) ?? temporadas.find((s) => s.numero > 0) ?? temporadas[0]
  const proximo = serie ? proximoParaAssistir(temporadas) : null
  const arquivoFilme = !serie ? (t.arquivos ?? [])[0] : undefined
  const assistirId = serie ? proximo?.arquivo ?? null : arquivoFilme?.id ?? null
  const progressoFilme = !serie ? fracao(t.progresso) : 0
  const fundo = !semFundo && t.fundo !== '' ? t.fundo : t.poster
  const ficha = [t.ano, t.duracao, t.nota !== '' ? `IMDb ${t.nota}` : '', t.generos.slice(0, 3).join(', ')].filter((x) => x !== '')

  return (
    <article class="pagina-jogo pagina-titulo">
      <header class={`hero-jogo${semFundo || t.fundo === '' ? ' sem-hero' : ''}`}>
        <div class="hero-arte">{fundo !== '' && <img class="hero-fundo" src={window.tucoteca.imagemUrl(fundo)} alt="" onError={() => setSemFundo(true)} />}</div>
        <div class="hero-conteudo">
          {t.logo !== '' ? <img class="hero-logo" src={t.logo} alt={t.nome} onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} /> : null}
          <h1 class={`hero-titulo${t.logo !== '' ? ' so-leitor' : ''}`}>{t.nome}</h1>
          <p class="hero-linha">
            {serie ? 'Série' : 'Filme'}
            {ficha.length > 0 ? ` · ${ficha.join(' · ')}` : ''}
          </p>
          <div class="hero-acoes">
            {assistirId !== null ? (
              <button type="button" class="acao primaria hero-jogar" onClick={() => (reproduzindo.value = assistirId)}>
                ▶ {serie && proximo ? `Assistir ${rotuloEpisodio(proximo.temporada, proximo.episodio)}` : progressoFilme > 0 && progressoFilme < 1 ? 'Continuar' : 'Assistir'}
              </button>
            ) : (
              <button type="button" class="acao" disabled title="Nenhum arquivo deste título nas suas pastas">
                Não está no disco
              </button>
            )}
            <button type="button" class="acao" onClick={() => void alternarLista()}>
              {t.na_lista ? '✓ Na minha lista' : '+ Minha lista'}
            </button>
            {serie && (
              <button type="button" class="acao" onClick={() => void seguir()}>
                {t.seguindo ? '🔔 Seguindo' : 'Seguir'}
              </button>
            )}
            {!serie && arquivoFilme !== undefined && (
              <button type="button" class="acao" onClick={() => void marcar([imdb], !(t.progresso?.assistido ?? false))}>
                {t.progresso?.assistido ? 'Marcar como não visto' : 'Marcar como visto'}
              </button>
            )}
          </div>
          {!serie && progressoFilme > 0 && progressoFilme < 1 && (
            <span class="cartao-titulo-barra hero-barra">
              <span style={{ width: `${Math.round(progressoFilme * 100)}%` }} />
            </span>
          )}
        </div>
      </header>

      <div class="sobre-jogo">
        <div class="sobre-principal">
          {t.descricao !== '' && (
            <section class="bloco-jogo">
              <h3>Sinopse</h3>
              <div class="descricao-jogo">
                <p>{t.descricao}</p>
              </div>
            </section>
          )}
          {serie && atual !== undefined && (
            <section class="bloco-jogo">
              <div class="bloco-topo">
                <select value={String(atual.numero)} onChange={(e) => setTemporada(Number((e.target as HTMLSelectElement).value))} aria-label="Temporada">
                  {temporadas.map((s) => (
                    <option key={s.numero} value={String(s.numero)}>
                      {s.numero === 0 ? 'Especiais' : `Temporada ${s.numero}`} ({s.episodios.filter((e) => e.arquivo !== null).length}/{s.episodios.length} no disco)
                    </option>
                  ))}
                </select>
                <button type="button" class="acao" onClick={() => void marcar(chavesDaTemporada(atual), true)}>
                  Marcar temporada como vista
                </button>
              </div>
              <ul class="lista-episodios">
                {atual.episodios.map((e) => (
                  <LinhaEpisodio key={e.chave} e={e} aoMarcar={(v) => void marcar([e.chave], v)} />
                ))}
              </ul>
            </section>
          )}
        </div>
        <aside class="ficha-jogo">
          {t.poster !== '' && <img class="ficha-capa" src={window.tucoteca.imagemUrl(t.poster)} alt="" onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />}
          {!serie && (t.arquivos ?? []).length > 0 && (
            <dl>
              <div>
                <dt>No disco</dt>
                {(t.arquivos ?? []).map((a) => (
                  <dd key={a.id} class="caminho-arquivo" title={a.caminho}>
                    {a.caminho.split(/[\\/]/).pop()}
                  </dd>
                ))}
              </div>
            </dl>
          )}
          <p class="sub origem-dados">Dados: Cinemeta (em inglês)</p>
        </aside>
      </div>
    </article>
  )
}

function LinhaEpisodio({ e, aoMarcar }: { e: Episodio; aoMarcar: (assistido: boolean) => void }) {
  const visto = e.progresso?.assistido ?? false
  const f = fracao(e.progresso)
  const futuro = e.estreia !== '' && e.estreia > hojeISO()
  return (
    <li class={`episodio${visto ? ' visto' : ''}${e.arquivo === null ? ' fora-do-disco' : ''}`}>
      <span class="episodio-miniatura">
        {e.miniatura !== '' && !futuro && <img src={e.miniatura} alt="" loading="lazy" onError={(ev) => ((ev.target as HTMLImageElement).style.display = 'none')} />}
        {e.arquivo !== null && (
          <button type="button" class="episodio-play" aria-label={`Assistir ${rotuloEpisodio(e.temporada, e.episodio)}`} onClick={() => (reproduzindo.value = e.arquivo)}>
            ▶
          </button>
        )}
        {f > 0 && f < 1 && (
          <span class="cartao-titulo-barra">
            <span style={{ width: `${Math.round(f * 100)}%` }} />
          </span>
        )}
      </span>
      <span class="episodio-textos">
        <strong>
          {e.episodio}. {e.nome || rotuloEpisodio(e.temporada, e.episodio)}
        </strong>
        <span class="sub">
          {e.estreia !== '' ? (futuro ? `Estreia ${data(e.estreia)}` : data(e.estreia)) : ''}
          {e.arquivo === null && !futuro ? ' · não está no disco' : ''}
        </span>
        {e.resumo !== '' && <span class="episodio-resumo">{e.resumo}</span>}
      </span>
      <button type="button" class={`episodio-marca${visto ? ' ativo' : ''}`} onClick={() => aoMarcar(!visto)} aria-pressed={visto} title={visto ? 'Marcar como não visto' : 'Marcar como visto'}>
        ✓
      </button>
    </li>
  )
}
