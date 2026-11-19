#!/usr/bin/env python3
"""Suíte stdlib: cada teste em processo e diretório temporário próprios, em paralelo.

    python ferramentas/testes/executar.py                 # tudo, um caso por núcleo
    python ferramentas/testes/executar.py --alterados     # só o que toca o que você mudou
    python ferramentas/testes/executar.py -k loja         # nome do caso contém "loja"
    python ferramentas/testes/executar.py --falhas        # só o que falhou da última vez
    python ferramentas/testes/executar.py --modulo test_ponte --cobertura

O audit hook bloqueia escrita fora do sandbox, rede e processos externos.
Não depende de monkeypatch para proteger a instalação real. Cada caso grava
quais arquivos do projeto executou (Python 3.12+, `sys.monitoring`); esse mapa
fica em `.provas/testes-estado.json` e é o que o `--alterados` usa.
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import urllib.request
from pathlib import Path

TESTES_DIR = Path(__file__).resolve().parent
REPO = TESTES_DIR.parent.parent.parent
CODIGO = REPO / "codigo"
FRONTENDS = CODIGO / "frontends"
ESTADO = REPO / ".provas" / "testes-estado.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(CODIGO))
sys.path.insert(0, str(FRONTENDS))

# ---- contrato comum com conftest.py (ao lado; o pytest coleta os mesmos casos) ----
TIMEOUT_CASO = 120
PULO = re.compile(r"\bskip\b|\[pula\]", re.I)
# mudar o próprio runner, o conftest ou a config muda todos os casos
GERAIS = ("codigo/ferramentas/testes/executar.py", "codigo/ferramentas/testes/conftest.py", "pyproject.toml")


def casos(arquivo: Path) -> list[str]:
    """Nomes `teste_*` do módulo, lidos por AST (sem importar no processo pai)."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    return sorted(n.name for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name.startswith("teste_"))


def ambiente_caso() -> dict:
    """Ambiente do subprocesso de um caso: UTF-8, sem bytecode e com o núcleo no PYTHONPATH."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONFAULTHANDLER="1")
    env["PYTHONPATH"] = os.pathsep.join(
        [str(CODIGO), str(FRONTENDS)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


def pasta_dos_casos() -> Path:
    """Pasta-mãe das sandboxes temporárias (uma por caso)."""
    pasta = Path(tempfile.gettempdir()) / "opencode"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def afirmar(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "afirmação falhou")


def azahar_fake(emu):
    """Binário falso do Azahar que o SO atual detecta (exe no Win, AppImage no Linux)."""
    from pathlib import Path as _P
    emu = _P(emu)
    if sys.platform == "darwin":
        binario = emu / "Azahar.app" / "Contents" / "MacOS"
        binario.mkdir(parents=True, exist_ok=True)
        (binario / "azahar").write_bytes(b"MachO-fake")
    elif os.name == "nt":
        (emu / "azahar.exe").write_bytes(b"MZ" + b"0" * 64)
    else:
        (emu / "azahar.AppImage").write_bytes(b"\x7fELF" + b"0" * 64)
    return emu


def isolar(raiz: Path):
    raiz = raiz.resolve()
    for sub in ("dados", "emu/user", "roms", "appdata", "programdata", "home"):
        (raiz / sub).mkdir(parents=True, exist_ok=True)
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_") or chave == "HYDRA_DB_PATH":
            os.environ.pop(chave)
    os.environ.update({
        "BIBLIOTECA_HOME": str(raiz / "dados"),
        "BIBLIOTECA_AZAHAR_DIR": str(raiz / "emu"),
        "BIBLIOTECA_WIN_ROOT": str(raiz / "win"),
        "BIBLIOTECA_LINUX_ROOT": str(raiz / "linux"),
        "BIBLIOTECA_MAC_ROOT": str(raiz / "mac"),
        "BIBLIOTECA_SCAN_ROOTS": str(raiz / "roms"),
        "BIBLIOTECA_ROMS_ROOTS": str(raiz / "roms"),
        "APPDATA": str(raiz / "appdata"), "LOCALAPPDATA": str(raiz / "appdata"),
        "ProgramData": str(raiz / "programdata"),
        "HOME": str(raiz / "home"), "USERPROFILE": str(raiz / "home"),
        "TMP": str(raiz), "TEMP": str(raiz),
    })
    tempfile.tempdir = str(raiz)

    def dentro(p, dir_fd=-1, seguir=True):
        if isinstance(p, int) or p is None:
            return
        if str(p) == ":memory:":
            return
        pp = Path(os.fsdecode(p))
        if not pp.is_absolute() and isinstance(dir_fd, int) and dir_fd >= 0:
            try:
                base = os.readlink(f"/proc/self/fd/{dir_fd}")
            except OSError:
                return
            pp = Path(base) / pp
        # unlink/rmdir removem a entrada, não o alvo do último symlink.
        # Os pais ainda são resolvidos para impedir escapes por links de pasta;
        # abspath normaliza também um componente final '..' sem seguir links.
        alvo = pp.resolve() if seguir else Path(os.path.abspath(pp.parent.resolve() / pp.name))
        if alvo != raiz and raiz not in alvo.parents:
            raise PermissionError(f"Teste tentou escrever fora do sandbox: {alvo}")

    def audit(event, args):
        if event == "open":
            path, mode, flags = args
            if (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
                dentro(path)
        elif event in ("os.remove", "os.unlink", "os.rmdir"):
            dentro(args[0], args[1] if len(args) > 1 else -1, seguir=False)
        elif event in ("os.mkdir", "os.chmod"):
            dentro(args[0], args[2] if len(args) > 2 else -1)
        elif event == "os.utime":
            dentro(args[0], args[3] if len(args) > 3 else -1)
        elif event == "os.open":
            path, flags = args[0], args[1] if len(args) > 1 else 0
            if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                dentro(path, args[3] if len(args) > 3 else -1)
        elif event == "sqlite3.connect":
            path = os.fsdecode(args[0])
            if path.startswith("file:"):
                parsed = urllib.parse.urlsplit(path)
                path = urllib.request.url2pathname(parsed.path)
            dentro(path)
        elif event in ("os.rename", "os.replace", "os.link"):
            dentro(args[0], args[2] if len(args) > 2 else -1)
            dentro(args[1], args[3] if len(args) > 3 else -1)
        elif event == "os.symlink":
            dentro(args[0])
            dentro(args[1], args[2] if len(args) > 2 else -1)
        elif event in ("socket.connect", "subprocess.Popen", "os.system", "os.startfile"):
            raise PermissionError(f"Operação externa bloqueada no teste: {event}")
    sys.addaudithook(audit)


# ---------------------------------------------------------------- mapa teste → arquivos

def _relativo(caminho: str) -> str | None:
    """Caminho do repositório (posix) se o arquivo for código do projeto (fora dos testes)."""
    try:
        rel = Path(caminho).resolve().relative_to(REPO).as_posix()
    except (ValueError, OSError):
        return None
    if not rel.startswith("codigo/") or rel.startswith("codigo/ferramentas/testes/"):
        return None
    return rel


def iniciar_mapa():
    """Registra cada função do projeto na 1ª execução (sys.monitoring; custo quase zero depois).

    Devolve o conjunto que vai sendo preenchido, ou None em Python < 3.12.
    """
    monitor = getattr(sys, "monitoring", None)
    if monitor is None:
        return None
    vistos: set[str] = set()
    prefixo = os.path.normcase(str(CODIGO))
    ferramenta = 4  # 0..5; 1 é do coverage, 2 do profiler

    def ao_iniciar(code, _offset):
        # só funções que rodaram (CO_OPTIMIZED): o código de módulo/classe roda em
        # todo import e faria qualquer teste "depender" de tudo que o serviço importa
        if code.co_flags & 0x1 and os.path.normcase(code.co_filename).startswith(prefixo):
            vistos.add(code.co_filename)
        return monitor.DISABLE

    try:
        monitor.use_tool_id(ferramenta, "tucoteca-mapa")
    except ValueError:
        return None
    monitor.register_callback(ferramenta, monitor.events.PY_START, ao_iniciar)
    monitor.set_events(ferramenta, monitor.events.PY_START)
    return vistos


def gravar_mapa(vistos, destino: Path):
    # desliga o monitor antes de ler: threads do caso (trabalhos da ponte) podem seguir rodando
    sys.monitoring.set_events(4, 0)
    arquivos = sorted({r for f in list(vistos) if (r := _relativo(f))})
    destino.write_text(json.dumps(arquivos), encoding="utf-8")


# ---------------------------------------------------------------- estado entre execuções

def ler_estado() -> dict:
    try:
        estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        estado = {}
    estado = estado if isinstance(estado, dict) else {}
    for chave in ("tempos", "mapa"):
        if not isinstance(estado.get(chave), dict):
            estado[chave] = {}
    if not isinstance(estado.get("falhas"), list):
        estado["falhas"] = []
    return estado


def gravar_estado(estado: dict, resultados: list[dict], selecao_completa: bool):
    for r in resultados:
        estado["tempos"][r["teste"]] = r["segundos"]
        if r.get("arquivos") is not None:
            estado["mapa"][r["teste"]] = r["arquivos"]
    falharam = {r["teste"] for r in resultados if r["status"] == "FAIL"}
    rodaram = {r["teste"] for r in resultados}
    anteriores = set() if selecao_completa else set(estado["falhas"]) - rodaram
    estado["falhas"] = sorted(anteriores | falharam)
    try:
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as erro:
        print(f"(não gravei {ESTADO}: {erro})")


# ---------------------------------------------------------------- seleção

def arquivos_alterados(ref: str) -> set[str] | None:
    """Arquivos mudados desde `ref` (inclui não commitados e novos); None se o Git não responder."""
    try:
        def git(*a):
            r = subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=30)
            if r.returncode:
                raise OSError(r.stderr.strip())
            return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}
        return git("diff", "--name-only", ref) | git("ls-files", "--others", "--exclude-standard")
    except (OSError, subprocess.SubprocessError):
        return None


def _imports_do_teste(arquivo: Path) -> set[str]:
    """Módulos que o arquivo de teste importa (qualquer escopo), como prefixos `a.b.c`."""
    nomes: set[str] = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
            nomes.update(f"{no.module}.{a.name}" for a in no.names)
    return nomes


def _modulo_de(rel: str) -> str:
    """codigo/bib_nucleo/rede/x.py → bib_nucleo.rede.x; codigo/frontends/ponte.py → ponte."""
    p = Path(rel).with_suffix("")
    partes = p.parts[2:] if p.parts[:2] == ("codigo", "frontends") else p.parts[1:]
    if partes and partes[-1] == "__init__":
        partes = partes[:-1]
    return ".".join(partes)


def filtrar_por_alteracao(selecao, alterados: set[str], mapa: dict) -> tuple[list, str]:
    """Casos afetados por `alterados`: os que executaram funções dos arquivos mudados
    (mapa da última execução) e os que importam diretamente os módulos mudados."""
    if any(a in GERAIS for a in alterados):
        return selecao, "o runner/config mudou: todos os casos"
    testes = {a for a in alterados if a.startswith("codigo/ferramentas/testes/test_")}
    codigo = {a for a in alterados if a.endswith(".py") and a.startswith("codigo/") and a not in testes}
    modulos = {_modulo_de(a) for a in codigo}
    imports_cache: dict[Path, set[str]] = {}
    escolhidos = []
    for arq, nome in selecao:
        rel = f"codigo/ferramentas/testes/{arq.name}"
        chave = f"{arq.stem}.{nome}"
        if rel in testes or (chave in mapa and codigo & set(mapa[chave])):
            escolhidos.append((arq, nome))
            continue
        if not codigo:
            continue
        if arq not in imports_cache:
            imports_cache[arq] = _imports_do_teste(arq)
        # import direto (pega erro na carga do módulo); sem mapa, também o pacote pai
        if any(imp == m or imp.startswith(m + ".") or (chave not in mapa and m.startswith(imp + "."))
               for imp in imports_cache[arq] for m in modulos):
            escolhidos.append((arq, nome))
    resto = sorted(a for a in alterados if not a.endswith(".py"))
    nota = f"{len(codigo)} arquivo(s) de código e {len(testes)} de teste alterados"
    if resto:
        nota += f"; fora do Python: {len(resto)} (Electron: npm test)"
    return escolhidos, nota


# ---------------------------------------------------------------- execução

def rodar_caso(arq: Path, nome: str, cobertura: Path | None = None) -> dict:
    inicio = time.monotonic()
    arquivos = None
    with tempfile.TemporaryDirectory(prefix="hub-teste-", dir=pasta_dos_casos()) as tmp:
        cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "--caso", arq.name, nome, "--raiz", tmp,
               "--mapa", str(Path(tmp) / ".mapa.json")]
        if cobertura is not None:
            cmd += ["--coverage-arquivo", str(Path(tmp) / ".coverage")]
        try:
            r = subprocess.run(cmd, env=ambiente_caso(), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=TIMEOUT_CASO)
        except subprocess.TimeoutExpired:
            r = subprocess.CompletedProcess([], 1, "", f"Teste excedeu {TIMEOUT_CASO} segundos.")
        try:
            arquivos = json.loads((Path(tmp) / ".mapa.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            arquivos = None
        if cobertura is not None and (Path(tmp) / ".coverage").is_file():
            shutil.copy2(Path(tmp) / ".coverage", cobertura / f".coverage.{arq.stem}.{nome}")
    pulo = r.returncode == 0 and bool(PULO.search(r.stdout))
    status = "FAIL" if r.returncode else "SKIP" if pulo else "PASS"
    return {"teste": f"{arq.stem}.{nome}", "status": status, "segundos": round(time.monotonic() - inicio, 3),
            "saida": r.stdout + r.stderr if r.returncode or pulo else "", "codigo": r.returncode,
            "arquivos": arquivos}


def combinar_cobertura(pasta: Path):
    """Junta os .coverage dos casos e gera relatório (texto, JSON e HTML) em `pasta`."""
    import coverage
    cov = coverage.Coverage(data_file=str(pasta / ".coverage"), config_file=str(REPO / "pyproject.toml"))
    cov.combine(data_paths=[str(pasta)])
    cov.save()
    cov.json_report(outfile=str(pasta / "coverage.json"))
    cov.html_report(directory=str(pasta / "html"))
    cov.report()
    print(f"Relatório de cobertura real dos subprocessos: {pasta}")


def _caso_filho(args) -> int:
    isolar(Path(args.raiz))
    vistos = iniciar_mapa() if args.mapa else None
    arq, nome = args.caso
    spec = importlib.util.spec_from_file_location("caso", TESTES_DIR / arq)
    mod = importlib.util.module_from_spec(spec)
    cobertura = None
    try:
        if args.coverage_arquivo:
            import coverage
            cobertura = coverage.Coverage(data_file=args.coverage_arquivo,
                                           config_file=str(REPO / "pyproject.toml"))
            cobertura.start()
        spec.loader.exec_module(mod)
        getattr(mod, nome)()
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        if cobertura:
            cobertura.stop()
            cobertura.save()
        if vistos is not None:
            gravar_mapa(vistos, Path(args.mapa))
    return 0


def _imprimir(linha: str):
    try:
        print(linha, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((linha + "\n").encode("utf-8", "replace"))
        sys.stdout.flush()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--caso", nargs=2, metavar=("ARQUIVO", "CASO"), help="um caso só, ex.: test_fontes.py teste_x")
    ap.add_argument("--raiz", help=argparse.SUPPRESS)
    ap.add_argument("--mapa", help=argparse.SUPPRESS)
    ap.add_argument("--coverage-arquivo", help=argparse.SUPPRESS)
    ap.add_argument("--modulo", action="append", default=[],
                    help="executa só este módulo, ex.: test_baixar (repetível)")
    ap.add_argument("-k", dest="filtro", action="append", default=[],
                    help="só casos cujo nome contém o texto (repetível = qualquer um)")
    ap.add_argument("--alterados", nargs="?", const="HEAD", metavar="REF",
                    help="só os casos que tocam arquivos mudados desde REF (padrão: HEAD + não commitados)")
    ap.add_argument("--falhas", action="store_true", help="só o que falhou na última execução")
    ap.add_argument("-j", "--paralelo", type=int, default=0,
                    help="casos ao mesmo tempo (padrão: um por núcleo; 1 = em série)")
    ap.add_argument("--cobertura", action="store_true", help="mede cobertura nos processos isolados")
    ap.add_argument("--json", metavar="ARQUIVO", help="salva relatório estruturado")
    args = ap.parse_args(argv)
    if args.caso and args.raiz:
        return _caso_filho(args)

    estado = ler_estado()
    modulos = {m.removesuffix(".py") for m in args.modulo}
    selecao = [(arq, nome) for arq in sorted(TESTES_DIR.glob("test_*.py"))
               if not modulos or arq.stem in modulos for nome in casos(arq)]
    if args.caso:
        selecao = [(a, n) for a, n in selecao if (a.name, n) == tuple(args.caso)]
    completa = not (modulos or args.filtro or args.falhas or args.alterados or args.caso)
    if args.filtro:
        selecao = [(a, n) for a, n in selecao if any(f.lower() in f"{a.stem}.{n}".lower() for f in args.filtro)]
    if args.falhas:
        anteriores = set(estado["falhas"])
        selecao = [(a, n) for a, n in selecao if f"{a.stem}.{n}" in anteriores]
        if not selecao:
            print("Nenhuma falha registrada na última execução.")
            return 0
    if args.alterados:
        alterados = arquivos_alterados(args.alterados)
        if alterados is None:
            print("(Git indisponível: rodando a seleção inteira)")
        else:
            selecao, nota = filtrar_por_alteracao(selecao, alterados, estado["mapa"])
            print(f"--alterados {args.alterados}: {nota} → {len(selecao)} caso(s)")
            if not selecao:
                return 0
    if not selecao:
        ap.error("nenhum teste corresponde à seleção")

    # os mais lentos primeiro: o último a terminar não fica sozinho no fim
    selecao.sort(key=lambda c: -float(estado["tempos"].get(f"{c[0].stem}.{c[1]}", 1.0)))
    jobs = max(1, args.paralelo or os.cpu_count() or 2)
    pasta_cov = None
    if args.cobertura:
        from datetime import datetime
        pasta_cov = REPO / ".provas" / "cobertura" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        pasta_cov.mkdir(parents=True)

    inicio = time.monotonic()
    resultados = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futuros = [pool.submit(rodar_caso, a, n, pasta_cov) for a, n in selecao]
        for f in concurrent.futures.as_completed(futuros):
            r = f.result()
            resultados.append(r)
            _imprimir(f"{r['status']} {r['teste']}")
            if r["status"] == "FAIL":
                _imprimir(f"Processo do caso encerrou com código {r['codigo']}.")
                _imprimir(r["saida"])
    duracao = time.monotonic() - inicio

    total = len(resultados)
    falhas = sum(r["status"] == "FAIL" for r in resultados)
    pulados = sum(r["status"] == "SKIP" for r in resultados)
    lentos = sorted(resultados, key=lambda r: -r["segundos"])[:5]
    _imprimir("\nMais lentos: " + ", ".join(f"{r['teste']} {r['segundos']:.1f}s" for r in lentos))
    _imprimir(f"\n{total - falhas}/{total} casos sem falha; {pulados} pulado(s) por ambiente."
              f" ({duracao:.0f} s, {jobs} em paralelo)")
    gravar_estado(estado, resultados, completa)
    if pasta_cov is not None:
        combinar_cobertura(pasta_cov)
    if args.json:
        destino = Path(args.json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps({"python": sys.version.split()[0], "plataforma": sys.platform,
                                       "total": total, "falhas": falhas, "pulados": pulados,
                                       "segundos": round(duracao, 1),
                                       "resultados": [{k: v for k, v in r.items() if k != "arquivos"}
                                                      for r in sorted(resultados, key=lambda r: r["teste"])]},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    return int(bool(falhas))


if __name__ == "__main__":
    raise SystemExit(main())
