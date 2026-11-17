import { bytes } from '../estado/formato'
import { useEffect, useState } from 'preact/hooks'
import { snapshot } from '../estado/dados'
import { EmptyState } from '../componentes/ui'
import { textoDeFalha } from '../estado/notificacoes'
import { listaTrabalhos } from '../estado/trabalhos'
import { confirmar } from '../componentes/ui/Confirmacao'

interface Props {
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou: () => void
}

interface TorrentItem {
  hash: string
  nome: string
  estado: string
  pct: number
  feito: number
  total: number
  fonte_progresso: string
  velocidade: number
  eta: number | null
  save_path: string
  /** Concluído fora da pasta de jogos: candidato a Organizar. */
  fora_destino?: boolean
}

interface RespostaListar {
  itens: TorrentItem[]
  erros: string[]
}

const formatarBytes = (n: number): string => bytes(Number(n || 0))

/** Tela Downloads: torrents em andamento/concluídos, importar e organizar. */
export function Downloads({ aoAvisar, aoMudou }: Props) {
  const [itens, setItens] = useState<TorrentItem[]>([])
  const [erros, setErros] = useState<string[]>([])
  const [ocupados, setOcupados] = useState<Record<string, boolean>>({})
  const [modal, setModal] = useState(false)
  const [importando, setImportando] = useState<string | null>(null)
  const [pacotePasta, setPacotePasta] = useState('')
  const [pacoteExe, setPacoteExe] = useState('')

  const carregar = async () => {
    try {
      const r = await window.tucoteca.chamar<RespostaListar>('torrents.listar')
      setItens(r?.itens ?? [])
      setErros(r?.erros ?? [])
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  useEffect(() => {
    void carregar()
    const timer = window.setInterval(() => void carregar(), 5000)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carregar só usa setters
  }, [])

  const trabalhoAtivo = listaTrabalhos.value.find(
    (t) => t.escopo === 'torrents' && (t.estado === 'rodando' || t.estado === 'cancelando'),
  )

  const abrirPasta = async (caminho: string) => {
    try {
      await window.tucoteca.abrirPasta(caminho)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const controlar = async (item: TorrentItem, acao: 'pausar' | 'retomar') => {
    setOcupados((atual) => ({ ...atual, [item.hash]: true }))
    try {
      await window.tucoteca.chamar('torrents.controlar', { ident: item.hash, acao })
      aoAvisar(acao === 'pausar' ? 'Torrent pausado.' : 'Torrent retomado.')
      await carregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupados((atual) => ({ ...atual, [item.hash]: false }))
    }
  }

  const organizar = async (item: TorrentItem) => {
    if (!(await confirmar({ titulo: 'Organizar download', texto: `Mover "${item.nome}" para a pasta de jogos?`, confirmar: 'Organizar' }))) return
    setOcupados((atual) => ({ ...atual, [item.hash]: true }))
    try {
      const r = await window.tucoteca.chamar<{ ok?: boolean }>('torrents.organizar', { caminho: item.save_path })
      aoAvisar(r?.ok === true ? 'Download organizado na pasta de jogos.' : 'Não foi possível organizar.')
      await carregar()
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupados((atual) => ({ ...atual, [item.hash]: false }))
    }
  }

  const importar = async (item: TorrentItem) => {
    setImportando(item.hash)
    try {
      await window.tucoteca.chamar('torrents.importar', { caminho: item.save_path })
      aoAvisar(`Importando "${item.nome}"…`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setImportando(null)
    }
  }

  const concluidos = itens.filter((item) => item.pct >= 100 || item.estado === 'completo')

  const sistema = snapshot.value?.sistema as { disco_livre_gb?: number } | undefined
  const livres = sistema?.disco_livre_gb

  return (
    <section class="vista downloads">
      <header class="vista-topo">
        <h1>Downloads ({itens.length})</h1>
        <div class="vista-acoes">
          <button type="button" class="acao" onClick={() => setModal(true)} disabled={concluidos.length === 0}>
            Importar concluídos… ({concluidos.length})
          </button>
        </div>
      </header>

      {erros.length > 0 && (
        <p class="aviso">{erros.join(' · ')}</p>
      )}

      {itens.length === 0 ? (
        <EmptyState icone="↓" titulo="Nenhum torrent conhecido." descricao="Adicione torrents no qBittorrent." />
      ) : (
        <ul class="lista-downloads">
          {itens.map((item) => {
            return (
              <li class="linha-download" key={item.hash}>
                <span class="download-icone">↓</span>
                <div class="download-textos">
                  <strong>{item.nome}</strong>
                  <span>
                    {item.pct >= 100 || item.estado === 'completo' ? 'Concluído' : `${item.pct.toFixed(0)}% · baixando`}
                    {item.total > 0 ? ` · ${formatarBytes(item.feito)}/${formatarBytes(item.total)}` : ''}
                    {item.fonte_progresso === 'estimativa' ? ' · estimativa em disco' : ''}
                    {item.velocidade ? ` · ${formatarBytes(item.velocidade)}/s` : ''}
                    {item.eta ? ` · ETA ${Math.round(item.eta)}s` : ''}
                  </span>
                </div>
                <progress class="download-barra" max={100} value={item.pct} />
                <div class="download-acoes">
                  {item.save_path !== '' && (
                    <button type="button" class="acao" onClick={() => void abrirPasta(item.save_path)}>
                      Abrir pasta
                    </button>
                  )}
                  {item.fonte_progresso === 'api' && (
                    <button
                      type="button"
                      class="acao"
                      onClick={() => void controlar(item, item.estado === 'pausado' ? 'retomar' : 'pausar')}
                      disabled={ocupados[item.hash] === true}
                    >
                      {item.estado === 'pausado' ? 'Retomar' : 'Pausar'}
                    </button>
                  )}
                  {item.save_path !== '' && (
                    <button
                      type="button"
                      class="acao"
                      onClick={() => void organizar(item)}
                      disabled={ocupados[item.hash] === true}
                      title={item.fora_destino === true ? 'Move para a pasta de jogos' : 'Organiza na pasta de jogos'}
                    >
                      {item.fora_destino === true ? 'Organizar (fora da pasta de jogos)' : 'Organizar'}
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {livres !== undefined && (
        <p class="sub">{livres.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} GB livres no disco</p>
      )}

      {trabalhoAtivo !== undefined && trabalhoAtivo !== null && (
        <p class="aviso">Importando… {trabalhoAtivo.rotulo}</p>
      )}

      <section class="pacotes">
        <h2>Pacotes locais</h2>
        <div class="vista-acoes">
          <input
            class="busca"
            type="text"
            placeholder="Pasta do pacote"
            value={pacotePasta}
            onInput={(e) => setPacotePasta((e.target as HTMLInputElement).value)}
          />
          <input
            class="busca"
            type="text"
            placeholder="Executável (opcional)"
            value={pacoteExe}
            onInput={(e) => setPacoteExe((e.target as HTMLInputElement).value)}
          />
          <button
            type="button"
            class="acao"
            onClick={async () => {
              try {
                const pasta = await window.tucoteca.escolherPasta()
                if (pasta === null || pasta === '') return
                setPacotePasta(pasta)
              } catch (falha) {
                aoAvisar(textoDeFalha(falha), 'atencao')
              }
            }}
          >
            Escolher pasta
          </button>
          <button
            type="button"
            class="acao"
            onClick={async () => {
              if (pacotePasta.trim() === '') return
              try {
                await window.tucoteca.chamar('pacotes.importar', { pasta: pacotePasta.trim(), exe: pacoteExe.trim() })
                aoAvisar('Pacote importado.')
                setPacotePasta('')
                setPacoteExe('')
                aoMudou()
              } catch (falha) {
                aoAvisar(textoDeFalha(falha), 'atencao')
              }
            }}
          >
            Importar pacote
          </button>
          <button
            type="button"
            class="acao"
            onClick={async () => {
              if (pacoteExe.trim() === '') return
              try {
                await window.tucoteca.chamar('pacotes.abrir_instalador', { exe: pacoteExe.trim() })
                aoAvisar('Instalador aberto.')
              } catch (falha) {
                aoAvisar(textoDeFalha(falha), 'atencao')
              }
            }}
          >
            Abrir instalador
          </button>
        </div>
      </section>

      {modal && (
        <div class="modal-downloads">
          <h2>Importar concluídos ({concluidos.length})</h2>
          <p class="aviso">Só entra aqui o que chegou a 100%.</p>
          {concluidos.length === 0 ? (
            <p class="aviso">Nada concluído ainda.</p>
          ) : (
            <ul class="lista-importar">
              {concluidos.map((item) => (
                <li key={item.hash}>
                  <span>{item.nome}</span>
                  <button
                    type="button"
                    class="acao"
                    onClick={() => void importar(item)}
                    disabled={importando === item.hash}
                  >
                    {importando === item.hash ? 'Importando…' : 'Importar'}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button type="button" class="acao" onClick={() => setModal(false)}>
            Fechar
          </button>
        </div>
      )}
    </section>
  )
}
