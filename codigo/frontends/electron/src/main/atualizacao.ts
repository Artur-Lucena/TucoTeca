import { caminhoPermitido, caminhosDe } from './caminhos'

/** O que fazer com o instalador baixado em `dados/atualizacoes/` (nunca outro arquivo). */
export type AcaoInstalador = 'abrir-e-fechar' | 'abrir' | 'mostrar'

const NOMES = /^TucoTeca-(Setup-[\d.]+-x64\.exe|[\d.]+-mac-(arm64|x64)\.dmg|[\d.]+-linux-x64\.AppImage)$/

/**
 * Windows: abre o instalador e fecha o app (o instalador precisa do app fechado).
 * Mac: abre a .dmg (o usuário arrasta para Aplicativos). Linux: mostra o AppImage
 * novo na pasta (já executável). `null` = fora da pasta, nome estranho ou de outro sistema.
 */
export function acaoDoInstalador(
  home: string,
  caminho: string,
  plataforma: NodeJS.Platform = process.platform,
): AcaoInstalador | null {
  const p = caminhosDe(plataforma)
  const texto = String(caminho ?? '').trim()
  if (!home || !texto) return null
  const alvo = p.resolve(texto)
  if (!caminhoPermitido(p.join(home, 'dados', 'atualizacoes'), alvo, { plataforma }) || !NOMES.test(p.basename(alvo))) {
    return null
  }
  if (plataforma === 'win32') return alvo.endsWith('.exe') ? 'abrir-e-fechar' : null
  if (plataforma === 'darwin') return alvo.endsWith('.dmg') ? 'abrir' : null
  return alvo.endsWith('.AppImage') ? 'mostrar' : null
}
