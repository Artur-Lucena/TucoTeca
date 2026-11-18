/** O app roda no macOS? (vem do preload; nos testes não há `window.tucoteca`). */
export function ehMac(): boolean {
  return typeof window !== 'undefined' && window.tucoteca?.plataforma === 'darwin'
}
