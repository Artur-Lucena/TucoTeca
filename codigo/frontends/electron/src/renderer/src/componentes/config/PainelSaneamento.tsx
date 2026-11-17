import { useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { jogoEmAndamento, listaTrabalhos } from '../../estado/trabalhos'
import { confirmar } from '../ui/Confirmacao'

interface Props {
  aoAvisar: AoAvisar
  aoMudou: () => void
}

interface Plano {
  ok?: boolean
  pasta?: string
  exe?: string | null
  precisa_instalar?: boolean
  quarentenaveis?: number
  avisos?: string[]
  erro?: string
}

/**
 * Sanear uma pasta de jogo: primeiro o plano (só leitura), depois aplicar com
 * confirmação. Instaladores vão para `.hub-lixo` (reversível), nada é apagado.
 */
export function PainelSaneamento({ aoAvisar, aoMudou }: Props) {
  const [plano, setPlano] = useState<Plano | null>(null)
  const [ocupado, setOcupado] = useState(false)

  const analisar = async () => {
    const caminho = await window.tucoteca.escolherPasta()
    if (!caminho) return
    setOcupado(true)
    try {
      setPlano(await window.tucoteca.chamar<Plano>('manutencao.plano', { caminho }))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const aplicar = async () => {
    if (!plano?.pasta) return
    const texto =
      `Sanear "${plano.pasta}"?` +
      (plano.quarentenaveis ? ` ${plano.quarentenaveis} instalador(es) vão para .hub-lixo (dá para recuperar).` : '')
    if (!(await confirmar({ titulo: 'Sanear pasta', texto, confirmar: 'Sanear' }))) return
    setOcupado(true)
    try {
      await window.tucoteca.chamar('manutencao.sanear', { caminho: plano.pasta })
      aoAvisar('Pasta saneada.')
      setPlano(null)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const jogando = jogoEmAndamento(listaTrabalhos.value) !== null

  return (
    <div class="form-config painel-paridade">
      <h2>Sanear pasta de jogo</h2>
      <p class="sub">Acha o executável e separa instaladores que sobraram. Primeiro mostra o plano; nada muda sem confirmar.</p>
      <button type="button" class="acao" disabled={ocupado} onClick={() => void analisar()}>
        Escolher pasta e analisar…
      </button>
      {plano !== null && (
        <div>
          {plano.ok !== true ? (
            <p class="sub">{plano.erro || plano.avisos?.[0] || 'Não deu para analisar esta pasta.'}</p>
          ) : (
            <ul class="lista-simples">
              <li>Pasta: {plano.pasta}</li>
              <li>
                {plano.precisa_instalar
                  ? 'Só há instalador: rode-o primeiro; a pasta fica como está.'
                  : `Executável: ${plano.exe ?? '—'}`}
              </li>
              {(plano.avisos ?? []).map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          )}
          {plano.ok === true && !plano.precisa_instalar && (
            <button type="button" class="acao primaria" disabled={ocupado || jogando} onClick={() => void aplicar()}>
              Aplicar saneamento
            </button>
          )}
        </div>
      )}
    </div>
  )
}
