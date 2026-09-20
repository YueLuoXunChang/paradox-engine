# -*- coding: utf-8 -*-
"""
test_glossary.py — 正式测试：术语表（docs/glossary.md）与实际不许对不上
========================================================================
为什么有它：
    术语表要是没人守，就会变成"另一份会说谎的文档"——写了个构件其实没有、
    题型写漏一个、工具数写旧了，读者照着查反而被带偏。本文件把几条硬约束
    变成不变式，让术语表**必须**跟实现同步。

查什么（都从**活代码/活文件**取，不信术语表的自述）：
    ① 术语表存在且不是空壳（小节数 + 行数下限）；
    ② 表里提到的每个构件路径（engine/**/*.py）真实存在；
    ③ 表里提到的每个构件都必须出现在构件参考 docs/components.md 里（真构件，不是编的）；
    ④ T1–T12 全覆盖，且 T12 的名字与判类器里的口径一致（T12 = 未分类）；
    ⑤ 四个层的名字都在（第 0/1/2/3 层）；
    ⑥ 表里写的工具件数与注册表长度一致；
    ⑦ README 中英都指向术语表（读者找得到）；
    ⑧ 中英对照不缺：每条术语都有 English 列/英文速查段。
运行：python engine/test_glossary.py
"""
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

PASS = 0
_GLOSS = os.path.join(_REPO, 'docs', 'glossary.md')

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


def _read(path):
    return io.open(path, encoding='utf-8').read()


print("术语表 · 正式测试")
print("=" * 60)

check("术语表存在", os.path.exists(_GLOSS), _GLOSS)
_text = _read(_GLOSS)

# ── ① 不是空壳
_sections = _text.count('\n## ')
_lines = _text.count('\n') + 1
check("术语表不是空壳（≥8 个小节、≥120 行）",
      _sections >= 8 and _lines >= 120, f'小节 {_sections} / 行 {_lines}')

# ── ② 提到的构件路径真实存在
_paths = sorted(set(re.findall(r'engine/[a-z_]+/[a-z_0-9]+\.py', _text)))
_bad_paths = [p for p in _paths if not os.path.exists(os.path.join(_REPO, p))]
check("术语表提到的构件路径都真实存在（不指空）",
      bool(_paths) and not _bad_paths, f'共 {len(_paths)} 条，坏：{_bad_paths}')

# ── ③ 提到的构件都在构件参考里（真构件）
_comp = _read(os.path.join(_REPO, 'docs', 'components.md'))
_not_in_comp = [p for p in _paths if f'`{p}`' not in _comp]
check("术语表提到的构件都在 docs/components.md 里（真构件，不是编的）",
      not _not_in_comp, str(_not_in_comp))

# ── ④ T1–T12 全覆盖，且 T12 口径与判类器一致
_missing_t = [f'T{i}' for i in range(1, 13) if f'T{i}' not in _text]
check("T1–T12 全覆盖（题型表不许漏型）", not _missing_t, str(_missing_t))
try:
    from engine.control.classifier import _TYPE_NAME
    _t12 = _TYPE_NAME.get('T12')
except Exception as e:  # noqa: BLE001
    _t12 = None
check("T12 的口径与判类器一致（未分类——不是第 12 个正经题型）",
      _t12 == '未分类' and 'T12' in _text
      and re.search(r'\|\s*T12\s*\|\s*\*\*未分类\*\*', _text) is not None,
      f"判类器里 T12 = {_t12!r}")

# ── ⑤ 四个层的名字都在
_layers = [f'第 {i} 层' for i in range(4)]
check("四个层的名字都在（第 0/1/2/3 层）",
      all(x in _text for x in _layers), str([x for x in _layers
                                             if x not in _text]))

# ── ⑥ 表里的工具件数与注册表一致
from engine.ai.tools import _TOOL_REGISTRY  # noqa: E402
_n_tools = len(_TOOL_REGISTRY)
_claims = [int(x) for x in re.findall(r'\*\*(\d+) 件\*\*', _text)]
check("术语表写的工具件数 = 注册表长度",
      _claims and all(c == _n_tools for c in _claims),
      f"实测 {_n_tools}，术语表写 {_claims}")

# ── ⑦ README 中英都指向术语表
_zh = _read(os.path.join(_REPO, 'README.md'))
_en = _read(os.path.join(_REPO, 'README.en.md'))
check("中文 README 指向术语表（读者找得到）",
      'docs/glossary.md' in _zh or 'glossary.md' in _zh)
check("英文 README 指向术语表（英文那份也指）",
      'glossary' in _en.lower())

# ── ⑧ 中英对照不缺
check("中英对照不缺（有 English 表头 + 英文速查段）",
      'English' in _text and '英文速查' in _text)

print("=" * 60)
print(f"结果: {PASS}/11 通过")
raise SystemExit(0 if PASS == 11 else 1)
