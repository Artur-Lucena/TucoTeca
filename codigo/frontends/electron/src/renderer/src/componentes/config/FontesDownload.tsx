import { useEffect, useState } from 'preact/hooks'
import { dataCurta, type FonteDownload } from '../../estado/fontes'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { listaTrabalhos } from '../../estado/trabalhos'
import { confirmar } from '../ui/Confirmacao'

/** Integrações › Fontes de download: adicionar (endereço de JSON no formato do Hydra), atualizar e remover. */
export function FontesDownload({ aoAvisar }: { aoAvisar: AoAvisar }) {
  const [fontes, setFontes] = useState<FonteDownload[]>([])
  const [url, setUrl] = useState('')

  const trabalho = listaTrabalhos.value.find(
    (t) => t.escopo === 'fontes' && (t.estado === 'rodando' || t.estado === 'cancelando'),
  )
  const ocupado = trabalho !== undefined

  const carregar = () => {
    window.tucoteca
      .chamar<FonteDownload[]>('fontes.listar')
      .then((r) => setFontes(Array.isArray(r) ? r : []))
      .catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))
  }
  // recarrega ao abrir e quando um trabalho de fontes termina
  useEffect(carregar, [ocupado])

  const adicionar = async (evento: Event) => {
    evento.preventDefault()
    if (!url.trim().startsWith('https://')) {
      aoAvisar('O endereço da fonte precisa começar com https://.', 'atencao')
      return
    }
    try {
      await window.tucoteca.chamar('fontes.adicionar', { url: url.trim() })
      aoAvisar('Baixando a lista da fonte… (o progresso aparece no rodapé)')
      setUrl('')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const atualizar = async (id = '') => {
    try {
      await window.tucoteca.chamar('fontes.atualizar', { id })
      aoAvisar(id ? 'Atualizando a fonte…' : 'Atualizando todas as fontes…')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const remover = async (f: FonteDownload) => {
    if (!(await confirmar({ titulo: 'Remover fonte', texto: `Remover “${f.nome}”? Os jogos já baixados ficam.`, confirmar: 'Remover' }))) return
    try {
      await window.tucoteca.chamar('fontes.remover', { id: f.id })
      carregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="bloco-config fontes-download">
      <h2>Fontes de download ({fontes.length})</h2>
      <p class="sub">
        Listas no formato do Hydra (um endereço https de JSON). Com elas, “Baixar” na loja e nos Desejos mostra as
        opções e baixa dentro do app. O TucoTeca não traz nenhuma fonte: adicione só as que você confia e
        responda pelo que baixar.
      </p>
      <form class="fontes-form" onSubmit={(e) => void adicionar(e)}>
        <input
          class="busca"
          type="url"
          placeholder="https://…/fonte.json"
          value={url}
          onInput={(e) => setUrl((e.target as HTMLInputElement).value)}
        />
        <button type="submit" class="acao primaria" disabled={ocupado || url.trim() === ''}>
          {ocupado ? 'Baixando…' : 'Adicionar'}
        </button>
        <button type="button" class="acao" disabled={ocupado || fontes.length === 0} onClick={() => void atualizar()}>
          Atualizar todas
        </button>
      </form>
      {fontes.length > 0 && (
        <ul class="lista-simples fontes-lista">
          {fontes.map((f) => (
            <li key={f.id}>
              <div class="fonte-textos">
                <strong>{f.nome}</strong>
                <span>
                  {f.total} downloads · atualizada em {dataCurta(f.atualizada_em) || '—'}
                  {f.erro !== '' ? ` · última falha: ${f.erro}` : ''}
                </span>
                <span class="sub fonte-url">{f.url}</span>
              </div>
              <div class="detalhe-linha">
                <button type="button" class="acao" disabled={ocupado} onClick={() => void atualizar(f.id)}>
                  Atualizar
                </button>
                <button type="button" class="acao perigo" disabled={ocupado} onClick={() => void remover(f)}>
                  Remover
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
