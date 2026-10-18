import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('tucoteca', {
  versao: 'f0',
})
