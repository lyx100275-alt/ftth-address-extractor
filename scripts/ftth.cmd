@echo off
rem ============================================================================
rem ftth.cmd - unified launcher for the ftth-address-extractor toolkit.
rem
rem WHY THIS EXISTS
rem   The host runtime often puts its own interpreter ahead of the system one on
rem   PATH. That interpreter has no ezdxf, so every script dies with
rem   "ModuleNotFoundError: No module named 'ezdxf'". This launcher probes for a
rem   Python that ACTUALLY imports ezdxf (real execution, not a path guess) and
rem   forwards there - so callers never need to know the interpreter path.
rem
rem USAGE
rem   ftth.cmd <subcommand> [args...]              -> scripts\ftth.py <subcommand> ...
rem   ftth.cmd <script.py> [args...]               -> scripts\<script.py> [args...]
rem   ftth.cmd probe --dxf "drawing.dxf" --out "out_dir"
rem   ftth.cmd dump_geom.py --dxf "drawing.dxf"
rem
rem   Both forms work: the first argument decides the target (see _launch.py).
rem
rem OVERRIDE
rem   set FTTH_PYTHON=C:\full\path\to\python.exe   (checked first)
rem
rem EXIT CODES
rem   <subcommand exit code>   forwarded
rem   9                        no interpreter with ezdxf found
rem ============================================================================
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
set "PYEXE="
set "PYVER="

rem --- candidate 0: explicit override -----------------------------------------
if defined FTTH_PYTHON (
  if exist "%FTTH_PYTHON%" (
    "%FTTH_PYTHON%" -c "import ezdxf" >nul 2>nul && set "PYEXE=%FTTH_PYTHON%"
  )
)

rem --- candidate 1: conventional per-user / per-machine installs --------------
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%ProgramFiles%\Python313\python.exe"
  "%ProgramFiles%\Python312\python.exe"
  "%ProgramFiles%\Python311\python.exe"
  "%SystemDrive%\Python313\python.exe"
  "%SystemDrive%\Python312\python.exe"
) do (
  if not defined PYEXE if exist "%%~P" (
    "%%~P" -c "import ezdxf" >nul 2>nul && set "PYEXE=%%~P"
  )
)

rem --- candidate 2: the py launcher (lives outside any runtime dir) ----------
if not defined PYEXE (
  for %%V in (3.13 3.12 3.11 3) do (
    if not defined PYEXE (
      py -%%V -c "import ezdxf" >nul 2>nul && ( set "PYEXE=py" & set "PYVER=-%%V" )
    )
  )
)

rem --- candidate 3: whatever `python` resolves to (may be the hijacked one) --
if not defined PYEXE (
  python -c "import ezdxf" >nul 2>nul && set "PYEXE=python"
)

if not defined PYEXE (
  echo [ftth.cmd] ERROR: no Python interpreter with ezdxf was found. 1>&2
  echo [ftth.cmd] Tried: %%LOCALAPPDATA%%\Programs\Python\Python311..313, 1>&2
  echo [ftth.cmd]        %%ProgramFiles%%\Python311..313, py -3.11..-3.13, python 1>&2
  echo [ftth.cmd] Fix one of: 1>&2
  echo [ftth.cmd]   * install ezdxf into one of those interpreters, or 1>&2
  echo [ftth.cmd]   * set FTTH_PYTHON to a full python.exe path that has ezdxf 1>&2
  echo [ftth.cmd] Do NOT rely on a pip mirror: an unreachable mirror reports 1>&2
  echo [ftth.cmd] "no matching distribution" for a package that does exist. 1>&2
  echo [ftth.cmd] See references/scripts_reference.md section "interpreter contract". 1>&2
  exit /b 9
)

rem --- forward through _launch.py -------------------------------------------
rem We do NOT re-order arguments here: cmd cannot drop the first argument
rem without mangling quotes/spaces. Instead the whole command line goes to
rem _launch.py, which picks the target (ftth.py by default, or the .py named
rem as the first argument) and forwards the rest verbatim.
"%PYEXE%" %PYVER% "%SCRIPT_DIR%_launch.py" %*
exit /b %ERRORLEVEL%
