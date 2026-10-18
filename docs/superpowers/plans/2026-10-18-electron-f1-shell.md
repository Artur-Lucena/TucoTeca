# TucoTeca Electron — F1 (shell completo) Implementation Plan

> **Para agentes executores:** SUB-SKILL OBRIGATÓRIA: use `superpowers:executing-plans` para
> implementar este plano tarefa a tarefa (ou `superpowers:subagent-driven-development` para
> paralelizar). Passos usam checkboxes (`- [ ]`).

**Goal:** fechar o shell do desktop Electron em 1.2.0: paleta Ctrl+K com busca real, atalhos por
seção, notificações locais, chip de perfil, navegação por gamepad e reabertura da ponte sem
travar a UI.

**Architecture:** mantém a F0 — renderer Preact fala só por IPC; o main fala com `ponte.py` por
NDJSON. A F1 adiciona: três métodos na ponte (`nucleo.buscar`, `preferencias.ler`,
`preferencias.trocar_perfil`); lógica pura nova no renderer (reducers de paleta/notificações/
conexão, leitor de gamepad, atalhos) coberta por vitest; reconexão da ponte no main com
`ClientePonte` testável por injeção de spawn; menu de aplicação por roles do Electron.

**Tech Stack:** Python stdlib (`servicos_ui`, `bib_nucleo`), electron-vite + TypeScript + Preact
+ @preact/signals, vitest, Electron 44.

**Spec:** `docs/DESKTOP_ELECTRON.md` (§"O que a F0 entrega (e o que ainda não)", lista da F1) e
`docs/superpowers/plans/2026-10-18-electron-f0-fundacao.md` (§"Pendências conhecidas"), repo
TucoTeca. Ledger das tarefas em `.superpowers/sdd/2026-10-18-electron-f1-shell/progress.md`
(segue o fluxo do `executing-plans` usado na F0: `task-start`/`task-done` com o mesmo base por
tarefa).

## Global Constraints

- Commits em PT sem acentos no estilo do repo (`area: descricao`), staging por caminhos
  explícitos; sem push/tag/release.
- Núcleo Python stdlib; nenhuma dependência nova de runtime no Python. TS: sem dependências novas
  de npm (Preact/signals já instalados).
- A ponte não abre porta TCP; envelope NDJSON da F0 inalterado
  (`{"id","metodo","params"}` → `{"id","ok","resultado"|"erro"}`; evento sem `id`).
- Provas só com `BIBLIOTECA_HOME`/`TUCOTECA_USERDATA` temporários sob `.provas/electron/…`;
  nunca a coleção real. Suíte: `py -3.14 -B codigo/ferramentas/testes/executar.py [--modulo test_x]`.
- Lint: `.provas/venv-ruff/Scripts/ruff.exe check codigo conftest.py`; `git diff --check`.
- Typecheck = `npm --prefix codigo/frontends/electron run typecheck`; testes web =
  `npm --prefix codigo/frontends/electron run test`; build = `… run build`.
- `VERSION`/`README.md`/`CHANGELOG.md`: só a linha do CHANGELOG "Não lançado" nesta fatia; 1.2.0
  só na F6.
- TDD em tudo: teste falhando (RED) antes da implementação; commits pequenos por tarefa.
- Não reintroduzir tkinter nem tocar TUI/Qt nesta fatia.

## Review Focus

1. **Busca com termo vazio/só espaços/símbolos** deve mostrar o convite ("digite para buscar"), não listar tudo nem quebrar; a resposta do backend com termo já obsoleto NÃO pode sobrescrever a lista atual (resposta fora de ordem descartada — teste no reducer da paleta).
2. **Ponte cai com chamadas pendentes**: cada chamada deve rejeitar com erro claro, o banner "núcleo caiu" aparece, e só o botão Reconectar reabre; item de menu Recarregar não pode deixar processos Python órfãos (teste de `ClientePonte` com processo fake + checklist manual).
3. **Atalhos digitados com a paleta aberta ou em campos de texto** não podem navegar de seção por acidente (Ctrl+1..8 tratados só com a paleta fechada; Escape fecha; teste de `acaoDoAtalho` + regra no App).
4. **Gamepad com direcional+botão simultâneos ou hotplug** não pode disparar navegação sozinha: só o direcional repete; botões disparam uma vez; todo pad recém-ligado exige neutro (testes do `LeitorControle`).
5. **Perfil trocado com o app aberto** (chip) deve refletir na hora e persistir no JSON; nome inválido é recusado sem quebrar a UI (testes Python do serviço + renderer usa `preferencias.ler` de novo).

## Estrutura de arquivos (decidida)

```text
codigo/frontends/servicos_ui/mix_nucleo.py     + buscar / preferencias / trocar_perfil
codigo/frontends/ponte.py                      + nucleo.buscar / preferencias.ler / preferencias.trocar_perfil
codigo/ferramentas/testes/test_ponte.py        + casos novos (fake + home temporário)
codigo/frontends/electron/src/main/ponte.ts    injeta spawn (deps) para testes com processo fake
codigo/frontends/electron/src/main/ponte.test.ts  + queda/rejeição/reabertura com processo fake
codigo/frontends/electron/src/main/menu.ts     novo: template de menu por roles
codigo/frontends/electron/src/main/index.ts    reconexão, menu, forward de eventos novos
codigo/frontends/electron/src/shared/api.ts    + reabrir(): Promise<void>
codigo/frontends/electron/src/preload/index.ts + reabrir via ipcRenderer.invoke('ponte:reabrir')
codigo/frontends/electron/src/renderer/src/
  atalhos.ts + atalhos.test.ts                 normaliza combinação e resolve ação
  controle.ts + controle.test.ts               leitor de gamepad (repete só direcional)
  estado/paleta.ts + estado/paleta.test.ts     reducer da paleta (resposta obsoleta ignorada)
  estado/notificacoes.ts + estado/notificacoes.test.ts
  estado/conexao.ts + estado/conexao.test.ts
  componentes/Paleta.tsx                       overlay Ctrl+K
  componentes/Avisos.tsx                       sino + painel
  componentes/AvisoPonte.tsx                   banner de queda + reconectar
  app.tsx                                      wire: atalhos, paleta, avisos, perfil, controle
  estilo.css                                   estilos novos
docs/DESKTOP_ELECTRON.md / CHANGELOG.md        atualizados na Task 6
```

---

### Task 1: Ponte — busca e preferências

**Files:**
- Modify: `codigo/frontends/servicos_ui/mix_nucleo.py` (novos métodos antes do `__all__`)
- Modify: `codigo/frontends/ponte.py` (três handlers + entradas no `METODOS`)
- Test: `codigo/ferramentas/testes/test_ponte.py` (ao fim do arquivo)

**Interfaces:**
- Consumes: `busca_global(jogos, musicas, desejos, downloads, termo, limite=12)` de
  `servicos_ui.sistema` (DTO `{tipo,id,titulo,sub,capa_url}`); `ServicoBiblioteca.snapshot()`
  (F0); `bib_nucleo.preferencias_pessoais`: `PERFIS == ("Tuco","Isa")`, `ler_preferencias()`
  (dict com `ativo`/`perfis`/`atalhos`), `trocar_perfil(nome)` (ValueError se fora de PERFIS).
- Produces (usado pelas Tasks 2, 3 e 5):
  - `ServicoBiblioteca.buscar(termo: str, limite: int = 12) -> list[dict]`
  - `ServicoBiblioteca.preferencias() -> {"ativo": str, "perfis": list[str], "atalhos": dict[str,str]}`
  - `ServicoBiblioteca.trocar_perfil(nome: str) -> dict` (mesmo shape de `preferencias()`)
  - Ponte: `nucleo.buscar` (params `{termo, limite?}` → lista), `preferencias.ler` (→ dict),
    `preferencias.trocar_perfil` (params `{nome}` → dict; nome inválido → `ok:false`).

- [ ] **Step 1: Escrever os testes que falham** (append em `test_ponte.py`):

```python
def teste_buscar_despacha_para_o_servico():
    class ComBusca(ServicoFalso):
        def buscar(self, termo, limite=12):
            return [{"tipo": "jogo", "id": 1, "titulo": f"eco:{termo}", "limite": limite}]

    ponte = Ponte(ComBusca())
    r = _chamar(ponte, {"id": 12, "metodo": "nucleo.buscar",
                        "params": {"termo": "zelda", "limite": 5}})
    afirmar(r["ok"] is True, r)
    afirmar(r["resultado"] == [{"tipo": "jogo", "id": 1, "titulo": "eco:zelda",
                                "limite": 5}], r)


def teste_buscar_real_acha_jogo_sem_acento():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-busca-"))
    db = tmp / "hub.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "Pokémon X", "executable_path": ""})
    finally:
        con.close()
    ponte = Ponte(ServicoBiblioteca(db))
    r = _chamar(ponte, {"id": 13, "metodo": "nucleo.buscar", "params": {"termo": "pokemon"}})
    afirmar(r["ok"] is True, r)
    afirmar([i["titulo"] for i in r["resultado"]] == ["Pokémon X"], r)
    vazio = _chamar(ponte, {"id": 14, "metodo": "nucleo.buscar", "params": {"termo": "  "}})
    afirmar(vazio["resultado"] == [], vazio)


def teste_preferencias_ler_e_trocar():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-prefs-"))
    servico = ServicoBiblioteca(tmp / "hub.db")
    inicial = servico.preferencias()
    afirmar(inicial["ativo"] == "Tuco" and list(inicial["perfis"]) == ["Tuco", "Isa"], inicial)
    afirmar(inicial["atalhos"]["paleta"] == "Ctrl+K", inicial["atalhos"])
    trocado = servico.trocar_perfil("Isa")
    afirmar(trocado["ativo"] == "Isa", trocado)
    afirmar(servico.preferencias()["ativo"] == "Isa", "troca não persistiu")


def teste_preferencias_via_ponte_e_nome_invalido():
    class ComPrefs(ServicoFalso):
        ativo = "Tuco"

        def preferencias(self):
            return {"ativo": self.ativo, "perfis": ["Tuco", "Isa"], "atalhos": {}}

        def trocar_perfil(self, nome):
            if nome not in ("Tuco", "Isa"):
                raise ValueError("Perfil precisa ser Tuco ou Isa.")
            type(self).ativo = nome
            return self.preferencias()

    ponte = Ponte(ComPrefs())
    afirmar(_chamar(ponte, {"id": 15, "metodo": "preferencias.ler"})["resultado"]["ativo"]
            == "Tuco", "ler")
    r = _chamar(ponte, {"id": 16, "metodo": "preferencias.trocar_perfil",
                        "params": {"nome": "Isa"}})
    afirmar(r["ok"] is True and r["resultado"]["ativo"] == "Isa", r)
    erro = _chamar(ponte, {"id": 17, "metodo": "preferencias.trocar_perfil",
                           "params": {"nome": "Ninguem"}})
    afirmar(erro["ok"] is False and "Tuco ou Isa" in erro["erro"], erro)
```

- [ ] **Step 2: Rodar e ver falhar** — `py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_ponte`; esperado: falhas por "método desconhecido"/AttributeError.

- [ ] **Step 3: Implementar os métodos em `mix_nucleo.py`** (antes de `__all__`):

```python
def buscar(self, termo, limite=12):
    snap = self.snapshot()
    return busca_global(snap["jogos"], snap["musicas"], snap["desejos"], [],
                        str(termo or ""), int(limite))

def preferencias(self):
    from bib_nucleo.preferencias_pessoais import PERFIS, ler_preferencias
    dados = ler_preferencias()
    return {"ativo": dados["ativo"], "perfis": list(PERFIS), "atalhos": dados["atalhos"]}

def trocar_perfil(self, nome):
    from bib_nucleo.preferencias_pessoais import trocar_perfil
    trocar_perfil(nome)
    return self.preferencias()
```

- [ ] **Step 4: Implementar os handlers em `ponte.py`** (junto dos existentes e no `METODOS`):

```python
def _buscar(servico, params):
    termo = params.get("termo", "")
    if not isinstance(termo, str):
        raise ValueError("termo deve ser texto")
    limite = params.get("limite", 12)
    if not isinstance(limite, int) or limite < 1 or limite > 50:
        raise ValueError("limite deve ser um inteiro entre 1 e 50")
    return servico.buscar(termo, limite)

def _preferencias(servico, params):
    return servico.preferencias()

def _trocar_perfil(servico, params):
    nome = params.get("nome", "")
    if not isinstance(nome, str):
        raise ValueError("nome deve ser texto")
    return servico.trocar_perfil(nome)
```

`METODOS` ganha `"nucleo.buscar": _buscar, "preferencias.ler": _preferencias,
"preferencias.trocar_perfil": _trocar_perfil`.

- [ ] **Step 5: Verdes + gates** — `--modulo test_ponte` (esperado 15/15);
  `ruff check codigo` limpo; `git diff --check`.

- [ ] **Step 6: Commit**

```bash
git add codigo/frontends/servicos_ui/mix_nucleo.py codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py
git commit -m "frontend: busca e preferencias na ponte (F1)"
```

---

### Task 2: Atalhos e paleta Ctrl+K

**Files:**
- Create: `codigo/frontends/electron/src/renderer/src/atalhos.ts` (+ `atalhos.test.ts`)
- Create: `codigo/frontends/electron/src/renderer/src/estado/paleta.ts` (+ `paleta.test.ts`)
- Create: `codigo/frontends/electron/src/renderer/src/componentes/Paleta.tsx`
- Modify: `codigo/frontends/electron/src/renderer/src/app.tsx`, `estilo.css`

**Interfaces:**
- Consumes: `nucleo.buscar` e `preferencias.ler` (Task 1); `window.tucoteca.chamar` (F0);
  `converterUrlMidia` (F0) para as capas da paleta.
- Produces (Tasks 3–5 usam): `combinacao(e) -> string | null`;
  `acaoDoAtalho(comb, atalhos) -> {tipo:'paleta'} | {tipo:'secao', chave} | null`;
  `decidirAtalho(paletaAberta, comb, atalhos) -> {tipo:'paleta'|'fechar'} | {tipo:'secao', chave} | null`
  (regra do Review Focus 3: com a paleta aberta, `Ctrl+K`/`Ctrl+F` fecham e atalhos de seção são
  ignorados); `reduzirPaleta`, `paletaInicial`, tipos `ItemBusca`/`EstadoPaleta`/`EventoPaleta`.

- [ ] **Step 1: Testes que falham** — `atalhos.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { acaoDoAtalho, combinacao, decidirAtalho } from './atalhos'

const tecla = (key: string, mods: Partial<Record<'ctrlKey' | 'altKey' | 'shiftKey' | 'metaKey', boolean>> = {}) =>
  ({ key, ctrlKey: false, altKey: false, shiftKey: false, metaKey: false, ...mods })

describe('combinacao', () => {
  it('normaliza letras, ordem dos modificadores e teclas especiais', () => {
    expect(combinacao(tecla('k', { ctrlKey: true }))).toBe('Ctrl+K')
    expect(combinacao(tecla('K', { shiftKey: true, ctrlKey: true }))).toBe('Ctrl+Shift+K')
    expect(combinacao(tecla('ArrowUp'))).toBe('Up')
    expect(combinacao(tecla(' ', { ctrlKey: true }))).toBe('Ctrl+Space')
    expect(combinacao(tecla('F11'))).toBe('F11')
    expect(combinacao(tecla('PageDown'))).toBe('PgDown')
  })

  it('devolve null para tecla desconhecida', () => {
    expect(combinacao(tecla('Dead'))).toBeNull()
    expect(combinacao(tecla('F36'))).toBeNull()
  })
})

describe('acaoDoAtalho', () => {
  const atalhos = { paleta: 'Ctrl+K', buscar: 'Ctrl+F', jogos: 'Ctrl+2', inicio: 'Ctrl+1' }

  it('resolve paleta (Ctrl+K e Ctrl+F) e seções', () => {
    expect(acaoDoAtalho('Ctrl+K', atalhos)).toEqual({ tipo: 'paleta' })
    expect(acaoDoAtalho('Ctrl+F', atalhos)).toEqual({ tipo: 'paleta' })
    expect(acaoDoAtalho('Ctrl+2', atalhos)).toEqual({ tipo: 'secao', chave: 'jogos' })
  })

  it('ignora combinação nula, desconhecida ou ação sem destino no shell', () => {
    expect(acaoDoAtalho(null, atalhos)).toBeNull()
    expect(acaoDoAtalho('Ctrl+9', atalhos)).toBeNull()
    expect(acaoDoAtalho('F11', { ...atalhos, tela_cheia: 'F11' })).toBeNull()
  })
})

describe('decidirAtalho', () => {
  const atalhos = { paleta: 'Ctrl+K', buscar: 'Ctrl+F', jogos: 'Ctrl+2' }

  it('fechado: paleta abre/toggle e seções navegam', () => {
    expect(decidirAtalho(false, 'Ctrl+K', atalhos)).toEqual({ tipo: 'paleta' })
    expect(decidirAtalho(false, 'Ctrl+2', atalhos)).toEqual({ tipo: 'secao', chave: 'jogos' })
  })

  it('aberta: só fecha (Ctrl+K/Ctrl+F/Esc) — seção não dispara', () => {
    expect(decidirAtalho(true, 'Ctrl+K', atalhos)).toEqual({ tipo: 'fechar' })
    expect(decidirAtalho(true, 'Ctrl+F', atalhos)).toEqual({ tipo: 'fechar' })
    expect(decidirAtalho(true, 'Ctrl+2', atalhos)).toBeNull()
    expect(decidirAtalho(true, null, atalhos)).toBeNull()
  })
})
```

teste da paleta — `paleta.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { paletaInicial, reduzirPaleta } from './paleta'

const abrir = (estado = paletaInicial) => reduzirPaleta(estado, { tipo: 'abrir' })

describe('reduzirPaleta', () => {
  it('abre limpa, alterna e fecha', () => {
    const aberta = abrir(reduzirPaleta(paletaInicial, { tipo: 'digitou', termo: 'z' }))
    expect(aberta.termo).toBe('')
    expect(reduzirPaleta(aberta, { tipo: 'alternar' }).aberta).toBe(false)
  })

  it('ignora resposta de termo obsoleto (resposta fora de ordem)', () => {
    const digitouZelda = reduzirPaleta(abrir(), { tipo: 'digitou', termo: 'zelda' })
    const esperada = reduzirPaleta(digitouZelda, { tipo: 'resultados', termo: 'zelda', itens: [{ tipo: 'jogo', id: 1, titulo: 'Zelda' }] })
    const obsoleta = reduzirPaleta(esperada, { tipo: 'resultados', termo: 'zel', itens: [{ tipo: 'jogo', id: 9, titulo: 'Zé' }] })
    expect(obsoleta.itens.map((i) => i.id)).toEqual([1])
  })

  it('navega com wrap-around e seleciona com clamp', () => {
    let estado = reduzirPaleta(abrir(), { tipo: 'resultados', termo: '', itens: [{ tipo: 'jogo', id: 1, titulo: 'A' }, { tipo: 'jogo', id: 2, titulo: 'B' }] })
    estado = reduzirPaleta(estado, { tipo: 'cima' })
    expect(estado.selecionado).toBe(1)
    estado = reduzirPaleta(estado, { tipo: 'baixo' })
    expect(estado.selecionado).toBe(0)
    expect(reduzirPaleta(estado, { tipo: 'selecionar', indice: 99 }).selecionado).toBe(0)
  })

  it('termo novo zera seleção e limpa itens; resultado vazio mantém paleta aberta', () => {
    let estado = reduzirPaleta(abrir(), { tipo: 'resultados', termo: 'a', itens: [{ tipo: 'jogo', id: 1, titulo: 'A' }] })
    estado = reduzirPaleta(estado, { tipo: 'digitou', termo: 'ab' })
    expect(estado.itens).toEqual([])
    expect(estado.selecionado).toBe(0)
    estado = reduzirPaleta(estado, { tipo: 'resultados', termo: 'ab', itens: [] })
    expect(estado.aberta).toBe(true)
  })
})
```

- [ ] **Step 2: Rodar e ver falhar** — `npm --prefix codigo/frontends/electron run test` (módulos não existem).

- [ ] **Step 3: Implementar `atalhos.ts`** — `combinacao` normaliza: `key` de 1 caractere vira maiúsculo; mapa `Arrow*→Up/Down/Left/Right`, `' '→Space`, `PageUp→PgUp`, `PageDown→PgDown`, demais nomes válidos do validador Python (Enter, Escape, Tab, Backspace, Delete, Home, End) e `F1..F35`; monta `Ctrl+Alt+Shift+Meta+Tecla` nessa ordem. `acaoDoAtalho` inverte `atalhos` (`paleta`/`buscar` → `{tipo:'paleta'}`; chave de seção → `{tipo:'secao'}`; qualquer outra ação, inclusive `tela_cheia`, → `null`). `decidirAtalho(paletaAberta, comb, atalhos)` aplica a regra de foco do Review Focus 3.

- [ ] **Step 4: Implementar `estado/paleta.ts`** — tipos e `reduzirPaleta` conforme os testes; `carregando: boolean` só de conveniência: `digitou` liga, `resultados` desliga; `resultados` com `evento.termo !== estado.termo` retorna o estado intacto; `baixo/cima` com lista vazia mantém `selecionado` em 0.

- [ ] **Step 5: Implementar `Paleta.tsx` + wiring no `app.tsx` + CSS**
  - `Paleta` recebe `{ estado, itens visíveis, aoSelecionar(item), aoFechar() }`; renderiza input
    auto-focus, lista com `imagemUrl(capa_url)` e `sub`; item ativo com destaque; rodapé com dica
    "Enter abre · Esc fecha". Termo vazio mostra "Digite para buscar na coleção" (Review Focus 1).
  - No `App`: `useEffect` de keydown global monta `combinacao` → `acaoDoAtalho` com os atalhos
    carregados uma vez de `preferencias.ler` (state `atalhos`); com a paleta aberta os atalhos de
    seção são ignorados (só `alternar`/`fechar`), conforme Review Focus 3. Digitação com debounce
    de 150 ms chama `nucleo.buscar({termo, limite: 12})` com o termo do request guardado no
    `EstadoPaleta` (a resposta obsoleta é descartada pelo reducer).
  - `aoSelecionar(item)`: mapeia `tipo→seção` (`jogo→jogos`, `musica→musicas`, `desejo→desejos`,
    `download→downloads`), troca a seção e fecha a paleta (abrir detalhe chega na F2 — anotar).
  - Atalhos de seção (`Ctrl+1..8`) trocam a seção ativa.

- [ ] **Step 6: Verdes** — `npm … run test` (esperado 40+ testes), `npm … run typecheck`, `build`.

- [ ] **Step 7: Prova visual** — selftest com home semeada + screenshot; conferir estado
  fechado sem regressão (a paleta é aberta por tecla; prova aberta fica no checklist manual da
  Task 6).

- [ ] **Step 8: Commit**

```bash
git add codigo/frontends/electron/src/renderer/src/atalhos.ts codigo/frontends/electron/src/renderer/src/atalhos.test.ts codigo/frontends/electron/src/renderer/src/estado/paleta.ts codigo/frontends/electron/src/renderer/src/estado/paleta.test.ts codigo/frontends/electron/src/renderer/src/componentes/Paleta.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: paleta de busca Ctrl+K com atalhos (F1)"
```

---

### Task 3: Notificações e chip de perfil

**Files:**
- Create: `codigo/frontends/electron/src/renderer/src/estado/notificacoes.ts` (+ `.test.ts`)
- Create: `codigo/frontends/electron/src/renderer/src/componentes/Avisos.tsx`
- Modify: `app.tsx`, `componentes/BarraLateral.tsx` (rodapé: sino + chip de perfil), `estilo.css`

**Interfaces:**
- Consumes: `SistemaResumo`/`Snapshot` de `derivacoes.ts` (F0); `preferencias.ler`/`trocar_perfil`
  (Task 1); `window.tucoteca.assinar('aviso', …)` (F0).
- Produces: `Aviso`, `avisosDoResumo(sistema)`, `juntarAvisos(lista, novos)`,
  `dispensarAviso(lista, id)`; `BarraLateral` ganha props `{ avisosPendentes: number,
  aoAbrirAvisos(), perfil: string, aoTrocarPerfil(nome) }`.

- [ ] **Step 1: Teste que falha** — `notificacoes.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { avisosDoResumo, dispensarAviso, juntarAvisos } from './notificacoes'

describe('avisosDoResumo', () => {
  it('avisa sessões pendentes com plural correto', () => {
    expect(avisosDoResumo({ pendentes: 1 }).map((a) => a.id)).toEqual(['sessoes-pendentes'])
    const dois = avisosDoResumo({ pendentes: 2 })
    expect(dois[0].texto).toContain('2 sessões pendentes')
    expect(dois[0].tom).toBe('atencao')
  })

  it('avisa backup ausente e backup velho (>14 dias), silencia quando ok', () => {
    expect(avisosDoResumo({ backup: 'sem backup' }).map((a) => a.id)).toEqual(['backup-ausente'])
    expect(avisosDoResumo({ backup: 'biblioteca-x.db', backup_idade_dias: 30 }).map((a) => a.id)).toEqual(['backup-velho'])
    expect(avisosDoResumo({ backup: 'biblioteca-x.db', backup_idade_dias: 3 })).toEqual([])
  })

  it('avisa disco baixo e ignora campos ausentes', () => {
    expect(avisosDoResumo({ disco_livre_gb: 2.5 }).map((a) => a.id)).toEqual(['disco-baixo'])
    expect(avisosDoResumo({})).toEqual([])
  })
})

describe('juntarAvisos / dispensarAviso', () => {
  it('deduplica por id mantendo o mais novo primeiro', () => {
    const atual = [{ id: 'a', texto: 'antigo', tom: 'info' as const }]
    const juntos = juntarAvisos(atual, [{ id: 'a', texto: 'novo', tom: 'info' }])
    expect(juntos).toEqual([{ id: 'a', texto: 'novo', tom: 'info' }])
  })

  it('dispensa por id e não quebra com id ausente', () => {
    const lista = [{ id: 'a', texto: 'x', tom: 'info' as const }]
    expect(dispensarAviso(lista, 'a')).toEqual([])
    expect(dispensarAviso(lista, 'z')).toEqual(lista)
  })
})
```

- [ ] **Step 2: RED** — `npm … run test`.

- [ ] **Step 3: Implementar `notificacoes.ts`** — regras do teste; `juntarAvisos` mantém teto de
  50 itens (descarta os mais antigos).

- [ ] **Step 4: Implementar `Avisos.tsx` + rodapé da `BarraLateral` + wiring**
  - `Avisos`: botão sino com contador; painel com lista + dispensar individual quando aberto.
  - Rodapé da sidebar: chip `Tuco`/`Isa` (clique alterna via `preferencias.trocar_perfil`) — Review
    Focus 5: recusa mantém o chip atual e vira aviso de erro.
  - No `App`: estado `avisos` inicializado com `avisosDoResumo(snapshot.sistema)` após o snapshot;
    `useEffect` com `assinar('aviso', dados => setAvisos(l => juntarAvisos(l, [normalizar(dados)])))`;
    troca de perfil gera aviso info `Perfil trocado para Isa`.

- [ ] **Step 5: Verdes** — `test` + `typecheck` + `build`; selftest com screenshot (chip e sino
  visíveis).

- [ ] **Step 6: Commit**

```bash
git add codigo/frontends/electron/src/renderer/src/estado/notificacoes.ts codigo/frontends/electron/src/renderer/src/estado/notificacoes.test.ts codigo/frontends/electron/src/renderer/src/componentes/Avisos.tsx codigo/frontends/electron/src/renderer/src/componentes/BarraLateral.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: notificacoes e perfil no shell (F1)"
```

---

### Task 4: Navegação por gamepad

**Files:**
- Create: `codigo/frontends/electron/src/renderer/src/controle.ts` (+ `controle.test.ts`)
- Modify: `app.tsx` (hook de polling), `estilo.css` (indicador discreto opcional)

**Interfaces:**
- Consumes: nada da ponte; `document.hasFocus()` e `navigator.getGamepads()` direto no hook.
- Produces: `EstadoPad {cima,baixo,a,b}`, `AcaoControle`, `LeitorControle` com
  `reiniciar(estado)`/`avaliar(estado, agoraMs)`.

- [ ] **Step 1: Teste que falha** — `controle.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { LeitorControle, type EstadoPad } from './controle'

const pad = (parcial: Partial<EstadoPad> = {}): EstadoPad =>
  ({ cima: false, baixo: false, a: false, b: false, ...parcial })
const solto = pad()

describe('LeitorControle', () => {
  it('dispara na pressão e só o direcional repete', () => {
    const leitor = new LeitorControle({ primeiroAtrasoMs: 350, repeticaoMs: 140 })
    leitor.reiniciar(solto)
    leitor.avaliar(solto, 0)
    expect(leitor.avaliar(pad({ cima: true }), 100)).toBe('cima')
    expect(leitor.avaliar(pad({ cima: true }), 300)).toBeNull()
    expect(leitor.avaliar(pad({ cima: true }), 450)).toBe('cima')
    expect(leitor.avaliar(pad({ cima: true }), 590)).toBe('cima')
    expect(leitor.avaliar(pad({ a: true }), 600)).toBe('ativar')
    expect(leitor.avaliar(pad({ a: true }), 900)).toBeNull()
  })

  it('rearma a repetição ao soltar e não dispara com direções juntas', () => {
    const leitor = new LeitorControle({ primeiroAtrasoMs: 350, repeticaoMs: 140 })
    leitor.reiniciar(solto)
    expect(leitor.avaliar(pad({ baixo: true }), 0)).toBe('baixo')
    leitor.avaliar(solto, 50)
    expect(leitor.avaliar(pad({ baixo: true }), 60)).toBe('baixo')
    expect(leitor.avaliar(pad({ cima: true, baixo: true }), 500)).toBeNull()
  })

  it('b vira voltar uma vez por pressão', () => {
    const leitor = new LeitorControle()
    leitor.reiniciar(solto)
    expect(leitor.avaliar(pad({ b: true }), 0)).toBe('voltar')
    expect(leitor.avaliar(pad({ b: true }), 100)).toBeNull()
    leitor.avaliar(solto, 120)
    expect(leitor.avaliar(pad({ b: true }), 140)).toBe('voltar')
  })

  it('pad recém-ligado exige neutro antes de qualquer ação (hotplug/foco)', () => {
    const leitor = new LeitorControle()
    leitor.reiniciar(pad({ cima: true }))
    expect(leitor.avaliar(pad({ cima: true }), 100)).toBeNull()
    expect(leitor.avaliar(solto, 200)).toBeNull()
    expect(leitor.avaliar(pad({ cima: true }), 300)).toBe('cima')
  })
})
```

- [ ] **Step 2: RED** — `npm … run test`.

- [ ] **Step 3: Implementar `controle.ts`** — classe com estado interno: `exigeNeutro`,
  `antes` (pad anterior), `direcao: 'cima'|'baixo'|null`, `proximaEm`. Ordem de avaliação:
  neutro obrigatório → direções (juntas: nenhuma ação e zera repetição) → repique por tempo →
  bordas de `a`/`b` (cada uma dispara no máximo uma vez por pressão; avaliadas só quando as
  direções não produziram ação no mesmo tick, o que torna `avaliar` determinístico para o teste
  do Step 1).

- [ ] **Step 4: Wiring no `app.tsx`** — hook `useControle(aoTrocarSecao, secaoAtiva)`: a cada
  120 ms, se `document.hasFocus()`, lê o primeiro pad conectado
  (`navigator.getGamepads().find(Boolean)`) e monta o `EstadoPad` (D-pad e eixo Y
  `axes[1] < -0.5 / > 0.5`; botões 0 = a, 1 = b); `reiniciar` na montagem, no
  `gamepadconnected` e no `window.focus`. Ações: cima/baixo navegam as seções na ordem do
  registry; `ativar` abre a paleta; `voltar` volta ao Início. Sem hardware não há prova física —
  anotar no relatório e no checklist manual.

- [ ] **Step 5: Verdes** — `test` + `typecheck` + `build`.

- [ ] **Step 6: Commit**

```bash
git add codigo/frontends/electron/src/renderer/src/controle.ts codigo/frontends/electron/src/renderer/src/controle.test.ts codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: navegacao por controle no shell (F1)"
```

---

### Task 5: Reabertura da ponte sem travar a UI

**Files:**
- Modify: `codigo/frontends/electron/src/main/ponte.ts` (injeção de spawn)
- Modify: `codigo/frontends/electron/src/main/index.ts` (conexão/reconexão; forward de eventos)
- Modify: `codigo/frontends/electron/src/shared/api.ts`, `src/preload/index.ts` (`reabrir`)
- Create: `codigo/frontends/electron/src/renderer/src/estado/conexao.ts` (+ `.test.ts`)
- Create: `codigo/frontends/electron/src/renderer/src/componentes/AvisoPonte.tsx`
- Test: `codigo/frontends/electron/src/main/ponte.test.ts` (casos novos), `conexao.test.ts`
- Modify: `app.tsx`, `estilo.css`

**Interfaces:**
- Consumes: `ClientePonte`/`Pendentes` (F0); `ipcMain.handle('ponte:chamar')` (F0).
- Produces: `ClientePonte` passa a aceitar segundo parâmetro
  `deps?: { criarProcesso?: FabricaProcesso }` com
  `type FabricaProcesso = (comando: string, args: string[], opcoes: object) => ChildProcess`
  (default: `spawn` do node; nos testes o fake entra com cast `as unknown as ChildProcess` porque
  só usamos stdin/stdout/stderr/on/once/kill); main expõe IPC `ponte:reabrir` (Promise) e evento
  `ponte-estado` (`'caiu' | 'reabrindo' | 'ok'`); preload `reabrir(): Promise<void>`; renderer
  `reduzirConexao` + banner.

- [ ] **Step 1: Testes que falham** — em `ponte.test.ts` (novos `describe`s com processo fake;
  o import existente do arquivo ganha `ClientePonte`):

```ts
import { EventEmitter } from 'node:events'
import type { ChildProcess } from 'node:child_process'
import { PassThrough } from 'node:stream'
import { ClientePonte } from './ponte'

class ProcessoFake extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  stdin = new PassThrough()  // o fake registra o que foi pedido e responde com `responder()`
  pid = 4242
  respondido: string[] = []
  saida = false
  constructor() {
    super()
    this.stdin.on('data', (pedaco: Buffer) => this.respondido.push(pedaco.toString('utf8')))
  }
  responder(objeto: unknown) { this.stdout.write(`${JSON.stringify(objeto)}\n`) }
  sair(codigo: number) { this.saida = true; this.emit('exit', codigo) }
  kill() { return true }
}

function clienteComFake() {
  const processo = new ProcessoFake()
  const cliente = new ClientePonte(
    { raiz: 'C:/raiz' },
    { criarProcesso: (() => processo) as unknown as () => ChildProcess },
  )
  cliente.iniciar()
  return { processo, cliente }
}

describe('ClientePonte — queda e rejeição', () => {
  it('rejeita chamadas pendentes e avisa quando o processo morre', async () => {
    const { processo, cliente } = clienteComFake()
    const encerrou: unknown[] = []
    cliente.aoEncerrar((info) => encerrou.push(info))
    const pendente = cliente.chamar('nucleo.ping')
    expect(processo.respondido[0]).toContain('"nucleo.ping"')
    processo.sair(1)
    await expect(pendente).rejects.toThrow('encerrou')
    expect(encerrou).toEqual([{ codigo: 1, erro: undefined }])
    await expect(cliente.chamar('nucleo.ping')).rejects.toThrow('não iniciada')
  })

  it('resposta fora de ordem resolve por id; id órfão é ignorado', async () => {
    const { processo, cliente } = clienteComFake()
    const primeira = cliente.chamar('a')
    const segunda = cliente.chamar('b')
    processo.responder({ id: 2, ok: true, resultado: 'B' })
    processo.responder({ id: 1, ok: true, resultado: 'A' })
    processo.responder({ id: 99, ok: true, resultado: 'órfã' })
    await expect(primeira).resolves.toBe('A')
    await expect(segunda).resolves.toBe('B')
  })
})
```

`conexao.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { reduzirConexao } from './conexao'

describe('reduzirConexao', () => {
  it('cai de qualquer estado, reabre só quando caiu e volta a ok', () => {
    expect(reduzirConexao('ok', { tipo: 'caiu' })).toBe('caiu')
    expect(reduzirConexao('caiu', { tipo: 'reabrindo' })).toBe('reabrindo')
    expect(reduzirConexao('ok', { tipo: 'reabrindo' })).toBe('ok')
    expect(reduzirConexao('reabrindo', { tipo: 'ok' })).toBe('ok')
    expect(reduzirConexao('caiu', { tipo: 'caiu' })).toBe('caiu')
  })
})
```

- [ ] **Step 2: RED** — `npm … run test`.

- [ ] **Step 3: `ClientePonte` com spawn injetável** — construtor aceita
  `deps.criarProcesso`; `iniciar()` usa `deps?.criarProcesso ?? spawn`; o resto do F0 permanece
  (buffer NDJSON, pendentes por id, timeout 30 s, `encerrar()` com taskkill). Ajustar tipos para
  aceitar `ChildProcess`-like (o fake não é um ChildProcess real — tipar a dependência como
  `(comando: string, args: string[], opcoes: object) => ProcessoFilhoMinimo`, com interface local
  mínima `{stdin, stdout, stderr, on, once, kill, pid}`).

- [ ] **Step 4: `conexao.ts`** — conforme teste.

- [ ] **Step 5: Main — conexão/reconexão + menu deixado para a Task 6**
  - Extrair `conectar(): Promise<void>`: cria `ClientePonte`, `aoEvento` (bloqueio → diálogo+
    exit 2 como na F0; demais eventos → `webContents.send('ponte:evento:…')`), `aoEncerrar` →
    `enviarEstado('caiu')`, `iniciar()`, `chamar('nucleo.ping')`.
  - `ipcMain.handle('ponte:chamar')` passa a usar a variável mutável `ponteAtual`; chamadas com a
    ponte morta rejeitam com "ponte encerrou" (Review Focus 2).
  - `ipcMain.handle('ponte:reabrir')`: single-flight; envia `ponte-estado: reabrindo`, chama
    `conectar()` de novo, envia `ok`; falha → mantém `caiu` e devolve erro claro.
  - `enviarEstado(estado)` manda `tucoteca:ponte-estado` para todas as janelas (preload expõe via
    `assinar('ponte-estado', …)` usando o canal existente `ponte:evento:ponte-estado`).
  - `window-all-closed` continua encerrando a ponte (sem órfãos: `encerrar()` com kill).

- [ ] **Step 6: Renderer — banner e reabertura**
  - `AvisoPonte`: quando `caiu`, faixa fixa no topo "O núcleo caiu — a coleção não está acessível.
    [Reconectar]"; enquanto `reabrindo`, botão desabilitado "Reconectando…".
  - `App`: estado `conexao` via `reduzirConexao`; `assinar('ponte-estado')` atualiza; sucesso da
    reabertura refaz `nucleo.snapshot` e substitui o snapshot (sem recarregar a página);
    `window.tucoteca.reabrir()` é chamado pelo botão.

- [ ] **Step 7: Verdes** — `test` (ponte fake + conexão), `typecheck`, `build`.

- [ ] **Step 8: Prova manual de queda** (checklist da Task 6 roda junto): em `npm run dev` com
  home de prova, `taskkill /PID <pid-do-python> /T /F` → banner aparece; Reconectar → volta;
  sair do app não deixa processo Python (conferir `Get-CimInstance Win32_Process`).

- [ ] **Step 9: Commit**

```bash
git add codigo/frontends/electron/src/main/ponte.ts codigo/frontends/electron/src/main/ponte.test.ts codigo/frontends/electron/src/main/index.ts codigo/frontends/electron/src/shared/api.ts codigo/frontends/electron/src/preload/index.ts codigo/frontends/electron/src/renderer/src/estado/conexao.ts codigo/frontends/electron/src/renderer/src/estado/conexao.test.ts codigo/frontends/electron/src/renderer/src/componentes/AvisoPonte.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: reabertura da ponte sem travar a UI (F1)"
```

---

### Task 6: Menu do app, provas finais e docs

**Files:**
- Create: `codigo/frontends/electron/src/main/menu.ts`; Modify: `src/main/index.ts`
- Modify: `docs/DESKTOP_ELECTRON.md`, `CHANGELOG.md`
- Test: rodada completa (comandos abaixo)

**Interfaces:**
- Consumes: `app`, `Menu`, `dialog`, `shell` do Electron; `lerVersao()` — ler `VERSION` do repo
  para o "Sobre" (via `process.env.TUCOTECA_RAIZ`/`RAIZ` já existente no main).
- Produces: `montarMenu(opcoes: { raiz: string; aoAbrirSobre: () => void })` devolvendo
  `MenuItemConstructorOptions[]` (função pura de template, testável por leitura).

- [ ] **Step 1: Implementar `menu.ts` + `setApplicationMenu`**
  - Menu: **TucoTeca** (Sobre…, Separador, Sair role `quit`); **Exibir** (Recarregar `CmdOrCtrl+R`
    role `reload`, Ferramentas de desenvolvedor `F12` com `toggleDevTools`, Separador, zoom
    in/out/reset, Tela cheia `F11` role `togglefullscreen`); **Ajuda** (Documentação →
    `shell.openExternal` para a URL do repo NÃO: abrir `docs/DESKTOP_ELECTRON.md` local com
    `shell.openPath`, Aviso legal → `docs/LEGAL.md`).
  - "Sobre": `dialog.showMessageBox` com versão (`VERSION`), home da coleção e versão do Electron.
  - `autoHideMenuBar` continua true (menu acessível com Alt; aceleradores funcionam sempre).

- [ ] **Step 2: Rodada completa** (`git diff --check` antes):
  - `py -3.14 -B codigo/ferramentas/testes/executar.py` — esperado 526+/526 (novos casos da Task 1).
  - `.provas/venv-ruff/Scripts/ruff.exe check codigo conftest.py`.
  - `npm --prefix codigo/frontends/electron run test/typecheck/build` — esperado 55+ testes.
  - Selftest com home semeada: `[ok] selftest Electron: 3 jogos …` rc 0 + screenshot revisado
    (chip de perfil e sino visíveis); home vazia sem erro.

- [ ] **Step 3: Checklist manual (documentar resultados no relatório)**
  - `npm run dev` com `BIBLIOTECA_HOME` de prova: Ctrl+K abre/`Esc` fecha; digitar "pokemon"
    acha o jogo semeado; Enter navega; Ctrl+1..8 trocam seção; chip alterna TukO/Isa e persiste
    (`preferencias-pessoais.json` no home de prova); Ctrl+R recarrega sem processo Python órfão;
    matar o Python → banner → Reconectar volta; `Alt` mostra o menu; F11 tela cheia.
  - Gamepad: sem hardware — registrar como não provado fisicamente.

- [ ] **Step 4: Docs** — `docs/DESKTOP_ELECTRON.md`: novos métodos da ponte na tabela, atalhos,
  gamepad (API do Chromium; limites), reconexão e menu; changelog "Não lançado" ganha a fatia F1.

- [ ] **Step 5: Commit**

```bash
git add codigo/frontends/electron/src/main/menu.ts codigo/frontends/electron/src/main/index.ts docs/DESKTOP_ELECTRON.md CHANGELOG.md
git commit -m "electron: menu, provas e docs da F1"
```

---

## Pendências herdadas (F2+)

- F2: telas restantes com a tabela de paridade do `docs/DESKTOP_QT.md` como checklist; jobs com
  progresso/cancelamento na ponte (eventos); detalhe do jogo aberto a partir da paleta;
  perfis com favoritos/filtros persistentes por perfil.
- F3: manifestos de módulos, permissões/consentimento, modo seguro, exemplo de terceiro.
- F4: electron-builder/NSIS, sidecar Python no pacote, aposentar ZIP portátil.
- F5: aposentar QML/`qt_bridge`/PySide6/builders Windows antigos; TUI permanece.
- F6: `VERSION`/`CHANGELOG` → 1.2.0 e commit final (sem push/tag sem pedido).

## Riscos e limitações honestas

- Gamepad provado só por unidade (sem controle físico na máquina) — mesmo limite já registrado no
  desktop Qt.
- `navegador.getGamepads()` no renderer cobre pads XInput via Chromium; seam/mapeamento fino por
  hardware fica para a F5 quando o Qt sair.
- A paleta busca em memória (12 itens/limite): coleções grandes podem querer FTS depois; F2 mede.
- `Ctrl+Shift+I` do Chromium continua abrindo DevTools — o menu F12 é o caminho oficial.
- Screenshot do selftest não cobre paleta aberta (entrada por teclado); prova por checklist.
