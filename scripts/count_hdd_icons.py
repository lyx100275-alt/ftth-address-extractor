#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口 —— 本脚本已更名为 `count_box_icons.py`（**家居配线箱图标法**）。

改名原因：方法名此前被绑定在 `HDD` 这一种图内文字上，而实测同一设备的
图内文字随画图人而变（云峰写 `HDD`、柳辛庄写 `HD`），方法本体也与文字无关
（判据是几何：图标贴皮线末端）。故统一正名为「家居配线箱图标法」。

此文件仅作向后兼容，保证既有的 `ftth.py count-hdd` 与文档引用不失效；
**新调用请一律用 `count_box_icons.py`（或 `ftth.py count-box`）**。
"""
import os
import runpy
import sys

sys.stdout.reconfigure(encoding="utf-8")

_TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "count_box_icons.py")
if not os.path.exists(_TARGET):
    sys.stderr.write("[ERROR] 找不到 %s（技能安装不完整）\n" % _TARGET)
    sys.exit(1)
runpy.run_path(_TARGET, run_name="__main__")
