import { useState } from 'preact/hooks'
import { candidatosDeCapa, errosDeCapa, type CandidatoCapa } from '../../estado/capas'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { Modal } from '../ui'

interface Props {
  id: number
  titulo: string
  aoMudou: () => void
  aoAvisar: AoAvisar
}

/** Botão "Capas…" da página do jogo: abre a galeria das capas das fontes (Steam, SteamGridDB…) para escolher. */
export function EscolherCapa({ id, titulo, aoMudou, aoAvisar }: Props) {
  const [aberto, setAberto] = useState(false)
  const [capas, setCapas] = useState<CandidatoCapa[] | null>(null)
  const [erros, setErros] = useState<string[]>([])
  const [ocupado, setOcupado] = useState(false)

  const abrir = async (atualizar = false) => {
    setAberto(true)
    setOcupado(true)
    try {
      const r = await window.tucoteca.chamar('capas.buscar', { categoria: 'jogos', id, provedor: '', atualizar })
      setCapas(candidatosDeCapa(r))
      setErros(errosDeCapa(r))
    } catch (falha) {
      setCapas([])
      setErros([textoDeFalha(falha)])
    } finally {
      setOcupado(false)
    }
  }

  const aplicar = async (c: CandidatoCapa) => {
    setOcupado(true)
    try {
      await window.tucoteca.chamar('capas.aplicar', { categoria: 'jogos', id, candidato: c.original })
      aoAvisar(`Capa de ${titulo} trocada${c.fonte ? ` (${c.fonte})` : ''}.`)
      setAberto(false)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  return (
    <>
      <button type="button" class="acao" onClick={() => void abrir()} title="Escolher entre as capas das fontes">
        Capas…
      </button>
      <Modal aberto={aberto} aoFechar={() => setAberto(false)} titulo={`Capas de ${titulo}`} largura="860px">
        {capas === null || (ocupado && capas.length === 0) ? (
          <p class="sub">Procurando capas…</p>
        ) : capas.length === 0 ? (
          <p class="sub">Nenhuma capa encontrada{erros[0] ? ` (${erros[0]})` : ''}.</p>
        ) : (
          <div class="galeria-capas">
            {capas.map((c, i) => {
              const url = window.tucoteca.imagemUrl(c.preview)
              return (
                <button key={i} type="button" class="capa-opcao" disabled={ocupado} onClick={() => void aplicar(c)} title={`Usar esta capa${c.fonte ? ` (${c.fonte})` : ''}`}>
                  {url !== '' ? <img src={url} alt="" loading="lazy" /> : <span class="capa-vazia">{i + 1}</span>}
                  <span>{c.fonte || `Capa ${i + 1}`}</span>
                </button>
              )
            })}
          </div>
        )}
        <div class="detalhe-linha">
          <button type="button" class="acao" disabled={ocupado} onClick={() => void abrir(true)}>
            Procurar de novo
          </button>
          {erros.length > 0 && capas !== null && capas.length > 0 && <span class="sub">Avisos: {erros.join(' · ')}</span>}
        </div>
      </Modal>
    </>
  )
}
