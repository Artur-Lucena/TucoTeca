import { contextBridge, ipcRenderer, webFrame, webUtils } from 'electron'
import type { ApiTucoteca } from '../shared/api'
import { converterUrlMidia, mediaUrl } from '../shared/midia'

const api: ApiTucoteca = {
  chamar: (metodo, params) => ipcRenderer.invoke('ponte:chamar', metodo, params),
  assinar: (evento, ouvinte) => {
    const canal = `ponte:evento:${evento}`
    const escuta = (_cena: unknown, dados: unknown) => ouvinte(dados)
    ipcRenderer.on(canal, escuta)
    return () => {
      ipcRenderer.removeListener(canal, escuta)
    }
  },
  pronto: (dados) => ipcRenderer.send('tucoteca:pronto', dados),
  imagemUrl: (url) => converterUrlMidia(url),
  mediaUrl: (caminho) => mediaUrl(caminho),
  escolherPasta: () => ipcRenderer.invoke('dialogo:escolher-pasta'),
  escolherArquivo: (filtros) => ipcRenderer.invoke('dialogo:escolher-arquivo', filtros),
  // sandbox sem File.path: o caminho real do arquivo solto vem do webUtils
  caminhoDoArquivo: (arquivo) => webUtils.getPathForFile(arquivo),
  abrirUrl: (url) => ipcRenderer.invoke('app:abrir-url', url),
  abrirPasta: (caminho) => ipcRenderer.invoke('app:abrir-pasta', caminho),
  reabrir: () => ipcRenderer.invoke('ponte:reabrir'),
  instalarAtualizacao: (caminho) => ipcRenderer.invoke('app:instalar-atualizacao', caminho),
  // densidade × escala de texto (Aparência); limites para nunca sumir com a interface
  definirZoom: (fator) => webFrame.setZoomFactor(Math.min(2, Math.max(0.5, Number(fator) || 1))),
  plataforma: process.platform,
}

contextBridge.exposeInMainWorld('tucoteca', api)
