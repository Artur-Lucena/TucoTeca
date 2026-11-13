/** Filtro do seletor de arquivo: rótulo e extensões sem ponto (ex.: zip). */
export interface FiltroArquivo {
  nome: string
  extensoes: string[]
}

/** Superfície que o preload expõe ao renderer (`window.tucoteca`). */
export interface ApiTucoteca {
  chamar<T = unknown>(metodo: string, params?: Record<string, unknown>): Promise<T>
  assinar(evento: string, ouvinte: (dados: unknown) => void): () => void
  pronto(dados: unknown): void
  imagemUrl(url: string): string
  mediaUrl(caminho: string): string
  escolherPasta(): Promise<string | null>
  escolherArquivo(filtros?: FiltroArquivo[]): Promise<string | null>
  abrirUrl(url: string): Promise<void>
  abrirPasta(caminho: string): Promise<void>
  reabrir(): Promise<void>
}
