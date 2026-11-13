import { render } from 'preact'
import { App } from './app'
import './estilo.css'

// Arrastar arquivos só tem efeito nas áreas que tratam o drop (ex.: Jogos);
// no resto da janela o padrão do navegador (abrir o arquivo) é cancelado.
for (const tipo of ['dragover', 'drop'] as const) {
  document.addEventListener(tipo, (evento) => evento.preventDefault())
}

const alvo = document.getElementById('app')
if (alvo) render(<App />, alvo)
