import { useEffect, useState } from 'preact/hooks'
import { avisoDeEvento, dispensarAviso, juntarAvisos, type AoAvisar, type Aviso } from './notificacoes'

/** Avisos do app (sino + tela Notificações): estado, atalhos de uso e o evento `aviso` da ponte. */
export function useAvisos() {
  const [avisos, setAvisos] = useState<Aviso[]>([])

  const juntar = (novos: Aviso[]) => setAvisos((atual) => juntarAvisos(atual, novos))
  /** Toast global das vistas/detalhe (id por texto evita duplicar o mesmo aviso). */
  const avisar: AoAvisar = (texto, tom = 'info') => juntar([{ id: texto, texto, tom }])
  const dispensar = (id: string) => setAvisos((lista) => dispensarAviso(lista, id))
  const limpar = () => setAvisos([])

  useEffect(() => {
    return window.tucoteca.assinar('aviso', (dados) => {
      const aviso = avisoDeEvento(dados)
      if (aviso !== null) setAvisos((atual) => juntarAvisos(atual, [aviso]))
    })
  }, [])

  return { avisos, setAvisos, juntar, avisar, dispensar, limpar }
}
