import { useEffect, useState } from 'preact/hooks'
import { type ComponentChildren } from 'preact'

interface Props {
  fabrica: () => Promise<any>
  props?: Record<string, unknown>
  fallback?: ComponentChildren
}

/** Carregamento sob demanda (code-splitting manual, sem preact/compat). */
export function Lazy({ fabrica, props = {}, fallback }: Props) {
  const [Componente, setComponente] = useState<any>(null)
  const [erro, setErro] = useState<string | null>(null)
  useEffect(() => {
    let vivo = true
    fabrica()
      .then((m) => {
        if (!vivo) return
        const comp = m?.default ?? m?.default?.default ?? Object.values(m ?? {})[0]
        setComponente(() => comp)
      })
      .catch((e) => {
        if (vivo) setErro(String(e))
      })
    return () => {
      vivo = false
    }
  }, [fabrica])
  if (erro !== null) return <div class="aviso">Erro ao carregar: {erro}</div>
  if (Componente === null) return <>{fallback ?? <div class="aviso">Carregando…</div>}</>
  return <Componente {...props} />
}
