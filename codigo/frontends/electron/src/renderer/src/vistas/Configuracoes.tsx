import { useEffect, useState } from 'preact/hooks'
import { PainelColecao } from '../componentes/PainelColecao'
import { PainelControles } from '../componentes/PainelControles'
import { PainelEmuladores } from '../componentes/PainelEmuladores'
import { PainelFerramentasMidia } from '../componentes/PainelFerramentasMidia'
import { PainelSaneamento } from '../componentes/PainelSaneamento'
import { textoDeFalha } from '../estado/notificacoes'

interface Props {
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou: () => void
}

/** Tela Configurações: aparência, provedores, emuladores, controles, manutenção e coleção. */
export function Configuracoes({ aoAvisar, aoMudou }: Props) {
  const [tema, setTema] = useState('')
  const [densidade, setDensidade] = useState('')
  const [autoBackup, setAutoBackup] = useState(true)
  const [steam, setSteam] = useState('')
  const [steamgrid, setSteamgrid] = useState('')
  const [spotifyId, setSpotifyId] = useState('')
  const [spotifySecret, setSpotifySecret] = useState('')

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

      <PainelControles aoAvisar={aoAvisar} />

      <PainelSaneamento aoAvisar={aoAvisar} aoMudou={aoMudou} />

      <PainelFerramentasMidia aoAvisar={aoAvisar} />

      <PainelColecao aoAvisar={aoAvisar} aoMudou={aoMudou} />
    </section>
  )
}
