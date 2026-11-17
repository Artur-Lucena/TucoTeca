import { cancelarTrabalho, listaTrabalhos } from '../../estado/trabalhos'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'

interface Props {
  aoAvisar: AoAvisar
}

/** Rodapé global: trabalho ativo (rótulo + barra + Parar). */
export function Atividade({ aoAvisar }: Props) {
  const ativo = listaTrabalhos.value.find(
    (t) => t.estado === 'rodando' || t.estado === 'cancelando',
  )
  if (ativo === undefined) return null
  const parar = async () => {
    try {
      await cancelarTrabalho(ativo.id)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }
  return (
    <div class="atividade">
      <span class="atividade-rotulo">{ativo.rotulo}…</span>
      {ativo.pct !== null && (
        <progress class="atividade-barra" max={100} value={ativo.pct ?? 0} />
      )}
      {ativo.cancelavel && ativo.estado !== 'cancelando' && (
        <button type="button" class="acao" onClick={() => void parar()}>
          Parar
        </button>
      )}
    </div>
  )
}
