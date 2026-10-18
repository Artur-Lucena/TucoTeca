import { render } from 'preact'
import { App } from './app'
import './estilo.css'

const alvo = document.getElementById('app')
if (alvo) render(<App />, alvo)
