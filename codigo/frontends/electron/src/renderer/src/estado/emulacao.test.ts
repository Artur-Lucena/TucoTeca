import { describe, expect, it } from 'vitest'
import { normalizarEmulacao, resumoEmulador, resumoTextura, validarCheat } from './emulacao'

describe('normalizarEmulacao', () => {
  it('campos ausentes viram vazios seguros', () => {
    const e = normalizarEmulacao({ id: 3, erro: 'Escolha um jogo 3DS' })
    expect(e).toMatchObject({ id: 3, tid: '', mods: [], cheats: [], presets: [], mods_off: false })
    expect(e.textura).toEqual({ instalado: false, ativo: false, arquivos: 0, mb: 0 })
  })

  it('preserva listas e booleanos estritos', () => {
    const e = normalizarEmulacao({
      tid: '0004000000055D00',
      mods: [{ nome: 'HD', ativo: true }, { nome: 'Fan', ativo: 'sim' }],
      cheats: [{ nome: 'Vida', ativo: false, linhas: 2 }],
      presets: ['rapido'],
    })
    expect(e.mods).toEqual([{ nome: 'HD', ativo: true }, { nome: 'Fan', ativo: false }])
    expect(e.cheats[0]).toEqual({ nome: 'Vida', ativo: false, linhas: 2 })
    expect(e.presets).toEqual(['rapido'])
  })
})

describe('validarCheat', () => {
  it('aceita pares hex e comentários', () => {
    expect(validarCheat('Vida', '*infinita\n00112233 44556677\n\nDD000000 00000204')).toBeNull()
  })

  it('recusa nome vazio, com colchetes e código inválido', () => {
    expect(validarCheat('  ', '00112233 44556677')).toMatch(/nome/)
    expect(validarCheat('[Vida]', '00112233 44556677')).toMatch(/colchetes/)
    expect(validarCheat('Vida', '*só comentário')).toMatch(/Cole/)
    expect(validarCheat('Vida', '0011 2233')).toMatch(/Linha inválida/)
  })
})

describe('resumos', () => {
  it('textura instalada, ativa e sem pacote', () => {
    expect(resumoTextura({ instalado: false, ativo: false, arquivos: 0 })).toMatch(/Nenhum/)
    expect(resumoTextura({ instalado: true, ativo: true, arquivos: 12, mb: 1.5 })).toBe('Ativas — 12 arquivo(s), 1,5 MB.')
  })

  it('emulador local × remoto', () => {
    const base = { chave: 'azahar', nome: 'Azahar', local: '', tag: '', atualizado: null }
    expect(resumoEmulador(base)).toBe('não instalado')
    expect(resumoEmulador({ ...base, local: '2124', tag: '2125', atualizado: false, tamanho_mb: 40 })).toBe(
      'instalado 2124 — disponível 2125 (40 MB)',
    )
    expect(resumoEmulador({ ...base, local: '2125', tag: '2125', atualizado: true })).toMatch(/última/)
  })
})
