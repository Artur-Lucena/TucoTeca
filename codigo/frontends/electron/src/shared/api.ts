/** Superfície que o preload expõe ao renderer (`window.tucoteca`). */
export interface ApiTucoteca {
  chamar<T = unknown>(metodo: string, params?: Record<string, unknown>): Promise<T>
  assinar(evento: string, ouvinte: (dados: unknown) => void): () => void
  pronto(dados: unknown): void
  imagemUrl(url: string): string
  mediaUrl(caminho: string): string
  escolherPasta(): Promise<string | null>
  reabrir(): Promise<void>
}
