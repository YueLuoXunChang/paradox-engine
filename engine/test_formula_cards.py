# -*- coding: utf-8 -*-
"""
test_formula_cards.py — 正式测试：公式卡与构件的对应关系（防"声明悄悄漂"）
============================================================================
为什么有它：
    第 1 层原本 10 个构件配 10 张公式卡（`docs/formulas/*.md`），后来构件加到
    15 个、卡还是 10 张，而 README 仍写着「第 1 层每构件一张」——**没有任何东西
    守着这条对应**，于是它悄悄漂了（英文 README 的场景数 25 vs 实测 28 也是同一类）。
    本文件把"卡 ↔ 构件"变成不变式：补了构件忘写卡、删了卡忘清引用、把卡写空，
    都会在这里报出来。

查什么（都从**活文件**取，不信任何自述清单）：
    ① 每个第 1 层构件（engine/classical 下非下划线非测试的 .py）都有同名公式卡；
    ② 每张卡的标题写了对应模块名（`# 公式卡：…（<模块名>）`）；
    ③ 每个构件的 docstring 里声明了卡路径（`公式卡：docs/formulas/<模块名>.md`）；
    ④ 没有多余的卡（卡必须对应真实构件）；
    ⑤ 卡不是空壳：标题之外至少有小节，且写了「代码/测试」指向与边界段；
    ⑥ 卡里声明的测试文件真实存在；
    ⑦ README 中英写的公式卡张数与实测一致。
运行：python engine/test_formula_cards.py
"""
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

PASS = 0
_CARD_DIR = os.path.join(_REPO, 'docs', 'formulas')
_L1_DIR = os.path.join(_HERE, 'classical')

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


# ── 实测：第 1 层构件清单 + 卡清单（都从文件系统取）
_MODS = sorted(
    f[:-3] for f in os.listdir(_L1_DIR)
    if f.endswith('.py') and not f.startswith(('test_', '_'))
    and f != '__init__.py')
_CARDS = sorted(f[:-3] for f in os.listdir(_CARD_DIR) if f.endswith('.md'))

print("公式卡 · 正式测试")
print("=" * 60)
print(f"  实测：第 1 层构件 {len(_MODS)} 个 / 公式卡 {len(_CARDS)} 张")

# ── ① 每个构件都有卡
_missing = [m for m in _MODS if m not in _CARDS]
check("每个第 1 层构件都有同名公式卡（补构件别忘补卡）",
      not _missing, f"缺卡：{_missing}")

# ── ② 卡标题写了模块名
_bad_title = []
for m in _MODS:
    if m not in _CARDS:
        continue
    first = _read(os.path.join(_CARD_DIR, m + '.md')).split('\n')[0].strip()
    if not (first.startswith('# 公式卡：') and f'（{m}）' in first):
        _bad_title.append((m, first[:40]))
check("每张卡标题形如「# 公式卡：…（模块名）」（卡与构件对得上）",
      not _bad_title, str(_bad_title))

# ── ③ 每个构件 docstring 里声明了卡路径
_nodesc = []
for m in _MODS:
    src = _read(os.path.join(_L1_DIR, m + '.py'))
    if f'公式卡：docs/formulas/{m}.md' not in src:
        _nodesc.append(m)
check("每个构件都在 docstring 里指向自己的卡（从代码能找到卡）",
      not _nodesc, f"没声明的：{_nodesc}")

# ── ④ 没有多余的卡
_extra = [c for c in _CARDS if c not in _MODS]
check("没有多余的卡（卡必须对应真实构件；不留孤儿卡）",
      not _extra, f"孤儿卡：{_extra}")

# ── ⑤ 卡不是空壳
_thin, _noshape = [], []
for c in _CARDS:
    text = _read(os.path.join(_CARD_DIR, c + '.md'))
    if len(text.strip()) < 400 or text.count('\n## ') < 3:
        _thin.append((c, len(text.strip()), text.count('\n## ')))
    if '代码：' not in text or '测试：' not in text:
        _noshape.append(c)
check("每张卡都写了小节（不是空壳：至少 3 个小节 + 400 字）",
      not _thin, str(_thin))
check("每张卡都写了「代码：」与「测试：」指向（读者能一键找到源头）",
      not _noshape, str(_noshape))

# ── ⑥ 卡里声明的代码/测试文件真实存在
_bad_test, _bad_code = [], []
for c in _CARDS:
    text = _read(os.path.join(_CARD_DIR, c + '.md'))
    m = re.search(r'测试：(engine/\S+\.py)', text)
    if m and not os.path.exists(os.path.join(_REPO, m.group(1))):
        _bad_test.append((c, m.group(1)))
    m2 = re.search(r'代码：(engine/\S+\.py)', text)
    if m2 and not os.path.exists(os.path.join(_REPO, m2.group(1))):
        _bad_code.append((c, m2.group(1)))
check("卡里声明的测试文件都真实存在（不指空）",
      not _bad_test, str(_bad_test))
check("卡里声明的代码文件都真实存在（不指空）",
      not _bad_code, str(_bad_code))

# ── ⑦ README 中英写的张数与实测一致
_n = len(_CARDS)
_zh = _read(os.path.join(_REPO, 'README.md'))
_en = _read(os.path.join(_REPO, 'README.en.md'))
_zh_claim = re.findall(r'公式卡 ×(\d+)', _zh)
# 英文那份把公式卡写成 concept cards (×N …)：两种写法都认，但必须先找得到
_en_claim = (re.findall(r'cards\s*\(×(\d+)', _en)
             + re.findall(r'formula cards? ×(\d+)', _en))
check("中文 README 的公式卡张数与实测一致",
      bool(_zh_claim) and all(int(x) == _n for x in _zh_claim),
      f"实测 {_n}，README 写 {_zh_claim}")
check("英文 README 的公式卡张数与实测一致（英文那份也要守）",
      bool(_en_claim) and all(int(x) == _n for x in _en_claim),
      f"实测 {_n}，README.en 写 {_en_claim}")

print("=" * 60)
print(f"结果: {PASS}/10 通过")
raise SystemExit(0 if PASS == 10 else 1)
