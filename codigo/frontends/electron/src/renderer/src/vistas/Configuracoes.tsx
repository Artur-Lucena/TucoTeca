import { useEffect, useState } from 'preact/hooks'
import { PainelEmuladores } from '../componentes/PainelEmuladores'
import { textoDeFalha } from '../estado/notificacoes'

interface Props {
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou: () => void
}

/** Tela Configurações: aparência, provedores, estatísticas, backups e coleção. */
export function Configuracoes({ aoAvisar, aoMudou }: Props) {
  const [tema, setTema] = useState('')
  const [densidade, setDensidade] = useState('')
  const [autoBackup, setAutoBackup] = useState(true)
  const [steam, setSteam] = useState('')
  const [steamgrid, setSteamgrid] = useState('')
  const [spotifyId, setSpotifyId] = useState('')
  const [spotifySecret, setSpotifySecret] = useState('')
  const [estatisticas, setEstatisticas] = useState<Record<string, unknown> | null>(null)
  const [backups, setBackups] = useState<unknown[]>([])

  useEffect(() => {
    void (async () => {
      try {
        const a = await window.tucoteca.chamar<{ tema?: string; densidade?: string; auto_backup?: boolean }>('aparencia.ler')
        if (typeof a.tema === 'string') setTema(a.tema)
        if (typeof a.densidade === 'string') setDensidade(a.densidade)
        if (typeof a.auto_backup === 'boolean') setAutoBackup(a.auto_backup)
      } catch (falha) {
        aoAvisar(textoDeFalha(falha), 'atencao')
      }
    })()
  }, [])

  const salvarAparencia = async () => {
    try {
      await window.tucoteca.chamar('aparencia.salvar', { tema, densidade, auto_backup: autoBackup })
      aoAvisar('Aparência salva.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const salvarProvedores = async () => {
    try {
      await window.tucoteca.chamar('provedores.configurar', {
        steam,
        steamgrid,
        spotify_id: spotifyId,
        spotify_secret: spotifySecret,
      })
      aoAvisar('Provedores salvos.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const verEstatisticas = async () => {
    try {
      setEstatisticas(await window.tucoteca.chamar<Record<string, unknown>>('estatisticas.ler'))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const listarBackups = async () => {
    try {
      const r = await window.tucoteca.chamar<{ itens?: unknown[] }>('backups.listar', { manter: 10 })
      setBackups(r?.itens ?? [])
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const sincronizarSteam = async () => {
    try {
      const r = await window.tucoteca.chamar<Record<string, unknown>>('desejos.sincronizar_steam')
      aoAvisar(`Wishlist sincronizada: ${JSON.stringify(r)}`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const exportar = async () => {
    try {
      const pasta = await window.tucoteca.escolherPasta()
      if (pasta === null || pasta === '') return
      await window.tucoteca.chamar('colecao.exportar', { pasta })
      aoAvisar('Coleção exportada.')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const importar = async () => {
    try {
      const pasta = await window.tucoteca.escolherPasta()
      if (pasta === null || pasta === '') return
      await window.tucoteca.chamar('colecao.importar', { caminho: pasta, restaurar_saves: false })
      aoAvisar('Coleção importada.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="vista configuracoes">
      <header class="vista-topo">
        <h1>Configurações</h1>
      </header>

      <div class="form-config">
        <h2>Aparência</h2>
        <label>
          Tema
          <input value={tema} onInput={(e) => setTema((e.target as HTMLInputElement).value)} />
        </label>
        <label>
          Densidade
          <input value={densidade} onInput={(e) => setDensidade((e.target as HTMLInputElement).value)} />
        </label>
        <label>
          <input
            type="checkbox"
            checked={autoBackup}
            onChange={(e) => setAutoBackup((e.target as HTMLInputElement).checked)}
          />
          Backup automático pós-sessão
        </label>
        <button type="button" class="acao" onClick={() => void salvarAparencia()}>
          Salvar aparência
        </button>
      </div>

      <div class="form-config">
        <h2>Provedores</h2>
        <label>
          Steam ID
          <input value={steam} onInput={(e) => setSteam((e.target as HTMLInputElement).value)} />
        </label>
        <label>
          SteamGridDB key
          <input value={steamgrid} onInput={(e) => setSteamgrid((e.target as HTMLInputElement).value)} />
        </label>
        <label>
          Spotify client id
          <input value={spotifyId} onInput={(e) => setSpotifyId((e.target as HTMLInputElement).value)} />
        </label>
        <label>
          Spotify client secret
          <input
            type="password"
            value={spotifySecret}
            onInput={(e) => setSpotifySecret((e.target as HTMLInputElement).value)}
          />
        </label>
        <button type="button" class="acao" onClick={() => void salvarProvedores()}>
          Salvar provedores
        </button>
      </div>

      <PainelEmuladores aoAvisar={aoAvisar} />

      <div class="form-config">
        <h2>Manutenção</h2>
        <button type="button" class="acao" onClick={() => void verEstatisticas()}>
          Estatísticas
        </button>
        <button type="button" class="acao" onClick={() => void listarBackups()}>
          Backups
        </button>
        <button type="button" class="acao" onClick={() => void sincronizarSteam()}>
          Sincronizar Steam (wishlist)
        </button>
        <button type="button" class="acao" onClick={() => void exportar()}>
          Exportar coleção
        </button>
        <button type="button" class="acao" onClick={() => void importar()}>
          Importar coleção
        </button>
        {estatisticas !== null && <pre class="stats">{JSON.stringify(estatisticas, null, 2)}</pre>}
        {backups.length > 0 && <pre class="stats">{JSON.stringify(backups, null, 2)}</pre>}
      </div>
    </section>
  )
}
