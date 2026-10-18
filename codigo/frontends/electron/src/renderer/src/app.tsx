import { useEffect, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../shared/protocolo'
import { combinacao, decidirAtalho } from './atalhos'
import { BarraLateral } from './componentes/BarraLateral'
import { Paleta } from './componentes/Paleta'
import type { Snapshot } from './derivacoes'
import { paletaInicial, reduzirPaleta, type ItemBusca } from './estado/paleta'
import { Inicio } from './vistas/Inicio'
import { Placeholder } from './vistas/Placeholder'

const DESTINO_DO_ITEM: Record<string, string> = {
  jogo: 'jogos',
  musica: 'musicas',
  desejo: 'desejos',
  download: 'downloads',
}

export function App() {
  const [modulos, setModulos] = useState<ModuloDTO[]>([])
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [secao, setSecao] = useState('inicio')
  const [paleta, setPaleta] = useState(paletaInicial)
  const [atalhos, setAtalhos] = useState<Record<string, string>>({})

  useEffect(() => {
    void (async () => {
      try {
        const lista = await window.tucoteca.chamar<ModuloDTO[]>('modulos.listar')
        setModulos(lista)
        const dados = await window.tucoteca.chamar<Snapshot>('nucleo.snapshot')
        setSnapshot(dados)
        try {
          const prefs = await window.tucoteca.chamar<{ atalhos?: Record<string, string> }>(
            'preferencias.ler',
          )
          setAtalhos(prefs.atalhos ?? {})
        } catch {
          // sem atalhos pessoais o shell segue funcionando; eles chegam na próxima carga
        }
        window.tucoteca.pronto({ jogos: dados.jogos?.length ?? 0 })
      } catch (falha) {
        setErro(String(falha))
      }
    })()
  }, [])

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      const decisao = decidirAtalho(paleta.aberta, combinacao(evento), atalhos)
      if (decisao === null) return
      evento.preventDefault()
      if (decisao.tipo === 'paleta') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'abrir' }))
      } else if (decisao.tipo === 'fechar') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
      } else {
        setSecao(decisao.chave)
      }
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [paleta.aberta, atalhos])

  useEffect(() => {
    if (!paleta.aberta) return
    const termo = paleta.termo
    if (!termo.trim()) return
    let vivo = true
    const timer = setTimeout(() => {
      void (async () => {
        let itens: ItemBusca[] = []
        try {
          itens = await window.tucoteca.chamar<ItemBusca[]>('nucleo.buscar', { termo, limite: 12 })
        } catch {
          itens = []
        }
        if (vivo) setPaleta((atual) => reduzirPaleta(atual, { tipo: 'resultados', termo, itens }))
      })()
    }, 150)
    return () => {
      vivo = false
      clearTimeout(timer)
    }
  }, [paleta.aberta, paleta.termo])

  if (erro) {
    return (
      <section class="painel erro">
        <h1>Não consegui falar com o núcleo</h1>
        <p>{erro}</p>
      </section>
    )
  }

  if (!snapshot) {
    return (
      <section class="painel">
        <h1>TucoTeca</h1>
        <p>Abrindo a coleção…</p>
      </section>
    )
  }

  const ativo = modulos.find((modulo) => modulo.chave === secao) ?? modulos[0]
  return (
    <>
      <main class="shell">
        <BarraLateral modulos={modulos} ativa={ativo?.chave ?? ''} aoTrocar={setSecao} />
        <section class="conteudo">
          {ativo === undefined || ativo.chave === 'inicio' ? (
            <Inicio snapshot={snapshot} />
          ) : (
            <Placeholder modulo={ativo} />
          )}
        </section>
      </main>
      {paleta.aberta && (
        <Paleta
          estado={paleta}
          aoDigitar={(termo) => setPaleta((atual) => reduzirPaleta(atual, { tipo: 'digitou', termo }))}
          aoMover={(delta) =>
            setPaleta((atual) => reduzirPaleta(atual, { tipo: delta === 1 ? 'baixo' : 'cima' }))
          }
          aoDestacar={(indice) =>
            setPaleta((atual) => reduzirPaleta(atual, { tipo: 'selecionar', indice }))
          }
          aoConfirmar={(indice) => {
            const item = paleta.itens[indice ?? paleta.selecionado]
            if (item === undefined) return
            const chave = DESTINO_DO_ITEM[item.tipo]
            if (chave !== undefined) setSecao(chave)
            setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
          }}
          aoFechar={() => setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))}
        />
      )}
    </>
  )
}
