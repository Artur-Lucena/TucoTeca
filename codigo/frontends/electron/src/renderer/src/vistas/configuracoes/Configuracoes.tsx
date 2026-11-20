import { useEffect, useState } from 'preact/hooks'
import { PainelAtualizacao } from '../../componentes/config/PainelAtualizacao'
import { PainelColecao } from '../../componentes/config/PainelColecao'
import { PainelControles } from '../../componentes/config/PainelControles'
import { PainelEmuladores } from '../../componentes/config/PainelEmuladores'
import { PainelFerramentasMidia } from '../../componentes/config/PainelFerramentasMidia'
import { PainelMetadados } from '../../componentes/config/PainelMetadados'
import { PainelSaneamento } from '../../componentes/config/PainelSaneamento'
import {
  aplicarAparencia,
  DENSIDADES,
  ESCALA_MAX,
  ESCALA_MIN,
  normalizarAparencia,
  TEMAS,
  type Aparencia,
} from '../../estado/aparencia'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'

interface Props {
  aoAvisar: AoAvisar
  aoMudou: () => void
}

/** Tela Configurações: aparência, provedores, emuladores, controles, manutenção e coleção. */
export function Configuracoes({ aoAvisar, aoMudou }: Props) {
  const [aparencia, setAparencia] = useState<Aparencia>(normalizarAparencia({}))
  const [steam, setSteam] = useState('')
  const [steamgrid, setSteamgrid] = useState('')
  const [spotifyId, setSpotifyId] = useState('')
  const [spotifySecret, setSpotifySecret] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        setAparencia(normalizarAparencia(await window.tucoteca.chamar('aparencia.ler')))
      } catch (falha) {
        aoAvisar(textoDeFalha(falha), 'atencao')
      }
    })()
  }, [])

  const salvarAparencia = async () => {
    try {
      const salva = normalizarAparencia(
        await window.tucoteca.chamar('aparencia.salvar', {
          tema: aparencia.tema,
          densidade: aparencia.densidade,
          escala_texto: aparencia.escala_texto,
          auto_backup: aparencia.auto_backup,
        }),
      )
      setAparencia(salva)
      aplicarAparencia(salva)
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

      <PainelAtualizacao aoAvisar={aoAvisar} />

      <div class="form-config">
        <h2>Aparência</h2>
        <label>
          Tema
          <select
            value={aparencia.tema}
            onChange={(e) => setAparencia({ ...aparencia, tema: (e.target as HTMLSelectElement).value as Aparencia['tema'] })}
          >
            {TEMAS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.rotulo}
              </option>
            ))}
          </select>
        </label>
        <label>
          Densidade
          <select
            value={aparencia.densidade}
            onChange={(e) =>
              setAparencia({ ...aparencia, densidade: (e.target as HTMLSelectElement).value as Aparencia['densidade'] })
            }
          >
            {DENSIDADES.map((d) => (
              <option key={d.valor} value={d.valor}>
                {d.rotulo}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tamanho do texto: {Math.round(aparencia.escala_texto * 100)}%
          <input
            type="range"
            min={ESCALA_MIN}
            max={ESCALA_MAX}
            step={0.05}
            value={aparencia.escala_texto}
            onInput={(e) => setAparencia({ ...aparencia, escala_texto: Number((e.target as HTMLInputElement).value) })}
          />
        </label>
        <label class="marcar">
          <input
            type="checkbox"
            checked={aparencia.auto_backup}
            onChange={(e) => setAparencia({ ...aparencia, auto_backup: (e.target as HTMLInputElement).checked })}
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

      <PainelMetadados aoAvisar={aoAvisar} />

      <PainelEmuladores aoAvisar={aoAvisar} />

      <PainelControles aoAvisar={aoAvisar} />

      <PainelSaneamento aoAvisar={aoAvisar} aoMudou={aoMudou} />

      <PainelFerramentasMidia aoAvisar={aoAvisar} />

      <PainelColecao aoAvisar={aoAvisar} aoMudou={aoMudou} />
    </section>
  )
}
