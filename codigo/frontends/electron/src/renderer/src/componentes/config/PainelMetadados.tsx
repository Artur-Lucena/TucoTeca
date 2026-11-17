import { useEffect, useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import type { ProvedorMeta } from '../../estado/paginaJogo'

interface Props {
  aoAvisar: AoAvisar
}

interface Estado {
  provedores: ProvedorMeta[]
  retro_user: string
  retro_key: boolean
}

/** Configurações › Dados dos jogos: quais provedores rodam, login do RetroAchievements e busca em lote. */
export function PainelMetadados({ aoAvisar }: Props) {
  const [estado, setEstado] = useState<Estado | null>(null)
  const [usuario, setUsuario] = useState('')
  const [chave, setChave] = useState('')

  const aplicar = (r: unknown) => {
    const e = (r ?? {}) as Partial<Estado>
    setEstado({ provedores: Array.isArray(e.provedores) ? e.provedores : [], retro_user: String(e.retro_user ?? ''), retro_key: e.retro_key === true })
    setUsuario(String(e.retro_user ?? ''))
  }

  useEffect(() => {
    window.tucoteca.chamar('metadados.provedores').then(aplicar).catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carrega uma vez
  }, [])

  const alternar = async (p: ProvedorMeta) => {
    try {
      aplicar(await window.tucoteca.chamar('metadados.configurar', { ligados: { [p.chave]: !p.ligado } }))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const salvarRetro = async () => {
    try {
      aplicar(await window.tucoteca.chamar('metadados.configurar', { retro_user: usuario.trim(), retro_key: chave.trim() }))
      setChave('')
      aoAvisar('RetroAchievements salvo.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const buscarTodos = async () => {
    try {
      await window.tucoteca.chamar('jogos.enriquecer_lote')
      aoAvisar('Buscando dados dos jogos que ainda não têm; acompanhe no rodapé.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <div class="form-config">
      <h2>Dados dos jogos</h2>
      <p class="sub">Descrição, arte, conquistas e horas para zerar. A rede só é usada quando você pede.</p>
      {estado === null ? (
        <p class="sub">Carregando…</p>
      ) : (
        <ul class="lista-provedores">
          {estado.provedores.map((p) => (
            <li key={p.chave}>
              <label class="marcar">
                <input type="checkbox" checked={p.ligado} onChange={() => void alternar(p)} />
                <span>
                  <strong>{p.nome}</strong> — {p.descricao}
                  {p.precisa_credencial && !p.configurado && <span class="sub"> (falta credencial)</span>}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      <label>
        Usuário RetroAchievements
        <input value={usuario} onInput={(e) => setUsuario((e.target as HTMLInputElement).value)} autoComplete="off" />
      </label>
      <label>
        Chave Web API RetroAchievements {estado?.retro_key === true && <span class="sub">(salva; deixe vazio para manter)</span>}
        <input type="password" value={chave} onInput={(e) => setChave((e.target as HTMLInputElement).value)} autoComplete="off" />
      </label>
      <p class="sub">A chave fica no seu Controle de usuário do site (retroachievements.org › Configurações).</p>
      <div class="detalhe-linha">
        <button type="button" class="acao" onClick={() => void salvarRetro()}>
          Salvar RetroAchievements
        </button>
        <button type="button" class="acao" onClick={() => void buscarTodos()}>
          Buscar dados dos jogos sem dados
        </button>
      </div>
    </div>
  )
}
