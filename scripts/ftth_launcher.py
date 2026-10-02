#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一启动器（Python 版，替代原 scripts/ftth.cmd）。

WHY THIS EXISTS
  宿主 runtime（如 TeleAgent 自带解释器）常被前置到 PATH 前面，且没有 ezdxf，
  直接 `python xxx.py` 会死在 `ModuleNotFoundError: No module named 'ezdxf'`。
  本启动器对候选解释器做**真实执行探测**（`<exe> -c "import ezdxf"`，不是路径猜测），
  把业务脚本交给「确实能 import ezdxf」的解释器执行 —— 调用方无需知道解释器路径。

  本文件自身**不依赖 ezdxf**，任意 Python 3 都能启动它；`python` 裸命令在这里
  是**安全**的（探测不中就换），这是「禁止裸 python」铁律的唯一豁免入口。

USAGE（与原 ftth.cmd 完全等价）
  python scripts/ftth_launcher.py <子命令> [参数...]   -> scripts/ftth.py <子命令> ...
  python scripts/ftth_launcher.py <脚本.py> [参数...]    -> scripts/<脚本.py> [参数...]

  python scripts/ftth_launcher.py probe --dxf a.dxf --out o.json
  python scripts/ftth_launcher.py dump_geom.py --dxf a.dxf

参数分派（与原 _launch.py 相同）
  首参以 `.py` 结尾 ⇒ 转发该脚本（相对/绝对路径均可，`scripts/` 前缀可写可不写）；
  否则转发 `ftth.py <首参> ...`（子命令模式）。

解释器探测（逐个真执行，命中即停）
  0) 解释器缓存（本机已验证过的解释器直接信任；exe 或 ezdxf 路径消失才重探）
  1) 环境变量 FTTH_PYTHON（优先级最高；不带 ezdxf 时自动回落继续探测）
  2) 当前解释器 sys.executable
  3) 常见安装位置 %LOCALAPPDATA%/%ProgramFiles%/%SystemDrive% 下 Python311~313
  4) py 启动器（py -3.13 / -3.12 / -3.11 / -3）
  5) PATH 上的 python

  ⚠ 实测（2026-09-25，某 Windows 主机）：`import ezdxf` 单次 24~52s（user CPU<0.1s，
  全为进程冷启动/杀软扫描的 I/O 等待），且**冷热不稳定**。探测 timeout 必须远大于
  该上界（取 120s）——30s 恰好卡在耗时边界上，导致同一台机器「时过时不过」。
  缓存文件记录 exe + ezdxf 模块路径，复用时只做 isfile 校验（0 成本）；两个路径
  任一消失即视为环境变更，自动重探。缓存损坏/丢失只是多付一次探测，无害。

退出码
  透传目标脚本退出码；全部候选失败 => 9，并打印候选清单与处置办法。

参数保真
  subprocess 直接传 argv 列表（不经 shell），引号/空格/中文原样透传，
  比 cmd.exe 的 %* 转发更不易出问题。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _ezdxf_ok(exe, *extra_args):
    """真实执行 import ezdxf 探测（不是路径猜测）。返回 (ok, ezdxf路径)。"""
    try:
        proc = subprocess.run(
            [exe] + list(extra_args)
            + ["-c", "import ezdxf,sys;sys.stdout.write(ezdxf.__file__)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
        if proc.returncode == 0:
            p = proc.stdout.decode("utf-8", "replace").strip()
            return True, p
        return False, ""
    except (OSError, subprocess.SubprocessError):
        return False, ""


# 解释器缓存：本机验证过的解释器直接信任，exe/ezdxf 路径任一消失才重探。
# 实测探测一次 25~120s（import ezdxf 慢且不稳定），缓存把 N 次调用降为 1 次。
CACHE_FILE = os.path.join(HERE, ".interpreter_cache.json")


def _cache_load():
    try:
        import json
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        exe = d.get("exe") or ""
        ez = d.get("ezdxf_path") or ""
        extra = d.get("extra_args") or ()
        if exe and os.path.isfile(exe) and ez and os.path.isfile(ez):
            return exe, tuple(extra)
    except (OSError, ValueError):
        pass
    return None, None


def _cache_save(exe, ezdxf_path, extra_args):
    try:
        import json
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"exe": exe, "ezdxf_path": ezdxf_path,
                       "extra_args": list(extra_args)}, f, ensure_ascii=False)
    except OSError:
        pass  # 缓存写失败只是下次多付一次探测，不致命


def _resolve_py():
    """按候选清单逐个真执行探测，返回 (python_exe, 需前置到脚本前的额外参数)。"""
    # 0) 解释器缓存（本机已验证，isfile 复验，0 成本）
    exe, extra = _cache_load()
    if exe:
        return exe, extra
    # 0.5) 显式覆盖：FTTH_PYTHON（优先级最高，不带 ezdxf 时回落）
    ftth_python = os.environ.get("FTTH_PYTHON")
    if ftth_python and os.path.isfile(ftth_python):
        ok, ez = _ezdxf_ok(ftth_python)
        if ok:
            _cache_save(ftth_python, ez, ())
            return ftth_python, ()
    # 1) 当前解释器（最常见的入口：直接 python 调本脚本）
    cur = sys.executable
    if cur and os.path.isfile(cur):
        ok, ez = _ezdxf_ok(cur)
        if ok:
            _cache_save(cur, ez, ())
            return cur, ()
    # 2) 常见安装位置
    candidates = []
    base_dirs = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        base_dirs.append(os.path.join(local_appdata, "Programs", "Python"))
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        base_dirs.append(os.path.join(program_files, "Python"))
    sys_drive = os.environ.get("SystemDrive") or ""
    if sys_drive:
        base_dirs.append(os.path.join(sys_drive, "Python"))
    for base in base_dirs:
        for ver in ("313", "312", "311"):
            cand = os.path.join(base, "Python%s" % ver, "python.exe")
            if os.path.isfile(cand):
                ok, ez = _ezdxf_ok(cand)
                if ok:
                    _cache_save(cand, ez, ())
                    return cand, ()
    # 3) py 启动器（按注册表选解释器，不受 PATH 劫持影响）
    for ver in ("3.13", "3.12", "3.11", "3"):
        ok, ez = _ezdxf_ok("py", "-" + ver)
        if ok:
            _cache_save("py", ez, ("-" + ver,))
            return "py", ("-" + ver,)
    # 4) PATH 上的 python（真执行成功才命中，故必带 ezdxf）
    ok, ez = _ezdxf_ok("python")
    if ok:
        _cache_save("python", ez, ())
        return "python", ()
    return None, None


def main():
    argv = sys.argv[1:]
    target = os.path.join(HERE, "ftth.py")
    if argv and argv[0].lower().endswith(".py"):
        cand = argv.pop(0)
        if not os.path.isabs(cand):
            norm = cand.replace("\\", "/")
            # HERE 本身就是 scripts/ 目录；容忍调用方多写一层 "scripts/" 前缀
            if norm.lower().startswith("scripts/"):
                norm = norm[len("scripts/"):]
            cand = os.path.normpath(os.path.join(HERE, norm))
        if not os.path.exists(cand):
            sys.stderr.write("[launch] 找不到脚本: %s\n" % cand)
            return 2
        target = cand

    py, py_extra = _resolve_py()
    if py is None:
        sys.stderr.write("[launch] ERROR: 未找到可 import ezdxf 的 Python 解释器。\n")
        sys.stderr.write("[launch] 已尝试：解释器缓存、FTTH_PYTHON、当前解释器、常见安装路径、py 启动器、PATH 上的 python。\n")
        sys.stderr.write("[launch] 处置办法之一：\n")
        sys.stderr.write("[launch]   * 向其中一个解释器安装 ezdxf，或\n")
        sys.stderr.write("[launch]   * 设 FTTH_PYTHON=<带 ezdxf 的 python.exe 绝对路径>，或\n")
        sys.stderr.write("[launch]   * 若怀疑缓存指向了坏解释器：删除 %s 后重跑。\n" % CACHE_FILE)
        sys.stderr.write("[launch] 详见 references/scripts_reference.md §解释器契约。\n")
        return 9
    # ---- L1-C7 调用契约的机器标记（2026-10-02 会审整改 P2-4 新增）----
    #   C7 此前是本技能唯一 `declared`（无检查器）契约：「业务脚本是否绕过本启动器
    #   直调」判不了 —— 调用链是跨进程事实，此前所有门禁都跑在单脚本内。
    #   本行把调用链变成**产物上的可见事实**：经启动器派生的产物，顶层带
    #   `_via_launcher: true`（ftth_common.write_json 依此环境变量写入）。
    #   值刻意是**布尔真值而非时间戳/路径** —— 含变量的标记会让每次运行的产物
    #   md5 都变，golden 回归将永久假红（这正是 T14 存在的意义）。
    #   检查方 = scripts/check_launch_path.py。
    env = dict(os.environ)
    env["FTTH_VIA_LAUNCHER"] = "1"
    return subprocess.call([py] + list(py_extra) + [target] + argv, env=env)


if __name__ == "__main__":
    sys.exit(main())