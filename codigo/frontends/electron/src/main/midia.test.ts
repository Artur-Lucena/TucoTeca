import { describe, expect, it } from 'vitest'
import { caminhoDaUrlMidia, faixaRange, raizesDaResposta, raizMidiaAceita, tipoDoArquivo } from './midia'

describe('faixaRange', () => {
  it('sem Range devolve o arquivo inteiro com 200', () => {
    expect(faixaRange(null, 1000)).toEqual({ status: 200, inicio: 0, fim: 999 })
    expect(faixaRange('', 1000)).toEqual({ status: 200, inicio: 0, fim: 999 })
  })

  it('bytes=0-99 vira 206 com {0, 99}', () => {
    expect(faixaRange('bytes=0-99', 1000)).toEqual({ status: 206, inicio: 0, fim: 99 })
  })

  it('bytes=100- vai até o fim do arquivo', () => {
    expect(faixaRange('bytes=100-', 1000)).toEqual({ status: 206, inicio: 100, fim: 999 })
  })

  it('fim além do tamanho é recortado', () => {
    expect(faixaRange('bytes=990-2000', 1000)).toEqual({ status: 206, inicio: 990, fim: 999 })
  })

  it('malformado ou fora do arquivo vira 416', () => {
    expect(faixaRange('itens=0-9', 1000).status).toBe(416)
    expect(faixaRange('bytes=abc', 1000).status).toBe(416)
    expect(faixaRange('bytes=1000-', 1000).status).toBe(416)
    expect(faixaRange('bytes=50-10', 1000).status).toBe(416)
    expect(faixaRange('bytes=0-99', 0).status).toBe(416)
    expect(faixaRange('bytes=0-1,3-4', 1000).status).toBe(416)
  })
})

describe('tipoDoArquivo', () => {
  it('reconhece áudio, vídeo e imagem por extensão', () => {
    expect(tipoDoArquivo('C:\\x\\a.wav')).toBe('audio/wav')
    expect(tipoDoArquivo('a.MP3')).toBe('audio/mpeg')
    expect(tipoDoArquivo('a.ogg')).toBe('audio/ogg')
    expect(tipoDoArquivo('a.flac')).toBe('audio/flac')
    expect(tipoDoArquivo('a.m4a')).toBe('audio/mp4')
    expect(tipoDoArquivo('a.mp4')).toBe('video/mp4')
    expect(tipoDoArquivo('a.webm')).toBe('video/webm')
    expect(tipoDoArquivo('a.png')).toBe('image/png')
    expect(tipoDoArquivo('a.jpg')).toBe('image/jpeg')
    expect(tipoDoArquivo('a.jpeg')).toBe('image/jpeg')
    expect(tipoDoArquivo('a.webp')).toBe('image/webp')
    expect(tipoDoArquivo('a.gif')).toBe('image/gif')
  })

  it('desconhecida cai em application/octet-stream', () => {
    expect(tipoDoArquivo('a.txt')).toBe('application/octet-stream')
    expect(tipoDoArquivo('sem-extensao')).toBe('application/octet-stream')
  })
})

describe('caminhoDaUrlMidia', () => {
  const home = 'C:\\Tucoteca'

  it('aceita caminho dentro da home', () => {
    const url = 'tucoteca-media://arquivo/C%3A%2FTucoteca%2Fdados%2Fmusicas%2Fa.wav'
    expect(caminhoDaUrlMidia(home, url, 'win32')).toBe('C:/Tucoteca/dados/musicas/a.wav')
  })

  it('recusa fora da home, esquema errado, host errado e URL quebrada', () => {
    expect(
      caminhoDaUrlMidia(home, 'tucoteca-media://arquivo/C%3A%2FOutra%2Fa.wav', 'win32'),
    ).toBeNull()
    expect(caminhoDaUrlMidia(home, 'https://exemplo.test/a.wav', 'win32')).toBeNull()
    expect(
      caminhoDaUrlMidia(home, 'tucoteca-media://outro/C%3A%2FTucoteca%2Fa.wav', 'win32'),
    ).toBeNull()
    expect(caminhoDaUrlMidia(home, 'tucoteca-media://arquivo/%E0%A4%A', 'win32')).toBeNull()
  })

  it('recusa subida com ..', () => {
    const url = 'tucoteca-media://arquivo/C%3A%2FTucoteca%2F..%2Fsegredo.wav'
    expect(caminhoDaUrlMidia(home, url, 'win32')).toBeNull()
  })

  it('funciona em posix', () => {
    expect(
      caminhoDaUrlMidia('/home/tuco/col', 'tucoteca-media://arquivo/home/tuco/col/musicas/a.wav', 'linux'),
    ).toBe('/home/tuco/col/musicas/a.wav')
    expect(
      caminhoDaUrlMidia('/home/tuco/col', 'tucoteca-media://arquivo/home/tuco/outro.wav', 'linux'),
    ).toBeNull()
  })
})

describe('pastas de Filmes e Séries', () => {
  const home = 'C:\\Tucoteca'
  const url = (caminho: string) => `tucoteca-media://arquivo/${encodeURIComponent(caminho)}`

  it('serve arquivo dentro de uma pasta escolhida', () => {
    expect(caminhoDaUrlMidia(home, url('D:/Filmes/Matrix.mkv'), 'win32', ['D:\\Filmes'])).toBe('D:/Filmes/Matrix.mkv')
  })

  it('recusa fora das pastas, subida com .. e pasta que é o disco inteiro', () => {
    expect(caminhoDaUrlMidia(home, url('D:/Outros/x.mkv'), 'win32', ['D:\\Filmes'])).toBeNull()
    expect(caminhoDaUrlMidia(home, url('D:/Filmes/../segredo.mkv'), 'win32', ['D:\\Filmes'])).toBeNull()
    expect(caminhoDaUrlMidia(home, url('D:/qualquer.mkv'), 'win32', ['D:\\'])).toBeNull()
    expect(caminhoDaUrlMidia(home, url('D:/Filmes/Matrix.mkv'), 'win32')).toBeNull()
  })

  it('raiz aceita: absoluta e não-raiz de disco', () => {
    expect(raizMidiaAceita('D:\\Filmes')).toBe(true)
    expect(raizMidiaAceita('D:\\')).toBe(false)
    expect(raizMidiaAceita('D:')).toBe(false)
    expect(raizMidiaAceita('relativa/pasta')).toBe(false)
    expect(raizMidiaAceita('')).toBe(false)
  })

  it('lê as raízes da resposta do núcleo e descarta as ruins', () => {
    expect(raizesDaResposta({ pastas: [{ caminho: 'D:\\Filmes' }, { caminho: 'C:\\' }, { x: 1 }, null] })).toEqual(['D:\\Filmes'])
    expect(raizesDaResposta(null)).toEqual([])
    expect(raizesDaResposta({ pastas: 'x' })).toEqual([])
  })
})
