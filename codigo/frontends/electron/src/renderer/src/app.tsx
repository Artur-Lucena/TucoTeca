import { useEffect, useState } from 'preact/hooks'

export function App() {
  const [mensagem, setMensagem] = useState('conectando ao núcleo…')

  useEffect(() => {
    void (async () => {
      try {
        const ping = await window.tucoteca.chamar<{ versao: string }>('nucleo.ping')
        const snapshot = await window.tucoteca.chamar<{ jogos: unknown[] }>('nucleo.snapshot')
        setMensagem(`conectado — núcleo ${ping.versao}, ${snapshot.jogos.length} jogos`)
        window.tucoteca.pronto({ jogos: snapshot.jogos.length })
      } catch (erro) {
        setMensagem(`erro: ${String(erro)}`)
      }
    })()
  }, [])

  return (
    <main class="andaime">
      <h1>TucoTeca</h1>
      <p>{mensagem}</p>
    </main>
  )
}
