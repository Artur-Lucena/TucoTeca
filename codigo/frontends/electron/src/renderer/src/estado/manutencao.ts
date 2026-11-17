/** `jogo.diagnosticar` → partes do exe e da ROM (bib_nucleo/emuladores/lancamento.py). */
export interface Diagnostico {
  exe: { estado?: string; gravado?: string; atual?: string; nome?: string }
  rom: { estado?: string; candidatos?: string[] }
}

type AcaoReparo =
  | { tipo: 'usar-emulador-atual'; caminho: string }
  | { tipo: 'escolher-exe' }
  | { tipo: 'escolher-rom'; candidatos: string[] }

export interface LeituraDiagnostico {
  ok: boolean
  linhas: string[]
  acoes: AcaoReparo[]
}

/** Traduz o diagnóstico em frases e nas ações de reparo possíveis. */
export function lerDiagnostico(d: Diagnostico): LeituraDiagnostico {
  const linhas: string[] = []
  const acoes: AcaoReparo[] = []
  const exe = d.exe ?? {}
  switch (exe.estado) {
    case 'ok':
      linhas.push('Executável encontrado.')
      break
    case 'sem-exe':
      linhas.push('Nenhum executável cadastrado.')
      acoes.push({ tipo: 'escolher-exe' })
      break
    case 'trocou-emulador':
      linhas.push(`O emulador gravado sumiu; ${exe.nome ?? 'o emulador atual'} está instalado em outro lugar.`)
      if (exe.atual) acoes.push({ tipo: 'usar-emulador-atual', caminho: exe.atual })
      acoes.push({ tipo: 'escolher-exe' })
      break
    case 'ausente':
      linhas.push(`Executável não encontrado: ${exe.gravado ?? ''}`.trim())
      acoes.push({ tipo: 'escolher-exe' })
      break
    default:
      if (exe.estado) linhas.push(`Executável: ${exe.estado}.`)
  }
  const rom = d.rom ?? {}
  if (rom.estado === 'ok') linhas.push('ROM encontrada.')
  else if (rom.estado === 'rom-ausente') {
    const candidatos = Array.isArray(rom.candidatos) ? rom.candidatos.map(String) : []
    linhas.push(
      candidatos.length > 0
        ? `ROM não encontrada; ${candidatos.length} arquivo(s) parecido(s) achado(s).`
        : 'ROM não encontrada e nenhum arquivo parecido achado.',
    )
    acoes.push({ tipo: 'escolher-rom', candidatos })
  }
  return { ok: acoes.length === 0, linhas, acoes }
}
