import { useEffect, useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'

interface Props {
  aoAvisar: AoAvisar
}

interface Ferramenta {
  chave: string
  nome?: string
  instalado?: boolean
  site?: string
  descricao?: string
  suportado?: boolean
}

type Grupo = 'imagens' | 'equalizadores' | 'videos'

const TITULO: Record<Grupo, string> = {
  imagens: 'Editores de imagem',
  equalizadores: 'Equalizadores',
  videos: 'Players de vídeo',
}

/** Ferramentas externas de mídia: abre as instaladas; as demais levam ao site oficial. */
export function PainelFerramentasMidia({ aoAvisar }: Props) {
  const [grupos, setGrupos] = useState<Record<Grupo, Ferramenta[]> | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        setGrupos(await window.tucoteca.chamar<Record<Grupo, Ferramenta[]>>('ferramentas.listar'))
      } catch (falha) {
        aoAvisar(`Ferramentas: ${textoDeFalha(falha)}`, 'atencao')
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga única
  }, [])

  const abrir = async (tipo: Grupo, f: Ferramenta) => {
    try {
      await window.tucoteca.chamar('ferramentas.abrir', { tipo, nome: f.chave, caminho: '' })
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const site = async (url: string) => {
    try {
      await window.tucoteca.abrirUrl(url)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  if (grupos === null) return null

  return (
    <div class="form-config painel-paridade">
      <h2>Ferramentas de mídia</h2>
      {(Object.keys(TITULO) as Grupo[]).map((tipo) => (
        <div key={tipo}>
          <h4>{TITULO[tipo]}</h4>
          <ul class="lista-simples">
            {(grupos[tipo] ?? [])
              .filter((f) => f.suportado !== false)
              .map((f) => (
                <li key={f.chave}>
                  <span title={f.descricao ?? ''}>
                    {f.nome ?? f.chave} {f.instalado ? '' : '— não instalado'}
                  </span>
                  {f.instalado ? (
                    <button type="button" class="acao" onClick={() => void abrir(tipo, f)}>
                      Abrir
                    </button>
                  ) : (
                    f.site && (
                      <button type="button" class="acao" onClick={() => void site(String(f.site))}>
                        Site oficial ↗
                      </button>
                    )
                  )}
                </li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
