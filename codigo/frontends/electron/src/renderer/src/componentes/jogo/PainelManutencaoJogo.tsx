import { useState } from 'preact/hooks'
import { lerDiagnostico, tamanhoLegivel, type Diagnostico, type LeituraDiagnostico } from '../../estado/manutencao'
import { textoDeFalha } from '../../estado/notificacoes'
import { confirmar } from '../ui/Confirmacao'

interface Props {
  id: number
  bloqueado: boolean
  aoMudou: () => void
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

const FILTRO_EXE = [{ nome: 'Executáveis', extensoes: ['exe', 'bat'] }]
const FILTRO_ROM = [{ nome: 'ROMs', extensoes: ['3ds', 'cci', 'cia', 'cxi', 'nds', 'zip', '7z'] }]

/**
 * Manutenção do jogo: verificar exe/ROM e religar (com backup, no núcleo),
 * espaço em disco da pasta e abrir como administrador (UAC, com confirmação).
 */
export function PainelManutencaoJogo({ id, bloqueado, aoMudou, aoAvisar }: Props) {
  const [leitura, setLeitura] = useState<LeituraDiagnostico | null>(null)
  const [disco, setDisco] = useState('')
  const [ocupado, setOcupado] = useState(false)

  const verificar = async () => {
    setOcupado(true)
    try {
      setLeitura(lerDiagnostico(await window.tucoteca.chamar<Diagnostico>('jogo.diagnosticar', { id })))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const religar = async (campo: 'executable_path' | 'launch_options', caminho: string) => {
    setOcupado(true)
    try {
      const d = await window.tucoteca.chamar<Diagnostico>('jogo.religar', { id, campo, caminho })
      setLeitura(lerDiagnostico(d))
      aoMudou()
      aoAvisar(campo === 'executable_path' ? 'Executável atualizado.' : 'ROM atualizada.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  const escolher = async (campo: 'executable_path' | 'launch_options') => {
    const caminho = await window.tucoteca.escolherArquivo(campo === 'executable_path' ? FILTRO_EXE : FILTRO_ROM)
    if (caminho) await religar(campo, caminho)
  }

  const medirDisco = async () => {
    setDisco('Medindo…')
    try {
      const r = await window.tucoteca.chamar<{ bytes?: number; arquivos?: number; parcial?: boolean }>('jogo.disco', { id })
      const texto = `${tamanhoLegivel(Number(r?.bytes ?? 0))} em ${Number(r?.arquivos ?? 0).toLocaleString('pt-BR')} arquivo(s)`
      setDisco(r?.parcial ? `${texto} (contagem parcial)` : texto)
    } catch (falha) {
      setDisco('')
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const elevado = async () => {
    const texto =
      'O Windows vai pedir confirmação (UAC). ' +
      'As horas não são contadas automaticamente: a sessão fica aberta no Início até você registrar.'
    if (!(await confirmar({ titulo: 'Abrir como administrador', texto, confirmar: 'Abrir' }))) return
    try {
      const r = await window.tucoteca.chamar<{ aviso?: string }>('jogo.jogar_elevado', { id })
      aoAvisar(r?.aviso || 'Jogo aberto como administrador. Registre as horas ao terminar.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const travado = ocupado || bloqueado

  return (
    <div class="painel-paridade">
      <div class="detalhe-linha">
        <button type="button" class="acao" disabled={ocupado} onClick={() => void verificar()}>
          Verificar arquivos
        </button>
        <button type="button" class="acao" onClick={() => void medirDisco()}>
          Espaço em disco
        </button>
        <button type="button" class="acao" disabled={bloqueado} onClick={() => void elevado()}>
          Abrir como administrador
        </button>
        {disco !== '' && <span class="sub">{disco}</span>}
      </div>
      {leitura !== null && (
        <>
          <ul class="lista-simples">
            {leitura.linhas.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          {leitura.acoes.map((acao) => {
            if (acao.tipo === 'usar-emulador-atual')
              return (
                <button key="atual" type="button" class="acao primaria" disabled={travado} onClick={() => void religar('executable_path', acao.caminho)}>
                  Usar o emulador instalado agora
                </button>
              )
            if (acao.tipo === 'escolher-exe')
              return (
                <button key="exe" type="button" class="acao" disabled={travado} onClick={() => void escolher('executable_path')}>
                  Escolher executável…
                </button>
              )
            return (
              <div key="rom">
                {acao.candidatos.length > 0 && (
                  <ul class="lista-simples">
                    {acao.candidatos.map((c) => (
                      <li key={c}>
                        <span>{c}</span>
                        <button type="button" class="acao" disabled={travado} onClick={() => void religar('launch_options', c)}>
                          Usar esta
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <button type="button" class="acao" disabled={travado} onClick={() => void escolher('launch_options')}>
                  Escolher ROM…
                </button>
              </div>
            )
          })}
        </>
      )}
      {bloqueado && <p class="sub">Feche o jogo aberto para religar arquivos ou abrir como administrador.</p>}
    </div>
  )
}
