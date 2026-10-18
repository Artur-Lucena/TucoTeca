import type { SistemaResumo } from '../derivacoes'

export interface Aviso {
  id: string
  texto: string
  tom: 'info' | 'atencao'
}

const LIMITE = 50

/** Avisos derivados do resumo do sistema (snapshot): só o que o usuário precisa saber. */
export function avisosDoResumo(sistema: SistemaResumo): Aviso[] {
  const avisos: Aviso[] = []

  const pendentes = Number(sistema.pendentes)
  if (Number.isFinite(pendentes) && pendentes > 0) {
    avisos.push({
      id: 'sessoes-pendentes',
      tom: 'atencao',
      texto:
        pendentes === 1
          ? '1 sessão pendente para registrar e fechar.'
          : `${pendentes} sessões pendentes para registrar e fechar.`,
    })
  }

  if (sistema.backup !== undefined) {
    const backup = String(sistema.backup).trim()
    if (backup === '' || backup === 'sem backup') {
      avisos.push({
        id: 'backup-ausente',
        tom: 'atencao',
        texto: 'Sem backup local da coleção — faça um backup na tela Sistema.',
      })
    } else {
      const idade = Number(sistema.backup_idade_dias)
      if (Number.isFinite(idade) && idade > 14) {
        avisos.push({ id: 'backup-velho', tom: 'atencao', texto: `Último backup há ${idade} dias.` })
      }
    }
  }

  const disco = Number(sistema.disco_livre_gb)
  if (Number.isFinite(disco) && disco < 5) {
    avisos.push({
      id: 'disco-baixo',
      tom: 'atencao',
      texto: `Pouco espaço em disco: ${disco} GB livres.`,
    })
  }

  return avisos
}

/** Junta avisos novos com os atuais: dedup por id, mais novos primeiro, teto de 50. */
export function juntarAvisos(atual: Aviso[], novos: Aviso[]): Aviso[] {
  const vistos = new Set<string>()
  const resultado: Aviso[] = []
  for (const aviso of [...novos, ...atual]) {
    if (vistos.has(aviso.id)) continue
    vistos.add(aviso.id)
    resultado.push(aviso)
  }
  return resultado.slice(0, LIMITE)
}

export function dispensarAviso(atual: Aviso[], id: string): Aviso[] {
  return atual.filter((aviso) => aviso.id !== id)
}
