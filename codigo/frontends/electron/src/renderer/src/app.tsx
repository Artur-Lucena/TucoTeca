import { useEffect, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../shared/protocolo'
import { BarraLateral } from './componentes/BarraLateral'
import type { Snapshot } from './derivacoes'
import { Inicio } from './vistas/Inicio'
import { Placeholder } from './vistas/Placeholder'

export function App() {
  const [modulos, setModulos] = useState<ModuloDTO[]>([])
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [secao, setSecao] = useState('inicio')

  useEffect(() => {
    void (async () => {
      try {
        const lista = await window.tucoteca.chamar<ModuloDTO[]>('modulos.listar')
        setModulos(lista)
        const dados = await window.tucoteca.chamar<Snapshot>('nucleo.snapshot')
        setSnapshot(dados)
        window.tucoteca.pronto({ jogos: dados.jogos?.length ?? 0 })
      } catch (falha) {
        setErro(String(falha))
      }
    })()
  }, [])

  if (erro) {
    return (
      <section class="painel erro">
        <h1>Não consegui falar com o núcleo</h1>
        <p>{erro}</p>
      </section>
    )
  }

  if (!snapshot) {
    return (
      <section class="painel">
        <h1>TucoTeca</h1>
        <p>Abrindo a coleção…</p>
      </section>
    )
  }

  const ativo = modulos.find((modulo) => modulo.chave === secao) ?? modulos[0]
  return (
    <main class="shell">
      <BarraLateral modulos={modulos} ativa={ativo?.chave ?? ''} aoTrocar={setSecao} />
      <section class="conteudo">
        {ativo === undefined || ativo.chave === 'inicio' ? (
          <Inicio snapshot={snapshot} />
        ) : (
          <Placeholder modulo={ativo} />
        )}
      </section>
    </main>
  )
}
