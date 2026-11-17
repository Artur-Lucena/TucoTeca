import { useEffect, useState } from 'preact/hooks'
import { alturasMeses, dataDoBackup, MESES, normalizarResumo, type ResumoAno } from '../../estado/colecao'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { confirmar } from '../ui/Confirmacao'
import { bytes, horas } from '../../estado/formato'

interface Props {
  aoAvisar: AoAvisar
  aoMudou: () => void
}

interface Backup {
  nome: string
  bytes: number
}

/**
 * Coleção: backup manual, últimos backups, horas do ano, exportar/importar o
 * pacote (.zip) e os erros recentes do log — tudo legível, sem JSON cru.
 */
export function PainelColecao({ aoAvisar, aoMudou }: Props) {
  const [backups, setBackups] = useState<Backup[]>([])
  const [resumo, setResumo] = useState<ResumoAno | null>(null)
  const [erros, setErros] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)

  const carregar = async () => {
    try {
      const lista = await window.tucoteca.chamar<Backup[]>('backups.listar', { manter: 10 })
      setBackups(Array.isArray(lista) ? lista : [])
      setResumo(normalizarResumo(await window.tucoteca.chamar('estatisticas.ler')))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  useEffect(() => {
    void carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga única
  }, [])

  const backupAgora = async () => {
    setOcupado(true)
    try {
      const r = await window.tucoteca.chamar<{ jogos?: number }>('colecao.backup')
      aoAvisar(`Backup feito (${r?.jogos ?? 0} jogo(s)). Os 10 mais recentes ficam guardados.`)
      await carregar()
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const exportar = async () => {
    const pasta = await window.tucoteca.escolherPasta()
    if (!pasta) return
    setOcupado(true)
    try {
      await window.tucoteca.chamar('colecao.exportar', { pasta })
      aoAvisar('Coleção exportada como pacote .zip na pasta escolhida.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const importar = async () => {
    const caminho = await window.tucoteca.escolherArquivo([{ nome: 'Pacote da coleção (.zip)', extensoes: ['zip'] }])
    if (!caminho) return
    const ok = await confirmar({
      titulo: 'Importar coleção',
      texto: 'Os jogos, músicas e desejos do pacote entram na coleção atual. Antes, um backup é feito automaticamente. Os saves não são restaurados.',
      confirmar: 'Importar',
    })
    if (!ok) return
    setOcupado(true)
    try {
      await window.tucoteca.chamar('colecao.importar', { caminho, restaurar_saves: false })
      aoAvisar('Coleção importada.')
      await carregar()
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const verErros = async () => {
    if (erros !== null) return setErros(null)
    try {
      const r = await window.tucoteca.chamar<{ texto?: string }>('sistema.erros', { linhas: 40 })
      setErros(String(r?.texto ?? ''))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const alturas = resumo === null ? [] : alturasMeses(resumo.meses)

  return (
    <div class="form-config painel-paridade">
      <h2>Coleção</h2>
      <div class="detalhe-linha">
        <button type="button" class="acao primaria" disabled={ocupado} onClick={() => void backupAgora()}>
          Fazer backup agora
        </button>
        <button type="button" class="acao" disabled={ocupado} onClick={() => void exportar()}>
          Exportar coleção (.zip)
        </button>
        <button type="button" class="acao" disabled={ocupado} onClick={() => void importar()}>
          Importar coleção (.zip)
        </button>
      </div>

      <h4>Últimos backups</h4>
      {backups.length === 0 ? (
        <p class="sub">Nenhum backup ainda.</p>
      ) : (
        <ul class="lista-simples">
          {backups.map((b) => (
            <li key={b.nome}>
              <span>{dataDoBackup(b.nome) || b.nome}</span>
              <span class="sub">{bytes(b.bytes)}</span>
            </li>
          ))}
        </ul>
      )}

      {resumo !== null && (
        <>
          <h4>
            Horas jogadas em {resumo.ano}: {horas(resumo.total_horas)}
          </h4>
          <div class="grafico-meses" role="img" aria-label={`Horas por mês em ${resumo.ano}`}>
            {resumo.meses.map((h, i) => (
              <div key={MESES[i]} class="grafico-mes" title={`${MESES[i]}: ${horas(h)}`}>
                <span class="grafico-barra" style={{ height: `${alturas[i]}%` }} />
                <span class="grafico-rotulo">{MESES[i]}</span>
              </div>
            ))}
          </div>
          {resumo.jogos.length > 0 && (
            <ul class="lista-simples">
              {resumo.jogos.slice(0, 5).map((j) => (
                <li key={j.titulo}>
                  <span>{j.titulo}</span>
                  <span class="sub">{horas(j.horas)}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <h4>Diagnóstico</h4>
      <button type="button" class="acao" onClick={() => void verErros()}>
        {erros === null ? 'Ver erros recentes' : 'Ocultar erros'}
      </button>
      {erros !== null && <pre class="log-erros">{erros}</pre>}
    </div>
  )
}
