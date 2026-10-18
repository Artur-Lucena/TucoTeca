import { contextBridge, ipcRenderer } from 'electron'
import type { ApiTucoteca } from '../shared/api'
import { converterUrlMidia } from '../shared/midia'

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
  reabrir: () => ipcRenderer.invoke('ponte:reabrir'),
}

contextBridge.exposeInMainWorld('tucoteca', api)
