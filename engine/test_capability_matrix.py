# -*- coding: utf-8 -*-
"""
test_capability_matrix.py — 正式测试：能力矩阵（docs/capability_matrix.md）
================================================================================
为什么有它：能力矩阵是"**要不要把新机制接进路由**"这件事的数据面，它必须与活代码一致
（路由表改了、构件增删了，矩阵得跟着变）。做法与 `test_components_doc.py` 同款：
**从活代码重算一遍，与文档逐项比对**——漂移即红。

查什么：
    ① 生成物存在，且与生成器输出**逐字节一致**（漂移检查）；
    ② 12 个题型都有小节；
    ③ 文档里"路由里的构件名"与 `classifier.ROUTE` 重算的一致；
    ④ 文档第三节列出的未接线工具集合 == 机器重算的集合（不漏不多）；
    ⑤ 小结里的三个数字（路由条目数 / 未接线机制件数 / 引擎自身件数）与重算一致；
    ⑥ 路由表里出现的每个构件名都能落到一个真实构件文件或一个真实层上（不许指向空气）。

运行：python engine/test_capability_matrix.py
"""
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

from engine import _capability_matrix as cm  # noqa: E402

PASS = 0
try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("能力矩阵 · 正式测试")
print("=" * 60)

doc = io.open(cm.DOC, encoding='utf-8').read() if os.path.exists(cm.DOC) else ''
check("能力矩阵文件存在", bool(doc), cm.DOC)

route, type_name = cm._router()
tools = cm._tools()
routed = cm._routed_modules(route)
sums = cm._summaries()

# ① 逐字节漂移检查
check("★矩阵与生成器输出一致（改了代码忘了重生成会失败）",
      doc == cm.render(), '跑 python engine/_capability_matrix.py --write')

# ② 题型小节齐全
miss = [t for t in type_name if ('## %s' % t not in doc)]
check("12 个题型都有小节", not miss, miss)

# ③ 路由里的构件名
doc_routed = set()
m = re.search(r'- 路由里的构件名：\*\*(\d+)\*\* 个', doc)
check("小结里的路由构件名条数与重算一致",
      m and int(m.group(1)) == len(routed), (m.group(1) if m else None,
                                             len(routed)))

# ④ 未接线清单逐项比对
listed = set(re.findall(r'^\| `([a-z_0-9]+)` \| (?:cold|classical|mechanisms|'
                        r'skeleton|scenarios|ai|\(root\)) \|', doc, re.M))


def _wired(name):
    modpath, leaf, _d = tools[name]
    if leaf in routed:
        return True
    return any(modpath.startswith(rn + '.') for rn in routed)


want = {n for n in tools if not _wired(n)}
from engine.ai.tools import _TOOL_REGISTRY  # noqa: E402
from engine.ai.tools import _TOOL_REGISTRY as _reg  # noqa: E402
# 引擎自身（control 层）不列进第三节，按层剔掉
self_names = set()
for name, modpath, _d in _reg:
    leaf = modpath.split('.')[-1]
    layer = sums.get(leaf, (None, None, '?'))[2]
    if layer == 'control':
        self_names.add(name)
want_public = want - self_names
check("★未接线清单 == 机器重算（不漏不多）", listed == want_public,
      '只在文档: %s；只在代码: %s' % (sorted(listed - want_public)[:4],
                                 sorted(want_public - listed)[:4]))

# ⑤ 小结数字
m2 = re.search(r'没接线的机制件 (\d+) 件', doc)
m3 = re.search(r'另有 \*\*(\d+)\*\* 件属于引擎自身', doc)
m4 = re.search(r'路由表条目：\*\*(\d+)\*\* 条', doc)
check("小结的未接线件数一致", m2 and int(m2.group(1)) == len(want_public),
      (m2.group(1) if m2 else None, len(want_public)))
check("小结的引擎自身件数一致", m3 and int(m3.group(1)) == len(self_names),
      (m3.group(1) if m3 else None, len(self_names)))
check("小结的路由条目数一致", m4 and int(m4.group(1)) == len(route),
      (m4.group(1) if m4 else None, len(route)))

# ⑥ 路由名都能落地（真构件文件或真层）
bad = []
for rn in routed:
    ok = bool(sums.get(rn)) or any(l == rn for l in sums) or \
        any(str(v[0]).startswith('engine/%s/' % rn) for v in sums.values())
    if not ok:
        bad.append(rn)
check("路由表里每个构件名都能落到真实构件上", not bad, bad)

print("=" * 60)
print(f"结果: {PASS}/9 通过")
raise SystemExit(0 if PASS == 9 else 1)
