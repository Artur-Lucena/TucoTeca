import { describe, expect, it } from 'vitest'
import { acaoDoInstalador } from './atualizacao'

describe('acaoDoInstalador', () => {
  it('Windows abre o .exe e fecha o app', () => {
    const exe = 'C:\\Users\\x\\Documents\\TucoTeca\\dados\\atualizacoes\\TucoTeca-Setup-2.3.0-x64.exe'
    expect(acaoDoInstalador('C:\\Users\\x\\Documents\\TucoTeca', exe, 'win32')).toBe('abrir-e-fechar')
  })

  it('Mac abre a .dmg e Linux mostra o AppImage', () => {
    const home = '/Users/isa/Documents/TucoTeca'
    expect(acaoDoInstalador(home, `${home}/dados/atualizacoes/TucoTeca-2.3.0-mac-arm64.dmg`, 'darwin')).toBe('abrir')
    const linux = '/home/t/Documentos/TucoTeca'
    expect(acaoDoInstalador(linux, `${linux}/dados/atualizacoes/TucoTeca-2.3.0-linux-x64.AppImage`, 'linux')).toBe('mostrar')
  })

  it('recusa fora da pasta, nome estranho ou de outro sistema', () => {
    const home = 'C:\\TucoTeca'
    expect(acaoDoInstalador(home, 'C:\\TucoTeca\\dados\\TucoTeca-Setup-2.3.0-x64.exe', 'win32')).toBeNull()
    expect(acaoDoInstalador(home, 'C:\\TucoTeca\\dados\\atualizacoes\\..\\..\\virus.exe', 'win32')).toBeNull()
    expect(acaoDoInstalador(home, 'C:\\TucoTeca\\dados\\atualizacoes\\outro.exe', 'win32')).toBeNull()
    expect(acaoDoInstalador(home, 'C:\\TucoTeca\\dados\\atualizacoes\\TucoTeca-2.3.0-mac-x64.dmg', 'win32')).toBeNull()
    expect(acaoDoInstalador(home, '', 'win32')).toBeNull()
  })
})
