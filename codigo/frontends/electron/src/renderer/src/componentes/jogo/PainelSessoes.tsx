import { dataHora } from '../../estado/formato'
import { useEffect, useState } from 'preact/hooks'
import { validarHoras } from '../../estado/jogos'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'

interface Sessao {
  arquivo: string
  gid?: number
  titulo: string
  inicio: string
}

interface Props {
  /** Muda quando o snapshot muda (ex.: contador de pendentes): recarrega a lista. */
  revisao: number
  aoMudou: () => void
  aoAvisar: AoAvisar
}

const quando = dataHora

/**
 * Sessões manuais abertas (ex.: jogo aberto como administrador, sem rastreio
 * automático): informar as horas fecha a sessão e soma no jogo.
 */
export function PainelSessoes({ revisao, aoMudou, aoAvisar }: Props) {
  const [sessoes, setSessoes] = useState<Sessao[]>([])
  const [horas, setHoras] = useState<Record<string, string>>({})

  useEffect(() => {
    let vivo = true
    void (async () => {
      try {
        const lista = await window.tucoteca.chamar<Sessao[]>('sessoes.listar')
        if (vivo) setSessoes(Array.isArray(lista) ? lista : [])
      } catch {
        // sem sessões legíveis o painel some; o aviso do sistema continua valendo
      }
    })()
    return () => {
      vivo = false
    }
  }, [revisao])

  if (sessoes.length === 0) return null

  const encerrar = async (s: Sessao) => {
    const valor = validarHoras(horas[s.arquivo] ?? '')
    if (valor === null) return aoAvisar('Informe as horas jogadas (maior que zero, ex.: 1,5).', 'atencao')
    try {
      await window.tucoteca.chamar('sessoes.encerrar', { arquivo: s.arquivo, horas: valor })
      setSessoes((atual) => atual.filter((x) => x.arquivo !== s.arquivo))
      aoAvisar(`${valor} h registradas em ${s.titulo || 'o jogo'}.`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="secao painel-paridade sessoes-abertas">
      <h2>Sessões abertas</h2>
      <p class="sub">Jogos abertos sem contagem automática de horas. Informe quanto jogou para fechar.</p>
      <ul class="lista-simples">
        {sessoes.map((s) => (
          <li key={s.arquivo}>
            <span>
              <strong>{s.titulo || 'Jogo'}</strong>
              <span class="sub"> desde {quando(s.inicio)}</span>
            </span>
            <span class="detalhe-linha">
              <input
                class="campo-horas"
                inputMode="decimal"
                placeholder="horas, ex.: 1,5"
                aria-label={`Horas jogadas em ${s.titulo}`}
                value={horas[s.arquivo] ?? ''}
                onInput={(e) => setHoras((atual) => ({ ...atual, [s.arquivo]: (e.target as HTMLInputElement).value }))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void encerrar(s)
                }}
              />
              <button type="button" class="acao primaria" onClick={() => void encerrar(s)}>
                Registrar e fechar
              </button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
