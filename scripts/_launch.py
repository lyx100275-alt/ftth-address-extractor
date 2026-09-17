#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动器转发层（由 ftth.cmd 以**已确认带 ezdxf** 的解释器调用）。

职责：把参数原样转交给目标脚本，目标由首个参数决定 ——

    ftth.cmd probe --dxf a.dxf --out o.json
        -> scripts/ftth.py probe --dxf a.dxf --out o.json
    ftth.cmd dump_geom.py --dxf a.dxf
        -> scripts/dump_geom.py --dxf a.dxf
    ftth.cmd scripts/read_titleblock_households.py --dxf a.dxf
        -> scripts/read_titleblock_households.py --dxf a.dxf

为什么不直接在 .cmd 里重排参数：批处理没有「安全删掉第一个参数」的写法
（shift 不改变 %*，手工拼 %1..%9 会破坏引号与空格）。所以整串参数交给 Python，
由本文件解析首参数。本文件不解析任何业务参数，也不改变退出码。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


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
            sys.stderr.write("[launch] \u627e\u4e0d\u5230\u811a\u672c: %s\n" % cand)
            return 2
        target = cand
    return subprocess.call([sys.executable, target] + argv)


if __name__ == "__main__":
    sys.exit(main())
