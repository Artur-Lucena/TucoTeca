import { useState } from 'preact/hooks'
import { arquivoBaixado, downloadsNoApp, ehAtualizacao, emAndamento, estadoDoDownload, pastaDe } from '../../estado/downloads'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'
import { cancelarTrabalho, listaTrabalhos } from '../../estado/trabalhos'

interface Props {
  aoAvisar: AoAvisar
}

/** Downloads feitos pelo próprio app (fontes https e atualização): progresso, cancelar e importar. */
export function DownloadsNoApp({ aoAvisar }: Props) {
  const [importando, setImportando] = useState<number | null>(null)
  const lista = downloadsNoApp(listaTrabalhos.value)
  if (lista.length === 0) return null

  const agir = async (acao: () => Promise<unknown>) => {
    try {
      await acao()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const importar = async (id: number, caminho: string) => {
    setImportando(id)
    await agir(async () => {
      await window.tucoteca.chamar('torrents.importar', { caminho })
      aoAvisar('Importando o download… (o progresso aparece no rodapé)')
    })
    setImportando(null)
  }

  return (
    <section class="downloads-app">
      <h2>Baixando no app</h2>
      <ul class="lista-downloads">
        {lista.map((t) => {
          const arquivo = arquivoBaixado(t)
          return (
            <li class={`linha-download${t.estado === 'erro' ? ' falhou' : ''}`} key={t.id}>
              <span class="download-icone">{emAndamento(t) ? '↓' : t.estado === 'ok' ? '✓' : '×'}</span>
              <div class="download-textos">
                <strong>{t.rotulo.replace(/^Baixar /, '')}</strong>
                <span>{estadoDoDownload(t)}</span>
              </div>
              <progress class="download-barra" max={100} value={t.estado === 'ok' ? 100 : (t.pct ?? undefined)} />
              <div class="download-acoes">
                {emAndamento(t) && t.cancelavel && (
                  <button type="button" class="acao" disabled={t.estado === 'cancelando'} onClick={() => void agir(() => cancelarTrabalho(t.id))}>
                    Cancelar
                  </button>
                )}
                {arquivo !== '' && ehAtualizacao(t) && (
                  <button type="button" class="acao primaria" onClick={() => ir('#/configuracoes')}>
                    Instalar
                  </button>
                )}
                {arquivo !== '' && !ehAtualizacao(t) && (
                  <button type="button" class="acao primaria" disabled={importando === t.id} onClick={() => void importar(t.id, arquivo)}>
                    {importando === t.id ? 'Importando…' : 'Importar'}
                  </button>
                )}
                {arquivo !== '' && (
                  <button type="button" class="acao" onClick={() => void agir(() => window.tucoteca.abrirPasta(pastaDe(arquivo)))}>
                    Abrir pasta
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
