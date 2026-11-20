import { useEffect, useState } from 'preact/hooks'
import {
  agoraIso,
  avisoDeEvento,
  dispensarAviso,
  juntarAvisos,
  persistiveis,
  type AoAvisar,
  type Aviso,
} from './notificacoes'

/** Grava no histórico do núcleo; sem ponte o aviso só vive nesta sessão. */
function gravar(metodo: string, params?: Record<string, unknown>): void {
  void window.tucoteca.chamar(metodo, params).catch(() => undefined)
}

/**
 * Avisos do app (sino + tela Notificações). O histórico fica no núcleo
 * (`avisos.*`): abre com o que já havia e grava o que chega; os derivados do
 * resumo (backup, disco…) são recalculados e não vão para o disco.
 */
export function useAvisos() {
  const [avisos, setAvisos] = useState<Aviso[]>([])

  const juntar = (novos: Aviso[]) => {
    const datados = novos.map((aviso) => (aviso.em ? aviso : { ...aviso, em: agoraIso() }))
    setAvisos((atual) => juntarAvisos(atual, datados))
    const guardar = persistiveis(datados)
    if (guardar.length > 0) gravar('avisos.registrar', { avisos: guardar })
  }
  /** Toast global das vistas/detalhe (id por texto evita duplicar o mesmo aviso). */
  const avisar: AoAvisar = (texto, tom = 'info') => juntar([{ id: texto, texto, tom }])
  const dispensar = (id: string) => {
    setAvisos((lista) => dispensarAviso(lista, id))
    gravar('avisos.dispensar', { id })
  }
  const limpar = () => {
    setAvisos([])
    gravar('avisos.limpar')
  }

  useEffect(() => {
    void window.tucoteca
      .chamar<Aviso[]>('avisos.listar')
      .then((salvos) => setAvisos((atual) => juntarAvisos(Array.isArray(salvos) ? salvos : [], atual)))
      .catch(() => undefined) // histórico ilegível: começa vazio
    return window.tucoteca.assinar('aviso', (dados) => {
      const aviso = avisoDeEvento(dados)
      if (aviso !== null) juntar([aviso])
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- juntar só usa o setter
  }, [])

  return { avisos, setAvisos, juntar, avisar, dispensar, limpar }
}
