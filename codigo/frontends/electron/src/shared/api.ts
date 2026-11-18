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
  /** Caminho no disco de um arquivo/pasta solto na janela ('' se não houver). */
  caminhoDoArquivo(arquivo: File): string
  abrirUrl(url: string): Promise<void>
  abrirPasta(caminho: string): Promise<void>
  reabrir(): Promise<void>
  /** Zoom da janela (0,5–2), usado pela densidade e escala de texto. */
  definirZoom(fator: number): void
  /** `process.platform` do app (o renderer sandboxed não tem `process`). */
  plataforma: string
}
