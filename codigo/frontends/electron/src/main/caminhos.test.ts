import { describe, expect, it } from 'vitest'
import { caminhoPermitido } from './caminhos'

describe('caminhoPermitido', () => {
  it('aceita arquivo dentro da coleção (Windows, sem diferenciar caixa)', () => {
    expect(caminhoPermitido('C:\\Hub', 'c:\\hub\\dados\\capas\\a.png', { plataforma: 'win32' })).toBe(true)
  })

  it('bloqueia vizinho que só compartilha o prefixo', () => {
    expect(caminhoPermitido('C:\\hub', 'C:\\hub2\\dados\\a.png', { plataforma: 'win32' })).toBe(false)
  })

  it('bloqueia subida com ..', () => {
    expect(caminhoPermitido('C:\\hub', 'C:\\hub\\..\\fora.png', { plataforma: 'win32' })).toBe(false)
  })

  it('bloqueia outro volume', () => {
    expect(caminhoPermitido('C:\\hub', 'D:\\hub\\a.png', { plataforma: 'win32' })).toBe(false)
  })

  it('posix: dentro ok, fora bloqueia', () => {
    expect(caminhoPermitido('/home/tuco/hub', '/home/tuco/hub/capas/a.png', { plataforma: 'linux' })).toBe(true)
    expect(caminhoPermitido('/home/tuco/hub', '/home/tuco/outra/a.png', { plataforma: 'linux' })).toBe(false)
  })

  it('vazio bloqueia', () => {
    expect(caminhoPermitido('', 'C:\\a.png')).toBe(false)
    expect(caminhoPermitido('C:\\hub', '')).toBe(false)
  })
})
