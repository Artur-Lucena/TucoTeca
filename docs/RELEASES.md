# Releases da TucoTeca

Uma release é uma entrega congelada, não uma pasta renomeada. Instalador,
fontes, manifestos e tag identificam a **mesma versão e revisão**. Nenhuma
etapa toca a coleção pessoal: o app instalado usa `Documentos\TucoTeca`
(ou `BIBLIOTECA_HOME`) e as provas usam coleções sintéticas.

A entrega Windows é um instalador NSIS (`electron-builder`), por usuário e
sem admin. Ele leva o app Electron e, em `resources/tucoteca/`, o núcleo
Python (`bib_core`, `bib_nucleo`), a ponte (`ponte.py`, `servicos_ui`),
`abrir_hub.py`, `codigo/VERSION`, `LICENSE`, os docs do menu Ajuda e o Python
embutido. A TUI (`tucoteca.sh`) segue para Linux/macOS pelos fontes.

## 1. Finalizar e congelar

- Atualize `codigo/VERSION`, a versão em `pyproject.toml` e em
  `codigo/frontends/electron/package.json`, e a seção do `docs/CHANGELOG.md` (o
  preparador recusa versões divergentes ou sem seção).
- Não escreva o SHA do próprio commit em um arquivo desse commit.
- Rode os gates e faça commit; o checkout precisa ficar limpo.

```powershell
py -3.14 -B codigo/ferramentas/testes/executar.py
npm --prefix codigo/frontends/electron run typecheck
npm --prefix codigo/frontends/electron test
ruff check codigo
$sha = git rev-parse HEAD
```

## 2. Gerar o instalador

```powershell
py -3.14 -B codigo/ferramentas/preparar_runtime_python.py   # Python embeddable oficial, SHA-256 fixado
npm --prefix codigo/frontends/electron ci
npm --prefix codigo/frontends/electron run dist
```

Saída: `codigo/frontends/electron/dist/TucoTeca-Setup-<versão>-x64.exe` e a
árvore `win-unpacked/`. Sem o Python embutido o `dist` falha de propósito;
`TUCOTECA_SEM_RUNTIME=1` aceita, e o app instalado passa a depender do
`py -3.14` do sistema (as notas avisam).

Prova do app empacotado, com coleção e userData sintéticos:

```powershell
py -3.14 -B codigo/ferramentas/semear_prova_electron.py --destino .provas/release/home --limpar
$env:BIBLIOTECA_HOME = "$PWD\.provas\release\home"
$env:TUCOTECA_USERDATA = "$PWD\.provas\release\userdata"
codigo\frontends\electron\dist\win-unpacked\TucoTeca.exe --selftest --screenshot .provas\release\inicio.png
```

O `ícone` (`resources/icon.ico`) é gerado por `codigo/ferramentas/gerar_icone.py`
(reproduzível; o teste confere o binário versionado).

## 3. Preparar os anexos

```powershell
py -3.14 -B codigo/ferramentas/preparar_release.py --revisao $sha --saida dist/release/v<versão>
```

O preparador exige HEAD limpo no SHA e fontes rastreados; confere versões,
o instalador da mesma versão e a árvore `win-unpacked` (ponte, núcleo,
runtime e ausência de estado pessoal). Monta tudo num staging e só renomeia
para a pasta final no sucesso; destino existente é recusado.

| Anexo | Conteúdo |
|---|---|
| `TucoTeca-Setup-<versão>-x64.exe` | instalador Windows |
| `tucoteca-<versão>-fontes.zip` | fontes (Python + Electron) com `MANIFESTO-FONTES.json` |
| `NOTAS-RELEASE.md` | instalação, SmartScreen e a seção do changelog |
| `release.json` | versão, revisão, runtime e inventário dos anexos |
| `SHA256SUMS.txt` | hashes de todos os outros anexos |

O instalador não é assinado (decisão do usuário): o SmartScreen pode avisar
na primeira execução, e as notas explicam como prosseguir.

## 4. Publicar e conferir

1. Confira que as branches não divergiram. Crie uma tag anotada na revisão
   congelada e envie por push normal.
2. Crie a release com `gh release create --draft --verify-tag`, usando as
   notas geradas e a lista explícita de anexos.
3. Confira lista, tamanhos e digests SHA-256 retornados pela API.
4. Só então publique com `gh release edit --draft=false`.

Nunca use `--clobber`, mova uma tag enviada ou reescreva histórico para
corrigir a entrega. A tag `v1.0.0` foi criada na preparação sem release e
permanece preservada.
