import { useEffect, useState } from 'preact/hooks'
import { resumoEmulador, type EmuladorStatus } from '../../estado/emulacao'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { jogoEmAndamento, listaTrabalhos } from '../../estado/trabalhos'
import { confirmar } from '../ui/Confirmacao'

interface Props {
  aoAvisar: AoAvisar
}

/**
 * Emuladores (Azahar/DeSmuME): versão local sem rede; "Verificar" consulta o
 * release (rede, sob ação do usuário) e "Atualizar" instala com confirmação
 * expressa, como trabalho com progresso no rodapé.
 */
export function PainelEmuladores({ aoAvisar }: Props) {
  const [itens, setItens] = useState<EmuladorStatus[]>([])
  const [ocupado, setOcupado] = useState<string | null>(null)

  const carregar = async () => {
    try {
      const r = await window.tucoteca.chamar<{ itens?: EmuladorStatus[] }>('emulacao.status')
      setItens(Array.isArray(r?.itens) ? r.itens : [])
    } catch (falha) {
      aoAvisar(`Emuladores: ${textoDeFalha(falha)}`, 'atencao')
    }
  }

  useEffect(() => {
    void carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga única
  }, [])

  const verificar = async (chave: string) => {
    setOcupado(chave)
    try {
      const r = await window.tucoteca.chamar<EmuladorStatus>('emulacao.consultar', { chave })
      setItens((atual) => atual.map((e) => (e.chave === chave ? { ...e, ...r } : e)))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(null)
    }
  }

  const atualizar = async (e: EmuladorStatus) => {
    const texto =
      `Baixar e instalar ${e.nome} ${e.tag}` +
      (e.tamanho_mb ? ` (${e.tamanho_mb} MB)` : '') +
      '? Feche o emulador antes. A pasta user/ (saves e configurações) não é tocada e a versão anterior fica guardada para recuperação.'
    if (!(await confirmar({ titulo: `Atualizar ${e.nome}`, texto, confirmar: 'Baixar e instalar' }))) return
    try {
      await window.tucoteca.chamar('emulacao.atualizar', { chave: e.chave, info: e.info ?? {} })
      aoAvisar(`Atualizando ${e.nome}… acompanhe no rodapé.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const jogando = jogoEmAndamento(listaTrabalhos.value) !== null

  return (
    <div class="form-config painel-paridade">
      <h2>Emuladores</h2>
      {itens.length === 0 ? (
        <p class="sub">Nenhum emulador conhecido.</p>
      ) : (
        <ul class="lista-simples">
          {itens.map((e) => (
            <li key={e.chave}>
              <span>
                <strong>{e.nome}</strong> — {resumoEmulador(e)}
              </span>
              <span class="detalhe-linha">
                <button type="button" class="acao" disabled={ocupado !== null} onClick={() => void verificar(e.chave)}>
                  {ocupado === e.chave ? 'Verificando…' : 'Verificar'}
                </button>
                {e.tag !== '' && e.atualizado !== true && (
                  <button type="button" class="acao primaria" disabled={jogando} onClick={() => void atualizar(e)}>
                    Atualizar
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {jogando && <p class="sub">Feche o jogo aberto para atualizar emuladores.</p>}
    </div>
  )
}
