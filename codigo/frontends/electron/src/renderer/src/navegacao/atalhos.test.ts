import { describe, expect, it } from 'vitest'
import { acaoDoAtalho, combinacao, decidirAtalho } from './atalhos'

const tecla = (
  key: string,
  mods: Partial<Record<'ctrlKey' | 'altKey' | 'shiftKey' | 'metaKey', boolean>> = {},
) => ({ key, ctrlKey: false, altKey: false, shiftKey: false, metaKey: false, ...mods })

describe('combinacao', () => {
  it('normaliza letras, ordem dos modificadores e teclas especiais', () => {
    expect(combinacao(tecla('k', { ctrlKey: true }))).toBe('Ctrl+K')
    expect(combinacao(tecla('K', { shiftKey: true, ctrlKey: true }))).toBe('Ctrl+Shift+K')
    expect(combinacao(tecla('ArrowUp'))).toBe('Up')
    expect(combinacao(tecla(' ', { ctrlKey: true }))).toBe('Ctrl+Space')
    expect(combinacao(tecla('F11'))).toBe('F11')
    expect(combinacao(tecla('PageDown'))).toBe('PgDown')
  })

  it('devolve null para tecla desconhecida', () => {
    expect(combinacao(tecla('Dead'))).toBeNull()
    expect(combinacao(tecla('F36'))).toBeNull()
  })
})

describe('acaoDoAtalho', () => {
  const atalhos = { paleta: 'Ctrl+K', buscar: 'Ctrl+F', jogos: 'Ctrl+2', inicio: 'Ctrl+1' }

  it('resolve paleta (Ctrl+K) e busca (Ctrl+F) em separado, e seções', () => {
    expect(acaoDoAtalho('Ctrl+K', atalhos)).toEqual({ tipo: 'paleta' })
    expect(acaoDoAtalho('Ctrl+F', atalhos)).toEqual({ tipo: 'busca' })
    expect(acaoDoAtalho('Ctrl+2', atalhos)).toEqual({ tipo: 'secao', chave: 'jogos' })
  })

  it('ignora combinação nula, desconhecida ou ação sem destino no shell', () => {
    expect(acaoDoAtalho(null, atalhos)).toBeNull()
    expect(acaoDoAtalho('Ctrl+9', atalhos)).toBeNull()
    expect(acaoDoAtalho('F11', { ...atalhos, tela_cheia: 'F11' })).toBeNull()
  })
})

describe('decidirAtalho', () => {
  const atalhos = { paleta: 'Ctrl+K', buscar: 'Ctrl+F', jogos: 'Ctrl+2' }

  it('fechado: paleta abre direto e seções navegam', () => {
    expect(decidirAtalho(false, 'Ctrl+K', atalhos, 'jogos')).toEqual({ tipo: 'paleta' })
    expect(decidirAtalho(false, 'Ctrl+2', atalhos, 'jogos')).toEqual({
      tipo: 'secao',
      chave: 'jogos',
    })
  })

  it('fechado: Ctrl+F foca a busca da seção; sem busca na seção, abre a paleta', () => {
    expect(decidirAtalho(false, 'Ctrl+F', atalhos, 'jogos')).toEqual({ tipo: 'focar-busca' })
    expect(decidirAtalho(false, 'Ctrl+F', atalhos, 'musicas')).toEqual({ tipo: 'focar-busca' })
    expect(decidirAtalho(false, 'Ctrl+F', atalhos, 'desejos')).toEqual({ tipo: 'focar-busca' })
    expect(decidirAtalho(false, 'Ctrl+F', atalhos, 'videos')).toEqual({ tipo: 'focar-busca' })
    expect(decidirAtalho(false, 'Ctrl+F', atalhos, 'inicio')).toEqual({ tipo: 'paleta' })
    expect(decidirAtalho(false, 'Ctrl+F', atalhos, 'integracoes')).toEqual({ tipo: 'paleta' })
    expect(decidirAtalho(false, 'Ctrl+F', atalhos)).toEqual({ tipo: 'paleta' })
  })

  it('aberta: só fecha (Ctrl+K/Ctrl+F) — seção não dispara', () => {
    expect(decidirAtalho(true, 'Ctrl+K', atalhos, 'jogos')).toEqual({ tipo: 'fechar' })
    expect(decidirAtalho(true, 'Ctrl+F', atalhos, 'jogos')).toEqual({ tipo: 'fechar' })
    expect(decidirAtalho(true, 'Ctrl+2', atalhos, 'jogos')).toBeNull()
    expect(decidirAtalho(true, null, atalhos, 'jogos')).toBeNull()
  })
})
