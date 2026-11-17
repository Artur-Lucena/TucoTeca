import { useState } from 'preact/hooks'
import { data } from '../../estado/formato'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import type { PaginaJogo } from '../../estado/paginaJogo'
import { ir } from '../../estado/rota'

interface Props {
  id: number
  pagina: PaginaJogo
  buscando: boolean
  aoAtualizarRetro: () => void
  aoAvisar: AoAvisar
}

/**
 * RetroAchievements (progresso da conta do usuário) e, abaixo, as conquistas
 * calculadas dos saves locais (catálogo Steam só como referência).
 */
export function ConquistasJogo({ id, pagina, buscando, aoAtualizarRetro, aoAvisar }: Props) {
  const retro = pagina.meta.retro
  const provedor = pagina.provedores.find((p) => p.chave === 'retro')
  return (
    <div class="conquistas-jogo">
      <section class="bloco-jogo">
        <div class="bloco-topo">
          <h3>RetroAchievements</h3>
          <button type="button" class="acao" onClick={aoAtualizarRetro} disabled={buscando || provedor?.configurado !== true}>
            {buscando ? 'Atualizando…' : '↻ Atualizar progresso'}
          </button>
        </div>
        {provedor?.configurado !== true && retro === null ? (
          <p class="sub">
            Informe seu usuário e a chave Web API do RetroAchievements em{' '}
            <button type="button" class="link-acao" onClick={() => ir('#/configuracoes')}>
              Configurações
            </button>{' '}
            para ver suas conquistas aqui. Funciona com jogos de Nintendo DS (casados pelo nome) ou com o id do jogo
            informado na aba Editar.
          </p>
        ) : retro === null ? (
          <p class="sub">
            Nenhum jogo do RetroAchievements ligado a este. Para Nintendo DS o nome é casado sozinho; para outros, informe o
            id do jogo (o número na URL do site) na aba Editar.
          </p>
        ) : (
          <>
            {provedor?.configurado !== true && (
              <p class="sub">Progresso salvo da última consulta; para atualizar, informe usuário e chave em Configurações.</p>
            )}
            <div class="conquistas-progresso">
              <progress max={retro.total} value={retro.ganhas} />
              <span>
                {retro.ganhas}/{retro.total} · {retro.pontos_ganhos}/{retro.pontos_total} pontos · {retro.titulo}
              </span>
            </div>
            <ul class="lista-retro">
              {retro.conquistas.map((c) => (
                <li key={c.id} class={c.ganha_em !== '' ? 'ganha' : ''}>
                  <span class="retro-marca" aria-hidden="true">
                    {c.ganha_em !== '' ? '🏆' : '🔒'}
                  </span>
                  <div>
                    <strong>{c.titulo}</strong>
                    <span class="sub">{c.descricao}</span>
                  </div>
                  <span class="retro-pontos">
                    {c.pontos} pts
                    {c.ganha_em !== '' && <small>{data(c.ganha_em.replace(' ', 'T'))}{c.hardcore ? ' · hardcore' : ''}</small>}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
      <ConquistasDoSave id={id} aoAvisar={aoAvisar} />
    </div>
  )
}

/** Conquistas avaliadas a partir do save local (antes no detalhe do jogo). */
function ConquistasDoSave({ id, aoAvisar }: { id: number; aoAvisar: Props['aoAvisar'] }) {
  const [conquistas, setConquistas] = useState<Array<Record<string, unknown>>>([])
  const [appid, setAppid] = useState('')
  const [regras, setRegras] = useState('')
  const [mostrarRegras, setMostrarRegras] = useState(false)

  const avaliar = async () => {
    try {
      const r = await window.tucoteca.chamar<{ itens?: Array<Record<string, unknown>>; desbloqueadas?: number; total?: number }>(
        'conquistas.avaliar',
        { id },
      )
      setConquistas(Array.isArray(r?.itens) ? r.itens : [])
      aoAvisar(`Conquistas: ${r?.desbloqueadas ?? 0}/${r?.total ?? 0} desbloqueadas.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const sincronizar = async () => {
    try {
      await window.tucoteca.chamar('conquistas.sincronizar', { id, appid: appid.trim(), save: '' })
      aoAvisar('Catálogo de conquistas sincronizado.')
      await avaliar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const salvarRegras = async () => {
    try {
      await window.tucoteca.chamar('conquistas.regras', { id, texto: regras })
      aoAvisar('Regras salvas.')
      await avaliar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const desbloqueadas = conquistas.filter((c) => c.desbloqueada === true).length
  return (
    <section class="bloco-jogo">
      <h3>Pelo save do jogo</h3>
      <p class="sub">Calculadas do save local; o catálogo da Steam serve só de referência (nada é lido da sua conta).</p>
      <div class="detalhe-linha">
        <input value={appid} onInput={(e) => setAppid((e.target as HTMLInputElement).value)} placeholder="App ID Steam (referência)" />
        <button type="button" class="acao" onClick={() => void sincronizar()}>
          Sincronizar catálogo
        </button>
        <button type="button" class="acao" onClick={() => void avaliar()}>
          Avaliar
        </button>
        <button type="button" class="acao" onClick={() => setMostrarRegras((v) => !v)}>
          {mostrarRegras ? 'Ocultar regras' : 'Regras'}
        </button>
      </div>
      {mostrarRegras && (
        <div class="detalhe-linha">
          <textarea
            value={regras}
            onInput={(e) => setRegras((e.target as HTMLTextAreaElement).value)}
            placeholder={'{"ID_DA_CONQUISTA": {"path": ["chave", "subchave"], "op": "eq", "value": true}}'}
          />
          <p class="sub">
            Uma regra por conquista: <code>path</code> é o caminho dentro do save (JSON) e <code>op</code> é eq, gte,
            contains ou exists (exists dispensa <code>value</code>).
          </p>
          <button type="button" class="acao" onClick={() => void salvarRegras()}>
            Salvar regras
          </button>
        </div>
      )}
      {conquistas.length > 0 && (
        <>
          <div class="conquistas-progresso">
            <progress max={conquistas.length} value={desbloqueadas} />
            <span>
              {desbloqueadas}/{conquistas.length} desbloqueadas
            </span>
          </div>
          <div class="conquistas-grid">
            {conquistas.map((c, i) => (
              <div key={i} class={`conquista-card${c.desbloqueada === true ? ' desbloqueada' : ''}`}>
                {c.icon_url ? (
                  <img class="conquista-icone" src={String(c.icon_url)} alt="" />
                ) : (
                  <div class="conquista-icone capa-vazia">🏆</div>
                )}
                <strong>{String(c.titulo ?? c.id ?? '')}</strong>
                <span>{String(c.status ?? '')}</span>
                {c.percent ? <span class="badge">{String(c.percent)}%</span> : null}
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
