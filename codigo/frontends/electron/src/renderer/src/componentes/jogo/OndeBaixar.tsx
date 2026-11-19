import { useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { Modal } from '../ui'

interface Fonte {
  titulo: string
  url: string
}

interface Resultado {
  steamrip: Fonte[]
  fitgirl: Fonte[]
  erros: string[]
}

const NOMES = { steamrip: 'SteamRIP', fitgirl: 'FitGirl' } as const

/** "Onde baixar": procura o título nos catálogos (SteamRIP, FitGirl) e abre a página escolhida no navegador. */
export function OndeBaixar({ titulo, aoAvisar }: { titulo: string; aoAvisar: AoAvisar }) {
  const [aberto, setAberto] = useState(false)
  const [r, setR] = useState<Resultado | null>(null)

  const procurar = async () => {
    setAberto(true)
    setR(null)
    try {
      const resp = await window.tucoteca.chamar<Partial<Resultado>>('desejos.buscar_fontes', { titulo })
      setR({ steamrip: resp?.steamrip ?? [], fitgirl: resp?.fitgirl ?? [], erros: resp?.erros ?? [] })
    } catch (falha) {
      setR({ steamrip: [], fitgirl: [], erros: [textoDeFalha(falha)] })
    }
  }

  const abrir = async (url: string) => {
    try {
      await window.tucoteca.abrirUrl(url)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <>
      <button type="button" class="acao" onClick={() => void procurar()} title="Procura nos catálogos e abre a página no navegador">
        Onde baixar
      </button>
      <Modal aberto={aberto} aoFechar={() => setAberto(false)} titulo={`Onde baixar ${titulo}`} largura="620px">
        {r === null ? (
          <p class="sub">Procurando nos catálogos…</p>
        ) : (
          <>
            {(['steamrip', 'fitgirl'] as const).map((chave) => (
              <div key={chave} class="onde-baixar-bloco">
                <h4>{NOMES[chave]}</h4>
                {r[chave].length === 0 ? (
                  <p class="sub">Nada encontrado.</p>
                ) : (
                  <ul class="lista-simples">
                    {r[chave].slice(0, 6).map((item, i) => (
                      <li key={`${chave}-${i}`}>
                        <span>{item.titulo}</span>
                        <button type="button" class="acao" onClick={() => void abrir(item.url)}>
                          Abrir página ↗
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
            {r.erros.length > 0 && <p class="sub">Avisos: {r.erros.join(' · ')}</p>}
            <p class="sub">A página abre no navegador; nada é baixado nem instalado pelo TucoTeca.</p>
          </>
        )}
      </Modal>
    </>
  )
}
