import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { snapshot } from '../estado/dados'
import {
  filtrarDesejos,
  formatarPreco,
  validarAppid,
  validarTituloDesejo,
  type PrecoSteam,
} from '../estado/desejos'
import { textoDeFalha } from '../estado/notificacoes'

interface Props {
  /** Incrementa a cada Ctrl+F: foca o campo de busca. */
  focoBusca?: number
  /** Troca de perfil limpa a seleção (a lista não muda com o perfil). */
  perfil?: string
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou: () => void
}

interface DesejoItem {
  id?: number
  appid?: string | number
  titulo?: string
  [campo: string]: unknown
}

/** Tela Desejos: lista, preços (cache Steam), adicionar/remover e nota das pendências. */
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

  const remover = async () => {
    if (escolhido?.id === undefined) return
    const titulo = String(escolhido.titulo ?? 'o desejo')
    if (!window.confirm(`Remover "${titulo}" da lista de desejos?`)) return
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
          <button type="button" class="acao" onClick={() => setFormAberto((atual) => !atual)}>
            + Adicionar
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

      <p class="aviso">
        Sincronizar Steam, importar wishlist e buscar fontes de download ainda não nesta fatia da
        interface nova.
      </p>

      {lista.length === 0 ? (
        <p class="aviso">Nada por aqui. Adicione um appid ou sincronize a wishlist mais tarde.</p>
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
