import { useState } from 'preact/hooks'
import { dataCurta, linksDaOpcao, type OpcaoDownload } from '../../estado/fontes'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'
import { Modal } from '../ui'

interface Props {
  titulo: string
  aoAvisar: AoAvisar
  rotulo?: string
  primario?: boolean
  desligado?: boolean
}

interface Resultado {
  itens: OpcaoDownload[]
  fontes: number
}

/** "Baixar": opções do jogo nas fontes de download do usuário; baixa dentro do app. */
export function BaixarDasFontes({ titulo, aoAvisar, rotulo = '⬇ Baixar', primario = false, desligado = false }: Props) {
  const [aberto, setAberto] = useState(false)
  const [r, setR] = useState<Resultado | null>(null)
  const [enviando, setEnviando] = useState<string | null>(null)

  const procurar = async () => {
    setAberto(true)
    setR(null)
    try {
      const resp = await window.tucoteca.chamar<Resultado>('fontes.buscar', { titulo })
      setR({ itens: resp?.itens ?? [], fontes: resp?.fontes ?? 0 })
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
      setAberto(false)
    }
  }

  const baixar = async (opcao: OpcaoDownload, uri: string) => {
    setEnviando(uri)
    try {
      const resp = await window.tucoteca.chamar<{ aviso?: string; trabalho?: unknown }>('fontes.baixar', { uri, titulo: opcao.titulo })
      aoAvisar(resp?.aviso ?? `Baixando ${opcao.titulo}… (o progresso aparece no rodapé)`)
      setAberto(false)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setEnviando(null)
    }
  }

  return (
    <>
      <button
        type="button"
        class={`acao${primario ? ' primaria hero-jogar' : ''}`}
        disabled={desligado || titulo.trim() === ''}
        onClick={() => void procurar()}
        title="Procura o jogo nas suas fontes de download e baixa dentro do app"
      >
        {rotulo}
      </button>
      <Modal aberto={aberto} aoFechar={() => setAberto(false)} titulo={`Baixar ${titulo}`} largura="760px">
        {r === null ? (
          <p class="sub">Procurando nas suas fontes…</p>
        ) : r.fontes === 0 ? (
          <div class="fontes-vazio">
            <p>Você ainda não tem fontes de download.</p>
            <p class="sub">
              Uma fonte é uma lista no formato do Hydra (um endereço https de JSON). Adicione as que você
              escolher em Configurações → Integrações.
            </p>
            <button type="button" class="acao primaria" onClick={() => { setAberto(false); ir('#/configuracoes/integracoes') }}>
              Adicionar fontes
            </button>
          </div>
        ) : r.itens.length === 0 ? (
          <p class="sub">Nenhuma das suas {r.fontes} fonte(s) tem “{titulo}”.</p>
        ) : (
          <ul class="opcoes-fontes">
            {r.itens.map((opcao, i) => (
              <li key={`${opcao.fonte_id}-${i}`}>
                <div class="opcao-fonte-textos">
                  <strong>{opcao.titulo}</strong>
                  <span>{[opcao.fonte, opcao.tamanho, dataCurta(opcao.data)].filter(Boolean).join(' · ')}</span>
                </div>
                <div class="opcao-fonte-acoes">
                  {linksDaOpcao(opcao).map((link) => (
                    <button
                      key={link.uri}
                      type="button"
                      class={`acao${link.tipo === 'torrent' ? ' primaria' : ''}`}
                      disabled={enviando !== null}
                      onClick={() => void baixar(opcao, link.uri)}
                      title={link.tipo === 'torrent' ? 'Baixa pelo qBittorrent integrado' : 'O app baixa o arquivo direto'}
                    >
                      {enviando === link.uri ? 'Enviando…' : link.rotulo}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
        <p class="sub">Vai para Meus Jogos Locais; ao terminar, importe em Downloads. As fontes são suas: o TucoTeca não traz nenhuma.</p>
      </Modal>
    </>
  )
}
