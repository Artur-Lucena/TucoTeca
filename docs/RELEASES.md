# Releases da TucoTeca

Uma release é uma entrega congelada, não uma pasta renomeada. Instalador,
fontes, manifestos e tag identificam a **mesma versão e revisão**. Nenhuma
etapa toca a coleção pessoal: o app instalado usa `Documentos\TucoTeca`
(ou `BIBLIOTECA_HOME`) e as provas usam coleções sintéticas.

A entrega Windows é um instalador NSIS (`electron-builder`), por usuário e
sem admin; a do macOS é uma `.dmg` por arquitetura (Apple Silicon e Intel),
com assinatura ad-hoc e sem notarização. Os dois levam o app Electron e, em
`resources/tucoteca/`, o núcleo Python (`bib_nucleo`), a ponte (`ponte.py`,
`servicos_ui`), `abrir_hub.py`, `codigo/VERSION`, `LICENSE`, os docs do menu
Ajuda e o Python embutido da plataforma. Linux roda pelos fontes.

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

Os ícones (`resources/icon.ico` e `icon.icns`) são gerados por
`codigo/ferramentas/gerar_icone.py` (reproduzíveis; o teste confere os
binários versionados).

### macOS (.dmg)

As `.dmg` saem do CI (job `app-mac` de `.github/workflows/testes.yml`) na
mesma revisão: Python de cada arquitetura (python-build-standalone, SHA-256
fixado), `npm run dist:mac`, `preparar_release.py --conferir-mac` (confere
cada `.app` e grava `conferencia-mac.json` com os SHA-256 das `.dmg`) e
selftest do app Apple Silicon; o job `app-mac-intel` instala a `.dmg` Intel
num Mac Intel e roda o selftest dela. Baixe o artefato `mac-dmgs` do run da
revisão congelada:

```powershell
gh run download <run-id> --name mac-dmgs --dir dist/mac-v<versão>
```

Num Mac, o mesmo vale localmente: `preparar_runtime_python.py --plataforma
macos-arm64` (e `macos-x64`), `npm run dist:mac` e `--conferir-mac`.

## 3. Preparar os anexos

```powershell
py -3.14 -B codigo/ferramentas/preparar_release.py --revisao $sha --saida dist/release/v<versão> `
    --mac dist/mac-v<versão>
```

O preparador exige HEAD limpo no SHA e fontes rastreados; confere versões,
o instalador da mesma versão e a árvore `win-unpacked` (ponte, núcleo,
runtime e ausência de estado pessoal). Com `--mac`, só aceita `.dmg` cuja
conferência do Mac seja da mesma versão e revisão e cujo SHA-256 bata com o
conferido lá. Monta tudo num staging e só renomeia para a pasta final no
sucesso; destino existente é recusado.

| Anexo | Conteúdo |
|---|---|
| `TucoTeca-Setup-<versão>-x64.exe` | instalador Windows |
| `TucoTeca-<versão>-mac-arm64.dmg` / `-mac-x64.dmg` | app macOS (Apple Silicon / Intel) |
| `tucoteca-<versão>-fontes.zip` | fontes (Python + Electron) com `MANIFESTO-FONTES.json` |
| `NOTAS-RELEASE.md` | instalação (Windows e macOS), SmartScreen/Gatekeeper e a seção do changelog |
| `release.json` | versão, revisão, instaladores por plataforma, runtime e inventário dos anexos |
| `SHA256SUMS.txt` | hashes de todos os outros anexos |

O instalador não é assinado e o app do Mac não é notarizado (decisão do
usuário): o SmartScreen pode avisar na primeira execução e o macOS pede
"botão direito → Abrir" uma vez; as notas explicam como prosseguir.

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
