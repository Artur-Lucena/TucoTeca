import { useEffect, useState } from 'preact/hooks'
import { acaoDaIntegracao, type IntegracaoDTO } from '../estado/integracoes'
import { textoDeFalha } from '../estado/notificacoes'

interface Props {
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  /** Navegação interna (o card de download manda para a tela Downloads). */
  aoNavegar: (secao: string) => void
}

interface ResultadoCatalogo {
  titulo?: string
  url?: string
}

interface RespostaBusca {
  itens: ResultadoCatalogo[]
  erros: string[]
}

const TIPOS = ['link', 'catalogo', 'emulador', 'download']

const CAMPOS_VAZIOS = { chave: '', nome: '', descricao: '', tipo: 'link', url: '' }

/** Tela Integrações: cartões do registro, busca por catálogo e personalizadas. */
export function Integracoes({ aoAvisar, aoNavegar }: Props) {
  const [itens, setItens] = useState<IntegracaoDTO[]>([])
  const [termos, setTermos] = useState<Record<string, string>>({})
  const [respostas, setRespostas] = useState<Record<string, RespostaBusca>>({})
  const [ocupados, setOcupados] = useState<Record<string, boolean>>({})
  const [formAberto, setFormAberto] = useState(false)
  const [campos, setCampos] = useState(CAMPOS_VAZIOS)
  const [erroForm, setErroForm] = useState('')

  const carregar = async () => {
    try {
      setItens(await window.tucoteca.chamar<IntegracaoDTO[]>('integracoes.listar'))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  useEffect(() => {
    void carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carregar só usa setters
  }, [])

  const abrirExterno = async (url: string) => {
    try {
      await window.tucoteca.abrirUrl(url)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const agir = async (item: IntegracaoDTO) => {
    const acao = acaoDaIntegracao(item)
    if (acao.tipo === 'download') {
      aoNavegar('downloads')
      return
    }
    if (acao.tipo === 'indisponivel') {
      aoAvisar(acao.motivo, 'atencao')
      return
    }
    if (acao.tipo === 'abrir') {
      try {
        const dados = await window.tucoteca.chamar<{ url?: string }>('integracoes.url', {
          chave: item.chave,
        })
        if (typeof dados.url === 'string') await abrirExterno(dados.url)
      } catch (falha) {
        aoAvisar(textoDeFalha(falha), 'atencao')
      }
      return
    }

    const termo = (termos[item.chave] ?? '').trim()
    setOcupados((atual) => ({ ...atual, [item.chave]: true }))
    try {
      if (item.url !== undefined && item.url !== '') {
        if (termo === '') {
          aoAvisar('Digite um termo para buscar no site.', 'atencao')
          return
        }
        const dados = await window.tucoteca.chamar<{ url?: string }>('integracoes.url', {
          chave: item.chave,
          termo,
        })
        if (typeof dados.url === 'string') await abrirExterno(dados.url)
        return
      }
      if (termo.length < 2) {
        aoAvisar('Digite pelo menos dois caracteres.', 'atencao')
        return
      }
      const resposta = await window.tucoteca.chamar<{ itens?: ResultadoCatalogo[]; erros?: string[] }>(
        'integracoes.buscar',
        { chave: item.chave, termo },
      )
      const limpa: RespostaBusca = {
        itens: (resposta.itens ?? []).slice(0, 8),
        erros: (resposta.erros ?? []).map((erro) => String(erro)),
      }
      setRespostas((atual) => ({ ...atual, [item.chave]: limpa }))
      if (limpa.erros.length > 0) aoAvisar(limpa.erros[0], 'atencao')
      else if (limpa.itens.length === 0) aoAvisar(`Nada encontrado para "${termo}".`, 'atencao')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupados((atual) => ({ ...atual, [item.chave]: false }))
    }
  }

  const salvar = async () => {
    setErroForm('')
    try {
      const salva = await window.tucoteca.chamar<IntegracaoDTO>('integracoes.adicionar', {
        dados: { ...campos },
      })
      aoAvisar(`Integração '${String(salva?.nome ?? campos.nome)}' adicionada.`)
      setCampos(CAMPOS_VAZIOS)
      setFormAberto(false)
      await carregar()
    } catch (falha) {
      setErroForm(textoDeFalha(falha))
    }
  }

  const remover = async (item: IntegracaoDTO) => {
    try {
      await window.tucoteca.chamar('integracoes.remover', { chave: item.chave })
      aoAvisar(`Integração '${item.nome}' removida.`)
      await carregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="vista integracoes">
      <header class="vista-topo">
        <h1>Integrações ({itens.length})</h1>
        <div class="vista-acoes">
          <button type="button" class="acao" onClick={() => setFormAberto((atual) => !atual)}>
            + Adicionar
          </button>
        </div>
      </header>

      {formAberto && (
        <div class="form-integracao">
          <label>
            Chave (identificador único)
            <input
              class="campo-chave"
              type="text"
              value={campos.chave}
              onInput={(evento) =>
                setCampos((atual) => ({ ...atual, chave: (evento.target as HTMLInputElement).value }))
              }
            />
          </label>
          <label>
            Nome
            <input
              class="campo-nome"
              type="text"
              value={campos.nome}
              onInput={(evento) =>
                setCampos((atual) => ({ ...atual, nome: (evento.target as HTMLInputElement).value }))
              }
            />
          </label>
          <label>
            Descrição
            <input
              class="campo-descricao"
              type="text"
              value={campos.descricao}
              onInput={(evento) =>
                setCampos((atual) => ({
                  ...atual,
                  descricao: (evento.target as HTMLInputElement).value,
                }))
              }
            />
          </label>
          <label>
            Tipo
            <select
              class="campo-tipo"
              value={campos.tipo}
              onChange={(evento) =>
                setCampos((atual) => ({ ...atual, tipo: (evento.target as HTMLSelectElement).value }))
              }
            >
              {TIPOS.map((tipo) => (
                <option key={tipo} value={tipo}>
                  {tipo}
                </option>
              ))}
            </select>
          </label>
          <label>
            URL (use {'{q}'} para busca)
            <input
              class="campo-url"
              type="text"
              value={campos.url}
              onInput={(evento) =>
                setCampos((atual) => ({ ...atual, url: (evento.target as HTMLInputElement).value }))
              }
            />
          </label>
          <button type="button" class="acao" onClick={() => void salvar()}>
            Salvar integração
          </button>
          <button type="button" class="acao" onClick={() => setFormAberto(false)}>
            Cancelar
          </button>
          {erroForm !== '' && <p class="erro-form">{erroForm}</p>}
        </div>
      )}

      <div class="grade-integracoes">
        {itens.map((item) => {
          const acao = acaoDaIntegracao(item)
          const resposta = respostas[item.chave]
          return (
            <article class="integracao" key={item.chave}>
              <span class="integracao-inicial" style={{ background: item.cor ?? '#2a2e39' }}>
                {item.inicial ?? '•'}
              </span>
              <div class="integracao-corpo">
                <h3>{item.nome}</h3>
                <p>{item.descricao ?? ''}</p>
                <div class="integracao-selos">
                  <span class="selo">{item.tipo}</span>
                  {(item.capacidades ?? []).map((capacidade) => (
                    <span class="selo" key={capacidade}>
                      {capacidade}
                    </span>
                  ))}
                  {item.personalizada === true && <span class="selo">personalizada</span>}
                </div>
              </div>
              <div class="integracao-acoes">
                {acao.tipo === 'buscar' && (
                  <input
                    class="busca-integracao"
                    type="search"
                    placeholder={item.url !== undefined && item.url !== '' ? 'Termo…' : 'Buscar no catálogo…'}
                    value={termos[item.chave] ?? ''}
                    onInput={(evento) =>
                      setTermos((atual) => ({
                        ...atual,
                        [item.chave]: (evento.target as HTMLInputElement).value,
                      }))
                    }
                    onKeyDown={(evento) => {
                      if (evento.key === 'Enter') void agir(item)
                    }}
                  />
                )}
                <button
                  type="button"
                  class="acao"
                  onClick={() => void agir(item)}
                  disabled={ocupados[item.chave] === true}
                >
                  {ocupados[item.chave] === true ? 'Consultando…' : acao.rotulo}
                </button>
                {item.personalizada === true && (
                  <button type="button" class="acao perigo" onClick={() => void remover(item)}>
                    Remover
                  </button>
                )}
              </div>
              {resposta !== undefined && resposta.itens.length > 0 && (
                <ul class="integracao-resultados">
                  {resposta.itens.map((resultado, posicao) => (
                    <li key={`${item.chave}-${posicao}`}>
                      <button
                        type="button"
                        class="link-resultado"
                        onClick={() => void abrirExterno(String(resultado.url ?? ''))}
                      >
                        {String(resultado.titulo ?? resultado.url ?? 'resultado')}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
