#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 标准地址表生成脚本（通用版）
从 DXF 解析 JSON（parse_dxf_structured.py 输出）+ 用户裁决的覆盖范围，生成每户一行的标准地址表 xlsx。

用法：
    python gen_addressbook.py --dxf-json 解析结果.json --out 标准地址表.xlsx [选项]

必选：
    --dxf-json       parse_dxf_structured.py 输出的解析 JSON
    --out            输出 xlsx 路径

可选：
    --coverage-json  用户裁决后的覆盖范围 JSON（格式见下方），缺省时单箱单元自动分配、双箱单元标"未分配"
    --template       标准地址模板 xlsx/xls（读取表头列结构与示例行格式，不复制示例数据）
    --addr 省,市,区,街道,小区   前5级地址（缺省从模板示例行读取，两者皆无则留空）
    --sheet-name     输出工作表名（默认"标准地址"）
    --cover-rule    户号规则：floor100=楼层*100+序号（默认），floor10=楼层*10+序号，unit=单元+楼层+序号

覆盖范围 JSON 格式（由用户裁决后提供）：
{
  "1#楼": {
    "1单元": {
      "<低区箱编号>": ["1F","2F","3F"],
      "<高区箱编号>": ["4F","5F"]
    }
  }
}

说明：
- 每户一行；九级地址（省/市/区/街道/小区/楼栋/单元/楼层/户）逐级组装。
- 户号按 楼层×100+序号 生成（如 3F 2户 → 301室、302室），可调整。
- 分纤箱归属严格按用户裁决的覆盖范围填写，未裁决楼层标"未分配"。
- 数据全部来自 DXF 解析，不照搬模板示例数据。
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from ftth_common import setup_logger, floor_num, floor_num_or_zero, bldg_num

log = setup_logger("gen_addressbook")

ap = argparse.ArgumentParser(description="FTTH 标准地址表生成（DXF → 每户一行）")
ap.add_argument("--dxf-json", required=True, help="parse_dxf_structured.py 输出的 JSON")
ap.add_argument("--out", required=True, help="输出 xlsx 路径")
ap.add_argument("--coverage-json", default=None, help="用户裁决后的覆盖范围 JSON（可选）")
ap.add_argument("--template", default=None, help="标准地址模板 xlsx/xls（可选，仅取表头与格式）")
ap.add_argument("--addr", default=None,
                help="前5级地址，逗号分隔：省,市,区,街道,小区。"
                     "【留空必须显式传空串，即 --addr 后跟一对空引号】："
                     "省略该参数(值为 None)会回退去读**模板第2行示例值**；"
                     "传空串(值为空)则五级全空。两者行为不等价，勿混用。"
                     "（模板示例行为占位文本时会被 _is_placeholder 拦住而留空，"
                     "但换成带真实数据的模板就会静默填入。）")
ap.add_argument("--branch", default=None, help="分公司名称（对应模板第1列）")
ap.add_argument("--sheet-name", default="标准地址")
ap.add_argument("--cover-rule", default="floor100", help="户号规则：floor100=楼层*100+序号（默认），floor10=楼层*10+序号，unit=单元+楼层+序号")
ap.add_argument("--floor-format", default="auto", choices=["auto", "chinese", "raw"],
                help="楼层列格式：auto=按模板示例行自动判定（原行为）；chinese=三层；raw=3F。"
                     "显式指定后不再依赖模板示例行，避免「靠改模板工作副本绕过格式」的做法。")
ap.add_argument("--door-format", default="auto", choices=["auto", "int", "str"],
                help="户号列格式：auto=按模板示例行自动判定（原行为）；int=101；str=101室。")
ap.add_argument("--fx-prefix-map", default=None,
                help="分纤箱编号前缀归一化映射（可选）\"旧前缀=新前缀;旧前缀2=新前缀2\"，"
                     "作用于编号开头。多图幅/多地块图纸上同一物理箱常在各图幅各有一个"
                     "带前缀编号，不归一会同箱多行。映射须人工确认后显式传入，"
                     "逐条改写都会打印留痕（2026-09-16，12坑复核·坑10）")
ap.add_argument("--floor-pattern", default=None, help="楼层标注正则。默认 None＝内置统一解析（支持 3F/17F/-1F/B1/B2/WF）。**不要再用 (-?\\d+)F 覆盖**，否则 B1 整层住户会被静默丢弃")
ap.add_argument("--allow-lossy", action="store_true", help="允许在丢弃楼层的情况下继续出表（默认关闭：一旦有楼层被丢弃即中止，防止静默少户）")
args = ap.parse_args()

if not os.path.exists(args.dxf_json):
    log.error(f"解析JSON不存在: {args.dxf_json}")
    sys.exit(1)

# ---------- 读取 DXF 解析结果 ----------
try:
    with open(args.dxf_json, "r", encoding="utf-8") as f:
        data = json.load(f)
except (IOError, json.JSONDecodeError) as e:
    log.error(f"无法读取解析JSON: {args.dxf_json}\n{e}")
    sys.exit(1)

# ---------- 读取用户裁决的覆盖范围 ----------
# 2026-09-14（P0-4）：兼容两种覆盖 JSON 格式：
#   ① 扁平格式 {楼栋: {单元: {箱号: [楼层,...]}}}（旧格式 / 手工裁决表）
#   ② 嵌套格式 {楼栋: {单元: {分纤箱: [{编号, 覆盖范围线索: {覆盖楼层: [...]}}]}}}（coverage-vshape 直出）
#   自动检测并统一转为扁平格式供下游使用。
# 2026-09-16（P0-接口键）：**单元键归一化**。
#   实测：产出端 analyze_coverage 给的是**全名键**（coverage["1#楼"]["单元"]["1#楼1单元"]），
#   而本脚本内部按**扁平键**（`1单元`）索引 —— 整轮静默失配，
#   调用方只能手写 coverage_flat.json 人工桥接才跑通。
#   现于入口统一归一，两种键形都直接可用（不再需要手工桥接脚本）。
def _norm_unit_key(ukey, bkey=None):
    """把单元键归一到「N单元」形式。

    兼容：`1#楼1单元` / `1号楼1单元` / `1单元` / 楼栋名本身（单单元楼栋）。
    """
    s = str(ukey).strip()
    if not s:
        return s
    m = re.search(r"(\d+)\s*[#号]?\s*楼?\s*(\d+)\s*单元", s)
    if m:
        return "%s单元" % m.group(2)
    m2 = re.fullmatch(r"(\d+)\s*单元", s)
    if m2:
        return "%s单元" % m2.group(1)
    if bkey is not None and s == str(bkey).strip():
        return "1单元"
    return s


coverage = {}
if args.coverage_json:
    try:
        with open(args.coverage_json, "r", encoding="utf-8") as f:
            raw_cov = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        log.error(f"无法读取覆盖范围JSON: {args.coverage_json}\n{e}")
        sys.exit(1)
    # 自动检测格式并转换
    # 2026-09-14（P0-4a）：coverage-vshape 的输出顶层含元数据（DXF文件/方法/参数/自检等），
    #   楼栋数据嵌在 raw_cov["楼栋"] 下；扁平格式则楼栋直接是顶层 key。
    #   先检测有无 "楼栋" 子键，有则进入它。
    bldg_source = raw_cov.get("楼栋", raw_cov) if isinstance(raw_cov, dict) else {}
    for bkey, bdata in bldg_source.items():
        if not isinstance(bdata, dict):
            continue
        # 尝试找到单元字典：可能是 bdata 本身，也可能是 bdata["单元"]
        units = bdata.get("单元", bdata) if isinstance(bdata, dict) else {}
        if not isinstance(units, dict):
            continue
        coverage[bkey] = {}
        for ukey, udata in units.items():
            if not isinstance(udata, dict):
                continue
            # 单元键归一（全名 `1#楼1单元` 与扁平 `1单元` 都落到 `1单元`）
            _uk = _norm_unit_key(ukey, bkey)
            if _uk != ukey:
                log.info("  单元键归一：%r → %r" % (ukey, _uk))
            # 格式②：udata 含 "分纤箱" 列表，每项有编号+覆盖范围线索
            fx_list = udata.get("分纤箱", [])
            if isinstance(fx_list, list) and fx_list and isinstance(fx_list[0], dict):
                coverage[bkey][_uk] = {}
                for fx in fx_list:
                    fx_id = fx.get("编号", "")
                    cov_floors = fx.get("覆盖范围线索", {}).get("覆盖楼层", [])
                    if fx_id and cov_floors:
                        coverage[bkey][_uk][fx_id] = cov_floors
            # 格式①：udata 直接是 {箱号: [楼层,...]}
            elif all(isinstance(v, list) for v in udata.values()):
                coverage[bkey][_uk] = dict(udata)
            # else: 无法识别，跳过
    log.info(f"覆盖范围JSON已加载（格式自动检测）：{len(coverage)}栋")

    # 2026-09-16（12坑复核·坑10）：分纤箱编号前缀归一化（可选，显式传入才生效）。
    #   作用于 coverage 键与 parse 侧箱编号两处，保证两来源一致可比；
    #   归一后编号冲突（覆盖范围不同）显式告警交人裁决，不自动择一。
    _fx_pmap = {}
    if args.fx_prefix_map:
        for _item in args.fx_prefix_map.split(";"):
            _item = _item.strip()
            if "=" in _item:
                _pa, _pb = _item.split("=", 1)
                _fx_pmap[_pa.strip()] = _pb.strip()

    def _norm_fx(_fid):
        for _pa, _pb in _fx_pmap.items():
            if _pa and isinstance(_fid, str) and _fid.startswith(_pa):
                return _pb + _fid[len(_pa):]
        return _fid

    if _fx_pmap:
        _ren = 0
        for _b, _bd in coverage.items():
            for _u, _ud in _bd.items():
                _nd = {}
                for _fid, _fl in _ud.items():
                    _nf = _norm_fx(_fid)
                    if _nf != _fid:
                        log.info("  [编号归一] %s/%s：%s → %s" % (_b, _u, _fid, _nf))
                        _ren += 1
                    if _nf in _nd and _nd[_nf] != _fl:
                        log.warning("  [编号归一] 归一后编号冲突：%s（%s/%s）两侧覆盖范围不同，需人工裁决"
                                    % (_nf, _b, _u))
                    _nd[_nf] = _fl
                coverage[_b][_u] = _nd
        log.info("编号前缀归一完成：%d 条改写（映射 %s）" % (_ren, _fx_pmap))

    # 2026-09-16（P0-接口键）：**键失配自检**。
    #   实测失配形态：产出端单元键为全名（`1#楼1单元`）、消费端按扁平（`1单元`）索引，
    #   整轮静默失配，直到出表才发现全是"未分配"，调用方被迫手写桥接脚本。
    #   现于加载后主动比对、显式告警。
    _miss = []
    for _b, _bd in (data.get("楼栋") or {}).items():
        _units = (_bd.get("单元") or {}) if isinstance(_bd, dict) else {}
        _cov_u = coverage.get(_b) or {}
        for _u in _units:
            if _norm_unit_key(_u, _b) not in _cov_u:
                _miss.append("%s/%s" % (_b, _u))
    if _miss:
        log.warning("覆盖范围与解析结果的单元键**对不上**（%d 处，样例：%s）——"
                    "出表时这些单元会被标为『未分配』。请核对 coverage JSON 的键写法。",
                    len(_miss), "、".join(_miss[:6]))

# ---------- 读取模板（可选）：表头与列结构 ----------
# 模板表头 → 内部字段 映射（与输出部分共用，提前定义）
HEADER_ALIASES = {
    "省": "省", "省份": "省", "省/市": "省",
    "市": "市", "城市": "市",
    "区": "区", "县区": "区", "县": "区", "区县": "区", "城区": "区",
    "街道": "街道", "乡镇": "街道", "镇": "街道", "街道/镇": "街道",
    "小区": "小区", "小区名称": "小区", "楼盘": "小区", "楼盘名称": "小区", "小区名": "小区",
    "楼栋": "楼栋", "楼号": "楼栋", "栋号": "楼栋", "楼": "楼栋", "楼栋号": "楼栋",
    "单元": "单元", "单元号": "单元",
    "楼层": "楼层", "层": "楼层",
    "户号": "户号", "房号": "户号", "房间号": "户号", "门牌号": "户号", "室号": "户号",
    "分纤箱编号": "分纤箱编号", "所属分纤箱": "分纤箱编号", "分纤箱": "分纤箱编号", "光分纤箱": "分纤箱编号", "分纤箱号": "分纤箱编号",
    # 标准地址表模板表头（一级~九级）
    "一级": "省", "二级": "市", "三级": "区", "四级": "街道", "五级": "小区",
    "六级": "楼栋", "七级": "单元", "八级": "楼层", "九级": "户号",
    # 分公司列（模板第1列）
    "分公司": "分公司", "分公司名称": "分公司", "公司": "分公司", "分公司(必填)": "分公司",
}

def normalize_header(h):
    """清洗表头（去空白/换行/(必填)后缀），返回归一化后的表头名与映射到的内部字段"""
    h = str(h).strip()
    h = re.sub(r'[\(（]必填[\)）]$', '', h)  # 去掉末尾的"(必填)"或"（必填）"
    return h, HEADER_ALIASES.get(h, None)

template_headers = None
template_floor_fmt = None   # "chinese" = "三层" / None = 保持原样
template_door_fmt = None    # "int" = 101 / None = 保持原样
template_tail_rows = []     # 模板第3行起（AIGC内容标识行等），须原样保留
if args.template:
    def _is_placeholder(val):
        """模板示例行里的占位文本（如 <省> / <分公司名称> / XX小区）不是数据，不得当默认值使用。

        2026-09-12：模板示例行已改为中性占位（原为某项目的实测数据）。
        占位被当成真实地址填进出表结果，属于"把示例当数据"，必须拦住。
        """
        s = str(val).strip()
        if not s:
            return True
        if s.startswith("<") and s.endswith(">"):
            return True
        if re.fullmatch(r"[XxＸ×]{1,}[^\s]*", s):
            return True
        return False

    if args.template.lower().endswith(".xlsx"):
        wb_t = load_workbook(args.template)
        ws_t = wb_t[wb_t.sheetnames[0]]
        template_headers = [c.value if c.value is not None else "" for c in ws_t[1]]
        # 从第2行读取前5级地址默认值（若 --addr 未提供），按表头映射对应列
        # 2026-09-12 修正：同一内部字段可能对应多列（如"三级"与"区县"都映射"区"），
        # 后列空值会覆盖前列非空值。改为"首个非空值优先"，空值不覆盖。
        # 同时：占位文本（<省> 等）一律视为空，避免把模板示例当成数据。
        if ws_t.max_row >= 2:
            addr_cols = ["省", "市", "区", "街道", "小区"]
            addr_vals = []
            for c, h in enumerate(template_headers, start=1):
                _, field = normalize_header(h)
                if field in addr_cols:
                    v = ws_t.cell(2, c).value
                    s = str(v).strip() if v is not None else ""
                    addr_vals.append((field, "" if _is_placeholder(s) else s))
                elif field == "楼层":
                    val = ws_t.cell(2, c).value
                    if val and not _is_placeholder(val) and "层" in str(val):
                        template_floor_fmt = "chinese"
                elif field == "户号":
                    val = ws_t.cell(2, c).value
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        template_door_fmt = "int"
                elif field == "分公司" and args.branch is None:
                    v = ws_t.cell(2, c).value
                    s = str(v).strip() if v is not None else ""
                    if s and not _is_placeholder(s):
                        args.branch = s
            if args.addr is None:
                addr_map = {}
                for _fld, _val in addr_vals:
                    if _val and _fld not in addr_map:  # 首个非空值优先，后列空值不覆盖
                        addr_map[_fld] = _val
                addr_parts_t = [addr_map.get(f, "") for f in addr_cols]
                if any(addr_parts_t):
                    args.addr = ",".join(addr_parts_t)
                    log.info(f"前5级地址取自模板示例行：{args.addr}"
                             f"（注意：这是**模板里的示例值、非本图数据**。"
                             f"要留空请显式传空串 --addr 加一对空引号；"
                             f"要填真实地址请传 --addr 省,市,区,街道,小区）")
                else:
                    log.info("模板示例行为占位文本，未取作前5级地址默认值；请用 --addr 传入真实地址")

        # 模板第3行起（AIGC 内容标识行等）须原样保留到输出（2026-09-11 修正 P1-1）。
        # 旧实现只取第1行表头 + 第2行格式，第3行的 AIGC 标识被整行丢弃。
        if ws_t.max_row >= 3 and template_headers:
            for _r in range(3, ws_t.max_row + 1):
                _vals = [ws_t.cell(_r, _c).value for _c in range(1, len(template_headers) + 1)]
                if any(v is not None and str(v).strip() for v in _vals):
                    template_tail_rows.append(_vals)
    elif args.template.lower().endswith(".xls"):
        try:
            import xlrd
        except ImportError:
            print("读取.xls模板需要 xlrd，请先安装或改用.xlsx")
            sys.exit(1)
        wb_t = xlrd.open_workbook(args.template)
        sheet_t = wb_t.sheet_by_index(0)
        template_headers = [str(sheet_t.cell_value(0, c)) for c in range(sheet_t.ncols)]
        if sheet_t.nrows >= 2:
            addr_cols = ["省", "市", "区", "街道", "小区"]
            addr_map = {}
            for c, h in enumerate(template_headers):
                _, field = normalize_header(h)
                if field in addr_cols:
                    v = str(sheet_t.cell_value(1, c)).strip()
                    if v and field not in addr_map:  # 首个非空值优先，后列空值不覆盖（同 xlsx 分支 2026-09-12 修正）
                        addr_map[field] = v
                elif field == "楼层":
                    val = sheet_t.cell_value(1, c)
                    if val and "层" in str(val):
                        template_floor_fmt = "chinese"
                elif field == "户号":
                    val = sheet_t.cell_value(1, c)
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        template_door_fmt = "int"
                elif field == "分公司" and args.branch is None:
                    v = sheet_t.cell_value(1, c)
                    if str(v).strip():
                        args.branch = str(v).strip()
            if args.addr is None:
                addr_parts_t = [addr_map.get(f, "") for f in addr_cols]
                if any(addr_parts_t):
                    args.addr = ",".join(addr_parts_t)

# 前5级地址
if args.addr:
    addr_parts = [x.strip() for x in re.split(r'[,，]', args.addr)]
else:
    addr_parts = ["", "", "", "", ""]
while len(addr_parts) < 5:
    addr_parts.append("")

def floor_num_local(fl_name):
    """从楼层名提取数字（如 3F→3, -1F→-1），失败返回 None"""
    return floor_num(fl_name, args.floor_pattern)

# NOTE: floor_num_local 保留为本文件包装（调用方较多），但底层已统一到 ftth_common.floor_num。
# gen_addressbook 中需 None 回退（而非 0），故不直接用 floor_num_or_zero。

def bldg_num_local(bldg_name):
    """从楼名提取数字（如 1#楼→1, 2号楼→2），失败返回 0（用于排序）"""
    return bldg_num(bldg_name)

# ---------- 模板格式转换 ----------
# 2026-09-16：`--floor-format` / `--door-format` 显式指定时**优先于模板示例行自动判定**。
#   原先只能靠"改模板工作副本的示例行"来触发中文楼层 / int 户号格式 ——
#   那要求调用方先复制模板、改第 2 行、再喂回来（实测某项目为此多写了一个脚本）。
#   现可直接传参，模板保持原样即可。
if args.floor_format != "auto":
    template_floor_fmt = "chinese" if args.floor_format == "chinese" else None
    log.info("楼层格式由 --floor-format=%s 显式指定（不再依赖模板示例行）" % args.floor_format)
if args.door_format != "auto":
    template_door_fmt = "int" if args.door_format == "int" else None
    log.info("户号格式由 --door-format=%s 显式指定（不再依赖模板示例行）" % args.door_format)

CN_DIGITS = "零一二三四五六七八九"

def num_to_cn(n):
    """正整数转中文数字（用于楼层名，支持1~99）"""
    if n <= 0:
        return str(n)
    if n < 10:
        return CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + CN_DIGITS[n % 10]
    if n < 100:
        tens, ones = n // 10, n % 10
        return CN_DIGITS[tens] + "十" + (CN_DIGITS[ones] if ones else "")
    return str(n)

def floor_to_template(fl_name):
    """将楼层名转换为模板格式（如 3F → 三层, B1 → 地下一层）"""
    fn = floor_num_local(fl_name)
    if fn is None:
        return fl_name
    if fn < 0:
        # 负楼层用中文格式：B1 → 地下一层, B2 → 地下二层
        if template_floor_fmt == "chinese":
            cn = num_to_cn(abs(fn))
            return f"地下{cn}层"
        return fl_name
    if template_floor_fmt == "chinese":
        return f"{num_to_cn(fn)}层"
    return fl_name

def door_to_template(hu):
    """将户号转换为模板格式。

    2026-09-11 修正（P1-2）：统一去掉末尾"室"，并保证负楼层户号不被截断。
      正数层：101室 → 101（模板为数字列时输出 int）
      负楼层：B101室 → B101（含字母，保持字符串；旧实现会原样留下"B101室"，
              与正数层的"101"格式不一致）
    """
    s = str(hu)
    if s.endswith("室"):
        s = s[:-1]
    if template_door_fmt == "int":
        m = re.fullmatch(r'(\d+)', s)
        if m:
            return int(m.group(1))
        return s          # B101 这类含字母的户号不做数字截断
    return s


# ---------- 生成行数据 ----------
def gen_unit_rows(bldg_name, unit_name, unit_data):
    """根据楼层表+覆盖范围生成每户一行"""
    rows = []
    floors = unit_data.get("楼层表", {})
    boxes = unit_data.get("分纤箱", [])

    def fl_sort_key(kv):
        fn = floor_num_local(kv[0])
        return fn if fn is not None else 0

    # 单箱单元：全部分配给该箱
    if len(boxes) == 1:
        box_id = _norm_fx(boxes[0].get("编号", "未分配"))
        for fl, info in sorted(floors.items(), key=fl_sort_key):
            n_hu = info.get("户数")
            if not n_hu:
                continue  # 无户数标注（如 -2F/-1F 地下层）：不生成行（SKILL.md Step 1c：若无户数标注，默认不生成户号）
            for seq in range(1, int(n_hu) + 1):
                rows.append((fl, seq, box_id))
        return rows

    # 多箱单元：按覆盖 JSON 分配
    cov_map = {}
    if coverage and bldg_name in coverage and unit_name in coverage[bldg_name]:
        cov_map = coverage[bldg_name][unit_name]  # {分纤箱: [楼层,...]}
    # 建立 楼层→分纤箱 映射
    floor_to_box = {}
    for box_id, floor_list in cov_map.items():
        for fl in floor_list:
            floor_to_box[fl] = box_id

    for fl, info in sorted(floors.items(), key=fl_sort_key):
        n_hu = info.get("户数")
        if not n_hu:
            continue  # 无户数标注（如 -2F/-1F 地下层）：不生成行
        box_id = floor_to_box.get(fl, "未分配")
        for seq in range(1, int(n_hu) + 1):
            rows.append((fl, seq, box_id))
    return rows


# 组装所有行
all_rows = []
skipped_floors = []     # 2026-09-11 新增：记录被静默丢弃的楼层，用于守恒校验
for bldg_name, bldg_data in sorted(data.get("楼栋", {}).items(), key=lambda x: bldg_num_local(x[0])):
    for unit_name, unit_data in bldg_data.get("单元", {}).items():
        unit_rows = gen_unit_rows(bldg_name, unit_name, unit_data)
        for fl, seq, box_id in unit_rows:
            fn = floor_num_local(fl)
            if fn is None:
                # 无法解析楼层号 → 旧实现直接 continue，整层住户静默消失
                # （实测教训：地下层整层被丢，日志却只报"生成 N 户"，不报丢失）。
                n_hu = (unit_data.get("楼层表", {}).get(fl, {}) or {}).get("户数")
                skipped_floors.append((bldg_name, unit_name, fl, n_hu))
                continue
            # 户号按 cover-rule 生成（先判断 seq is None，避免 None 参与计算）
            if seq is None:
                hu = ""
            elif fn < 0:
                # 负楼层户号：B1层用 B101/B102/... 格式（B+abs(fn)*100+序号）
                base = abs(fn) * 100
                hu = f"B{base + seq}室"
            elif args.cover_rule == "unit":
                hu = f"{unit_name}{fn}0{seq}" if seq < 10 else f"{unit_name}{fn}{seq}"
            else:  # floor100 / floor10
                base = fn * (100 if args.cover_rule == "floor100" else 10)
                hu = f"{base + seq}室"
            all_rows.append(
                {
                    "分公司": args.branch or "",
                    "省": addr_parts[0],
                    "市": addr_parts[1],
                    "区": addr_parts[2],
                    "街道": addr_parts[3],
                    "小区": addr_parts[4],
                    "楼栋": bldg_name,
                    "单元": unit_name,
                    "楼层": floor_to_template(fl),
                    "户号": door_to_template(hu),
                    "分纤箱编号": box_id,
                }
            )

# ---------- 守恒校验（2026-09-11 新增，P0-4 补；2026-09-12 P0-3 重写：三方对账） ----------
# 目的：杜绝"整层住户被静默丢掉、日志却报成功"以及"源户数 0 也能出表"的情况。
src_households = 0
for _b, _bd in (data.get("楼栋", {}) or {}).items():
    for _u, _ud in (_bd.get("单元", {}) or {}).items():
        for _fl, _info in ((_ud or {}).get("楼层表", {}) or {}).items():
            src_households += int((_info or {}).get("户数") or 0)

lost_households = sum(int(n) for *_, n in skipped_floors if n)
output_rows = len(all_rows)

# 统计 INSERT 总数（若 parse JSON 中有 INSERT 数据）
insert_total = 0
insert_assigned = 0
for _b, _bd in (data.get("楼栋", {}) or {}).items():
    for _u, _ud in (_bd.get("单元", {}) or {}).items():
        for _ins in (_ud.get("INSERT", []) or []):
            insert_total += 1
            if _ins.get("归属楼层") is not None:
                insert_assigned += 1

log.info(f"生成 {output_rows} 户（源户数合计 {src_households}，INSERT 已归属 {insert_assigned}/{insert_total}）")

# P0-3 修正：三方对账——源户数、输出行数、INSERT 总数，任一不等即报错
# 1) 楼层号解析失败导致整层丢弃（原有逻辑保留）
if skipped_floors:
    log.error(f"[守恒校验不通过] {len(skipped_floors)} 个楼层因解析不出楼层号被丢弃，涉及 {lost_households} 户：")
    for _s in skipped_floors[:20]:
        log.error(f"    丢弃 {_s[0]} {_s[1]} 楼层={_s[2]!r} 户数={_s[3]}")
    log.error("常见原因：楼层标注写法未被识别（如 B1 / WF / 中文层名）。"
              "可用 --floor-pattern 显式指定，或扩展 ftth_common.parse_floor_label 支持该写法。")
    if not args.allow_lossy:
        log.error("已中止出表。如确认这些楼层可以丢弃，请加 --allow-lossy 强制继续。")
        sys.exit(2)

# 2) 源户数为 0 时报错（P0-3 核心修复：旧实现源户数 0 也能出 141 户且 exit 0）
if src_households == 0 and output_rows > 0:
    log.error(f"[守恒校验不通过] 源户数合计为 0，但生成了 {output_rows} 行——"
              f"可能原因：①无「X户」标注且未传 --hu-pattern；②户数被默认填充（如每层 2 户），"
              f"违反 SKILL.md「户数必须直读，禁止假设默认值」。")
    log.error("已中止出表。请检查 parse JSON 中的楼层表户数字段。")
    sys.exit(2)

# 3) 输出行数与源户数对账（P0-3 核心修复：旧实现不比较输出行数与源户数）
if src_households > 0 and output_rows != src_households:
    log.error(f"[守恒校验不通过] 源户数合计 {src_households} ≠ 输出行数 {output_rows}"
              f"（差 {abs(src_households - output_rows)}）。")
    log.error("可能原因：①部分楼层户数未生成行（检查 skipped_floors）；"
              "②覆盖 JSON 分配导致部分楼层被丢弃；③多箱单元中部分楼层未分配到分纤箱。")
    if not args.allow_lossy:
        log.error("已中止出表。如确认差异可接受，请加 --allow-lossy 强制继续。")
        sys.exit(2)

# ---------- 输出 xlsx ----------
wb = Workbook()
ws = wb.active
ws.title = args.sheet_name

if template_headers:
    headers = []
    field_map = []  # headers[i] -> 内部字段名或None
    for h in template_headers:
        h_clean, field = normalize_header(h)
        headers.append(h_clean)
        field_map.append(field)
else:
    headers = ["分公司", "省", "市", "区", "街道", "小区", "楼栋", "单元", "楼层", "户号", "分纤箱编号"]
    field_map = headers[:]  # 与headers一一对应
ws.append(headers)

for row in all_rows:
    ws.append([row[f] if f else "" for f in field_map])

# 模板尾行（AIGC 内容标识行）原样追加（2026-09-11 修正 P1-1）
# 2026-09-16（防护）：**同类尾行去重**。
#   本脚本按设计会原样保留模板尾行（这是对的）；平台在文件生成后还会再写一条
#   AIGC 标识行（实测某项目产物出现 2 条：模板尾行 + 平台 hook 写入，属正常系统行为）。
#   真正的风险是：**以已含尾行的产物为模板再次出表**时，尾行会逐次累积。
#   故此处按「首列标识前缀」去重，同一前缀只保留第一条，并显式告知跳过了几条。
_seen_tail = set()
_dup_tail = 0
for _tr in template_tail_rows:
    _sig = (str(_tr[0]).split(":")[0].strip() if _tr and _tr[0] is not None else "") or "__blank__"
    if _sig in _seen_tail:
        _dup_tail += 1
        log.warning("模板尾行去重：跳过重复的 %r 行（同一标识前缀已存在）" % _sig)
        continue
    _seen_tail.add(_sig)
    ws.append(_tr)
if _dup_tail:
    log.warning("本次共跳过 %d 条重复模板尾行（通常源于『以已有产物为模板再次出表』）" % _dup_tail)

# 样式：表头蓝底白字，数据区边框
header_font = Font(bold=True, color="FFFFFF", size=11)
header_fill = PatternFill("solid", fgColor="4472C4")
header_align = Alignment(horizontal="center", vertical="center")
thin_border = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)
center = Alignment(horizontal="center", vertical="center")

for c in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=c)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_align
    cell.border = thin_border

for r in range(2, len(all_rows) + 2):
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=r, column=c)
        cell.border = thin_border
        cell.alignment = center

# 列宽
for c in range(1, len(headers) + 1):
    ws.column_dimensions[get_column_letter(c)].width = 12

ws.freeze_panes = "A2"
os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
try:
    wb.save(args.out)
except IOError as e:
    log.error(f"无法保存输出文件: {args.out}\n{e}")
    sys.exit(1)
log.info(f"已保存: {args.out}")

# 回读校验
try:
    wb_check = load_workbook(args.out)
    ws_check = wb_check[args.sheet_name]
    log.info(f"校验: {ws_check.max_row}行 x {ws_check.max_column}列")
    if ws_check.max_row >= 2:
        log.info(f"第2行: {[ws_check.cell(2, c).value for c in range(1, min(10, len(headers)+1))]}")
except Exception as e:
    log.warning(f"回读校验失败（不影响输出）: {e}")