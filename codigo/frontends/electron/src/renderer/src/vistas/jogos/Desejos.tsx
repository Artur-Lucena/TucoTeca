import { modoTv } from '../../navegacao/foco'
import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { snapshot } from '../../estado/dados'
import {
  filtrarDesejos,
  formatarPreco,
  validarAppid,
  validarTituloDesejo,
  type PrecoSteam,
} from '../../estado/desejos'
import { EmptyState } from '../../componentes/ui'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { confirmar } from '../../componentes/ui/Confirmacao'

interface Props {
  /** Incrementa a cada Ctrl+F: foca o campo de busca. */
  focoBusca?: number
  /** Troca de perfil limpa a seleção (a lista não muda com o perfil). */
  perfil?: string
  aoAvisar: AoAvisar
  aoMudou: () => void
}

interface DesejoItem {
  id?: number
  appid?: string | number
  titulo?: string
  [campo: string]: unknown
}

/** Tela Desejos: lista, preços (cache Steam), adicionar/remover e nota das pendências. */
interface FontesDesejo {
  titulo: string
  steamrip: Array<{ titulo: string; url: string }>
  fitgirl: Array<{ titulo: string; url: string }>
  erros: string[]
}

export function Desejos({ focoBusca = 0, perfil = '', aoAvisar, aoMudou }: Props) {
  const desejos = (snapshot.value?.desejos ?? []) as DesejoItem[]
  const [busca, setBusca] = useState('')
  const [selecionado, setSelecionado] = useState(0)
  const [precos, setPrecos] = useState<Record<string, PrecoSteam>>({})
  const [consultando, setConsultando] = useState(false)
  const [formAberto, setFormAberto] = useState(false)
  const [novoTitulo, setNovoTitulo] = useState('')
  const [novoAppid, setNovoAppid] = useState('')
  const campo = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (focoBusca > 0) campo.current?.focus()
  }, [focoBusca])

  useEffect(() => {
    setSelecionado(0)
  }, [perfil])

  const lista = useMemo(() => filtrarDesejos(desejos, busca), [desejos, busca])
  const indice = Math.min(selecionado, Math.max(0, lista.length - 1))
  const escolhido = lista[indice]

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (modoTv() && evento.key.startsWith('Arrow')) return
      if (evento.ctrlKey || evento.altKey || evento.metaKey) return
      if (document.querySelector('.paleta-fundo') !== null) return
      const alvo = evento.target as HTMLElement | null
      if (alvo !== null && alvo.closest('input, textarea, select') !== null && alvo !== campo.current) return
      if (evento.key !== 'ArrowDown' && evento.key !== 'ArrowUp') return
      evento.preventDefault()
      const passo = evento.key === 'ArrowDown' ? 1 : -1
      setSelecionado((atual) => Math.max(0, Math.min(lista.length - 1, atual + passo)))
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [lista.length])

  const abrirSteam = async () => {
    const appid = escolhido?.appid
    if (appid === undefined) return
    try {
      await window.tucoteca.abrirUrl(`https://store.steampowered.com/app/${String(appid)}/`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const verPrecos = async () => {
    setConsultando(true)
    try {
      const mapa = await window.tucoteca.chamar<Record<string, PrecoSteam>>('desejos.precos')
      const limpo = mapa ?? {}
      setPrecos(limpo)
      const total = Object.keys(limpo).length
      if (total === 0) aoAvisar('Sem preços agora (sem rede ou sem cache).', 'atencao')
      else aoAvisar(`${total} preço(s) encontrados no cache/consulta.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setConsultando(false)
    }
  }

  const adicionar = async () => {
    const erroTitulo = validarTituloDesejo(novoTitulo)
    const erroAppid = validarAppid(novoAppid)
    const erro = erroTitulo ?? erroAppid
    if (erro !== null) {
      aoAvisar(erro, 'atencao')
      return
    }
    const titulo = novoTitulo.trim()
    try {
      const dados = await window.tucoteca.chamar<{ ok?: boolean; novo?: boolean }>(
        'desejos.adicionar',
        { titulo, appid: novoAppid.trim() },
      )
      aoAvisar(
        dados?.novo === true
          ? `"${titulo}" entrou na lista de desejos.`
          : `"${titulo}" atualizou um desejo que já estava na lista.`,
      )
      setFormAberto(false)
      setNovoTitulo('')
      setNovoAppid('')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const [fontes, setFontes] = useState<FontesDesejo | null>(null)
  const [buscandoFontes, setBuscandoFontes] = useState(false)

  const sincronizarSteam = async () => {
    try {
      const r = await window.tucoteca.chamar<{ avisos?: string[] }>('desejos.sincronizar_steam')
      aoAvisar(r?.avisos?.[0] ?? 'Wishlist sincronizada.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const importarWishlist = async () => {
    const caminho = await window.tucoteca.escolherArquivo([{ nome: 'Wishlist da Steam (JSON)', extensoes: ['json'] }])
    if (!caminho) return
    try {
      const r = await window.tucoteca.chamar<{ avisos?: string[] }>('desejos.importar_wishlist', { caminho })
      aoAvisar(r?.avisos?.[0] ?? 'Wishlist importada.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const buscarFontes = async () => {
    const titulo = String(escolhido?.titulo ?? '').trim()
    if (titulo === '') return
    setBuscandoFontes(true)
    try {
      const r = await window.tucoteca.chamar<FontesDesejo>('desejos.buscar_fontes', { titulo })
      setFontes({ titulo, steamrip: r?.steamrip ?? [], fitgirl: r?.fitgirl ?? [], erros: r?.erros ?? [] })
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setBuscandoFontes(false)
    }
  }

  const abrirFonte = async (url: string) => {
    try {
      await window.tucoteca.abrirUrl(url)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const remover = async () => {
    if (escolhido?.id === undefined) return
    const titulo = String(escolhido.titulo ?? 'o desejo')
    if (!(await confirmar({ titulo: 'Remover desejo', texto: `Remover "${titulo}" da lista de desejos? Dá para desfazer pela barra de status.`, confirmar: 'Remover', perigo: true }))) return
    try {
      await window.tucoteca.chamar('item.excluir', {
        categoria: 'desejos',
        id: Number(escolhido.id),
      })
      aoAvisar(`${titulo} saiu da lista (Desfazer na barra de status).`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="vista desejos">
      <header class="vista-topo">
        <h1>Desejos ({lista.length})</h1>
        <div class="vista-acoes">
          <input
            ref={campo}
            class="busca"
            type="search"
            placeholder="Buscar por título…"
            value={busca}
            onInput={(evento) => setBusca((evento.target as HTMLInputElement).value)}
          />
          <button
            type="button"
            class="acao"
            onClick={() => void abrirSteam()}
            disabled={escolhido?.appid === undefined}
          >
            Steam ↗
          </button>
          <button
            type="button"
            class="acao"
            onClick={() => void verPrecos()}
            disabled={consultando}
          >
            {consultando ? 'Ver preços…' : 'Ver preços'}
          </button>
          <button
            type="button"
            class="acao"
            onClick={() => void buscarFontes()}
            disabled={escolhido === undefined || buscandoFontes}
            title="Procura o título selecionado nas fontes (abre a página no navegador)"
          >
            {buscandoFontes ? 'Buscando…' : 'Buscar fontes'}
          </button>
          <button type="button" class="acao" onClick={() => setFormAberto((atual) => !atual)}>
            + Adicionar
          </button>
          <button type="button" class="acao" onClick={() => void sincronizarSteam()} title="Lê a wishlist da conta Steam deste PC">
            Sincronizar Steam
          </button>
          <button type="button" class="acao" onClick={() => void importarWishlist()} title="Importa o JSON da wishlist salvo do site da Steam">
            Importar JSON
          </button>
          <button
            type="button"
            class="acao perigo"
            onClick={() => void remover()}
            disabled={escolhido === undefined}
          >
            Remover
          </button>
        </div>
      </header>

      {formAberto && (
        <div class="form-desejo">
          <label>
            Título
            <input
              class="campo-titulo"
              type="text"
              value={novoTitulo}
              onInput={(evento) => setNovoTitulo((evento.target as HTMLInputElement).value)}
            />
          </label>
          <label>
            appid da Steam
            <input
              class="campo-appid"
              type="text"
              inputMode="numeric"
              placeholder="ex.: 504230"
              value={novoAppid}
              onInput={(evento) => setNovoAppid((evento.target as HTMLInputElement).value)}
              onKeyDown={(evento) => {
                if (evento.key === 'Enter') void adicionar()
              }}
            />
          </label>
          <button type="button" class="acao" onClick={() => void adicionar()}>
            Salvar desejo
          </button>
          <button type="button" class="acao" onClick={() => setFormAberto(false)}>
            Cancelar
          </button>
        </div>
      )}

      {fontes !== null && (
        <div class="form-config painel-paridade fontes-desejo">
          <h2>Fontes para “{fontes.titulo}”</h2>
          {(['steamrip', 'fitgirl'] as const).map((chave) => (
            <div key={chave}>
              <h4>{chave === 'steamrip' ? 'SteamRip' : 'FitGirl'}</h4>
              {fontes[chave].length === 0 ? (
                <p class="sub">Nada encontrado.</p>
              ) : (
                <ul class="lista-simples">
                  {fontes[chave].map((item, i) => (
                    <li key={`${chave}-${i}`}>
                      <span>{item.titulo}</span>
                      <button type="button" class="acao" onClick={() => void abrirFonte(item.url)}>
                        Abrir página ↗
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          {fontes.erros.length > 0 && <p class="sub">Avisos: {fontes.erros.join(' · ')}</p>}
          <button type="button" class="acao" onClick={() => setFontes(null)}>
            Fechar
          </button>
        </div>
      )}

      {lista.length === 0 ? (
        <EmptyState icone="★" titulo="Nada por aqui." descricao="Adicione um appid, sincronize com a Steam ou importe o JSON da wishlist." />
      ) : (
        <ul class="lista-desejos">
          {lista.map((desejo, posicao) => {
            const appid = desejo.appid === undefined ? '' : String(desejo.appid)
            const preco = formatarPreco(precos[appid])
            const capa = appid !== '' ? `https://cdn.akamai.steamstatic.com/steam/apps/${appid}/header.jpg` : ''
            return (
              <li
                key={String(desejo.id ?? posicao)}
                class={`linha${posicao === indice ? ' selecionado' : ''}`}
                onClick={() => setSelecionado(posicao)}
                onDblClick={() => void abrirSteam()}
              >
                {capa !== '' && (
                  <span class="desejo-capa">
                    <img src={capa} alt="" loading="lazy" onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
                  </span>
                )}
                <span class="desejo-textos">
                  <strong>{String(desejo.titulo ?? '')}</strong>
                  <span>{appid === '' ? 'Steam' : `Steam · ${appid}`}</span>
                </span>
                {preco !== '' && <span class="preco">{preco}</span>}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
