import { useEffect, useState } from 'preact/hooks'
import { type ComponentChildren, type ComponentType } from 'preact'

interface Props {
  /**
   * Carrega o módulo e devolve O componente, nomeado por quem chama — ex.:
   * `() => import('./vistas/Videos').then((m) => m.Videos)`. Adivinhar pela
   * "primeira" exportação falha: a ordem do namespace é alfabética (em Vídeos,
   * `REPRODUTORES` vinha antes de `Videos`).
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- cada vista tem as suas props
  fabrica: () => Promise<ComponentType<any>>
  props?: Record<string, unknown>
  fallback?: ComponentChildren
}

/**
 * Carregamento sob demanda (code-splitting manual, sem preact/compat).
 * Use com `key` por seção: assim a troca de seção remonta o Lazy e nunca
 * desenha o componente anterior com as props da seção nova.
 */
export function Lazy({ fabrica, props = {}, fallback }: Props) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [Componente, setComponente] = useState<ComponentType<any> | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  useEffect(() => {
    let vivo = true
    fabrica()
      .then((comp) => {
        if (!vivo) return
        if (typeof comp !== 'function') throw new Error('o módulo não exporta o componente pedido')
        setComponente(() => comp)
      })
      .catch((e) => {
        if (vivo) setErro(String(e))
      })
    return () => {
      vivo = false
    }
    // carrega uma vez por montagem: a `fabrica` é inline e muda a cada render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  if (erro !== null) return <div class="aviso">Erro ao carregar: {erro}</div>
  if (Componente === null) return <>{fallback ?? <div class="aviso">Carregando…</div>}</>
  return <Componente {...props} />
}
