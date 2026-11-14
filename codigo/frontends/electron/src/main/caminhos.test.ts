import { describe, expect, it } from 'vitest'
import { join, resolve } from 'node:path'
import { caminhoPermitido, resolverRaizHome } from './caminhos'

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

describe('resolverRaizHome', () => {
  // caminhos montados com join: o teste vale em Windows e em POSIX
  const r0 = resolve('/raiz-teste')
  const base = {
    appPath: join(r0, 'repo', 'codigo', 'frontends', 'electron'),
    resourcesPath: join(r0, 'Apps', 'TucoTeca', 'resources'),
    documentos: join(r0, 'Users', 'x', 'Documents'),
  }

  it('checkout: raiz é o repositório e a coleção fica nele', () => {
    const r = resolverRaizHome({ ...base, empacotado: false, env: {} })
    expect(r.raiz).toBe(join(r0, 'repo'))
    expect(r.home).toBe(join(r0, 'repo'))
  })

  it('instalado: núcleo em resources/tucoteca e coleção em Documentos/TucoTeca', () => {
    const r = resolverRaizHome({ ...base, empacotado: true, env: {} })
    expect(r.raiz).toBe(join(r0, 'Apps', 'TucoTeca', 'resources', 'tucoteca'))
    expect(r.home).toBe(join(r0, 'Users', 'x', 'Documents', 'TucoTeca'))
  })

  it('variáveis de ambiente têm prioridade (vazias são ignoradas)', () => {
    const r = resolverRaizHome({
      ...base,
      empacotado: true,
      env: { TUCOTECA_RAIZ: join(r0, 'fontes'), BIBLIOTECA_HOME: join(r0, 'colecao') },
    })
    expect(r).toEqual({ raiz: join(r0, 'fontes'), home: join(r0, 'colecao') })
    const vazio = resolverRaizHome({ ...base, empacotado: true, env: { BIBLIOTECA_HOME: '  ' } })
    expect(vazio.home).toBe(join(r0, 'Users', 'x', 'Documents', 'TucoTeca'))
  })
})
