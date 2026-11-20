import { useEffect, useState } from 'preact/hooks'
import { downloadDaAtualizacao, instaladorPronto, resumoDaVerificacao, type Verificacao } from '../../estado/atualizacao'
import { emAndamento, estadoDoDownload } from '../../estado/downloads'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { listaTrabalhos } from '../../estado/trabalhos'
import { confirmar } from '../ui/Confirmacao'

interface Props {
  aoAvisar: AoAvisar
}

const TEXTO_INSTALAR: Record<string, string> = {
  win32: 'O instalador abre e o TucoTeca fecha para atualizar. Sua coleção não é tocada.',
  darwin: 'A imagem (.dmg) abre: arraste o TucoTeca para Aplicativos, substituindo o antigo.',
  linux: 'A pasta com o AppImage novo abre: use-o no lugar do antigo.',
}

/** Sobre e atualizações: versão atual, verificar no GitHub (só ao clicar), baixar e instalar. */
export function PainelAtualizacao({ aoAvisar }: Props) {
  const [versao, setVersao] = useState('')
  const [verificando, setVerificando] = useState(false)
  const [resultado, setResultado] = useState<Verificacao | null>(null)

  useEffect(() => {
    void window.tucoteca
      .chamar<{ versao?: string }>('nucleo.ping')
      .then((r) => setVersao(r?.versao ?? ''))
      .catch(() => undefined)
  }, [])

  const download = downloadDaAtualizacao(listaTrabalhos.value)
  const pronto = instaladorPronto(listaTrabalhos.value)

  const verificar = async () => {
    setVerificando(true)
    try {
      setResultado(await window.tucoteca.chamar<Verificacao>('app.verificar_atualizacao'))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setVerificando(false)
    }
  }

  const baixar = async () => {
    if (resultado?.instalador == null) return
    try {
      await window.tucoteca.chamar('app.baixar_atualizacao', { instalador: resultado.instalador, versao: resultado.ultima })
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const instalar = async () => {
    const plataforma = window.tucoteca.plataforma
    const ok = await confirmar({
      titulo: 'Instalar atualização',
      texto: TEXTO_INSTALAR[plataforma] ?? TEXTO_INSTALAR['linux'] ?? '',
      confirmar: plataforma === 'win32' ? 'Instalar e fechar' : 'Abrir',
    })
    if (!ok) return
    try {
      await window.tucoteca.instalarAtualizacao(pronto)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <div class="form-config painel-atualizacao">
      <h2>Sobre e atualizações</h2>
      <p>TucoTeca {versao || '…'}</p>
      <div class="vista-acoes">
        <button type="button" class="acao" disabled={verificando} onClick={() => void verificar()}>
          {verificando ? 'Verificando…' : 'Verificar atualização'}
        </button>
        {pronto !== '' && (
          <button type="button" class="acao primaria" onClick={() => void instalar()}>
            Instalar atualização
          </button>
        )}
      </div>
      <p class="sub">Só consulta o GitHub quando você clica; nada é baixado sem pedir.</p>
      {resultado !== null && (
        <div class="resultado-atualizacao">
          <p>{resumoDaVerificacao(resultado)}</p>
          {resultado.nova && (
            <>
              {download !== null && emAndamento(download) ? (
                <p class="sub">{estadoDoDownload(download)} (também em Downloads)</p>
              ) : resultado.instalador !== null ? (
                pronto === '' && (
                  <button type="button" class="acao primaria" onClick={() => void baixar()}>
                    Baixar {resultado.ultima}
                  </button>
                )
              ) : (
                <button type="button" class="acao" onClick={() => void window.tucoteca.abrirUrl(resultado.pagina).catch(() => undefined)}>
                  Abrir a página da versão
                </button>
              )}
              {resultado.notas.trim() !== '' && (
                <details>
                  <summary>O que mudou</summary>
                  <pre class="notas-versao">{resultado.notas}</pre>
                </details>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
