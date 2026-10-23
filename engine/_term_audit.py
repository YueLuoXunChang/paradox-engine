# -*- coding: utf-8 -*-
"""_term_audit.py — ④ 轴「撞名与同名不同物**一律标注**」的机械核查

做什么：
    扫全部构件的 `PORTS['out']`，找出**同一个字段名出现在 ≥2 件**的撞名，
    给出三样东西：
        ① 每个名字被哪些件用、各自声明什么类型；
        ② **同型/不同型**（不同型 = 至少两种载体，是"同名不同物"的高危信号）；
        ③ 人工判定：`JUDGMENTS[name] = (是否同一物, 一句话理由)`。

规矩（④ 轴从严）：
    **不同型的撞名必须有判定**——`--check` 遇到"没判定"的不同型撞名会**报错**；
    同型撞名只报数（默认视为同物，但仍列出来供人一眼扫）。

用法：
    python engine/_term_audit.py --write   # 写 docs/term_collisions.md
    python engine/_term_audit.py --check   # 门禁：不同型撞名是否都有判定
    python engine/_term_audit.py           # 打印摘要
"""
import collections
import importlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

OUT = os.path.join(os.path.dirname(HERE), 'docs', 'term_collisions.md')

# 判定表：不同型撞名**必须**在这里有一条（是否同一物 + 理由）。
# True = 同一物（承载方式不同但语义一致）；False = 同名不同物（必须标注清楚）。
JUDGMENTS = {
    'verdict': (True, '统一判词："这件给出什么结论"——48 件同义，词表见术语表'),
    'boundary': (True, '边界声明："本层承诺/不承诺什么"——形态统一'),
    'counterexample': (False, 'presburger=反例算术式 · propositional=赋值 · '
                              'many_valued=真值指派 · relevance=反模型：'
                              '都是"反例"但**载体不同**'),
    'value': (False, 'belnap_four=四值真值 · intuitionistic=节点真值 · '
                     'many_valued=n 值真值：**载体不同**'),
    'annotation': (False, 'paradox_annotate=8 字段卡 · selfref_fixpoint=结论注记 · '
                          'wall_pipeline=6 字段卡：**卡形状不同**'),
    'changed': (False, 'freeze_tool_schema=契约漂移条目 · review_marks=审核状态变更：'
                       '**含义不同**'),
    'level': (False, 'decidability_map=可判定层级 · classifier=分级（P-A/B/C）：**不同**'),
    'equivalent': (False, 'presburger=公式等价 · bisimulation=互模拟等价：**关系不同**'),
    'route': (False, 'classifier=判定路径 · clue_suggester=管线路线：**不同**'),
    'report': (False, 'controller=五查报告 · scenarios=场景报告：**形态不同**'),
    'branch': (False, 'converge_check=收敛分支名（压缩/有限步/渐进/振荡）· '
                      'paradox_measure=测度分支名（mu1–mu4）：**命名空间撞车**'),
    'scenes': (False, 'corpus_stats=统计用场景集 · scenarios=场景库：**不同集合**'),
    'matrix': (False, 'interval_algebra=区间关系矩阵 · corpus_stats=统计矩阵：**不同**'),
    'types': (False, 'classifier=分类类型 · corpus_stats=统计类型：**不同**'),
    'components': (False, 'dung_framework=攻击图**连通分量** · clue_suggester=管线构件：'
                          '**同名不同物**（图论量 vs 系统模块）——注意两者**同型**（都是 list），'
                          '类型检查看不出来，靠本判定'),
    'review': (False, 'corpus_stats=审核汇总 dict · review_marks=审核状态串'
                      '（ok/wrong/edge/pending）：**载体不同**'),
}


def _base_type(decl):
    """把 'list[dict]?' / 'float?' 之类归一成基类型（list/dict/float/…）。"""
    s = str(decl).strip().rstrip('?').strip()
    for sep in ('[', '（', '(', '：', ':'):
        s = s.split(sep)[0]
    return s.strip().lower() or '?'


def _mods():
    for th in ('skeleton', 'classical', 'mechanisms', 'cold', 'control', 'engine',
               'ai', 'scenarios'):
        d = os.path.join(HERE, th)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.py') and not f.startswith(('_', 'test_')) \
                    and f != '__init__.py':
                yield th, f[:-3]


def collisions():
    """返回 {字段名: [(层, 件, 声明原文, 基类型)]}，只保留 ≥2 件的名字。"""
    by = collections.defaultdict(list)
    for layer, name in _mods():
        try:
            m = importlib.import_module('engine.%s.%s' % (layer, name))
        except Exception:                          # noqa: BLE001
            continue
        ports = getattr(m, 'PORTS', None) or {}
        for k, v in (ports.get('out') or {}).items():
            by[k].append((layer, name, str(v), _base_type(v)))
    return {k: v for k, v in by.items() if len(v) >= 2}


def audit():
    """返回 (rows, problems)。rows 按撞名件数降序。"""
    cols = collisions()
    rows, problems = [], []
    for name, entries in sorted(cols.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        types = {e[3] for e in entries}
        mixed = len(types) > 1
        judged = JUDGMENTS.get(name)
        if mixed and judged is None:
            problems.append((name, '不同型撞名**没有判定**——④ 轴要求一律标注'))
        rows.append({'name': name, 'n': len(entries), 'entries': entries,
                     'types': sorted(types), 'mixed': mixed,
                     'judgment': judged})
    return rows, problems


def render(rows, problems):
    L = ['# 撞名登记（④ 轴：同名不同物一律标注）', '',
         '由 `engine/_term_audit.py --write` 自动生成；判定表在脚本的 `JUDGMENTS`。', '',
         '口径：把全部构件的 `PORTS["out"]` 字段名撞在一起；**不同型 = 同名不同物的高危信号**，',
         '必须在本表有判定（同物/不同物 + 理由）。', '',
         '共 **%d** 个撞名 · 其中**不同型 %d 个** · 未判定 **%d 个**。'
         % (len(rows), sum(1 for r in rows if r['mixed']), len(problems)), '']
    if problems:
        L += ['## 未判定（必须补）', '']
        for n, why in problems:
            L.append('- ❌ `%s`：%s' % (n, why))
        L.append('')
    L += ['## 不同型撞名（逐条判定）', '',
          '| 字段 | 件数 | 类型 | 判定 | 理由 |', '|---|---|---|---|---|']
    for r in rows:
        if not r['mixed']:
            continue
        ok, why = r['judgment'] if r['judgment'] else (None, '（未判定）')
        tag = '同物' if ok is True else ('**不同物**' if ok is False else '?')
        L.append('| `%s` | %d | %s | %s | %s |'
                 % (r['name'], r['n'], '/'.join(r['types']), tag, why))
    L += ['', '## 同型撞名（默认同物，仍列出供扫）', '']
    for r in rows:
        if r['mixed']:
            continue
        line = ('- `%s` × %d：%s'
                % (r['name'], r['n'], '、'.join('%s/%s' % (e[0], e[1])
                                                for e in r['entries'])))
        j = r['judgment']
        if j is not None and j[0] is False:
            line += '\n  - ⚠ **已判定为同名不同物**（同型看不出来）：%s' % j[1]
        elif j is not None:
            line += '\n  - 判定为同物：%s' % j[1]
        L.append(line)
    L += ['', '## 各件明细（不同物者重点看）', '']
    for r in rows:
        if not r['mixed']:
            continue
        L.append('### `%s`' % r['name'])
        for layer, name, decl, base in r['entries']:
            L.append('- `engine/%s/%s.py`：`%s`（基类型 %s）' % (layer, name, decl, base))
        L.append('')
    return '\n'.join(L) + '\n'


def _print(rows, problems):
    print('撞名登记：共 %d 个名字 · 不同型 %d 个 · 未判定 %d 个'
          % (len(rows), sum(1 for r in rows if r['mixed']), len(problems)))
    for n, why in problems:
        print('  ❌ %s：%s' % (n, why))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows, problems = audit()
    if '--write' in argv:
        md = render(rows, problems)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, 'w', encoding='utf-8', newline='').write(md)
        print('已写出 docs/term_collisions.md（%d 字）' % len(md))
        _print(rows, problems)
        return 0 if not problems else 1
    if '--check' in argv:
        _print(rows, problems)
        if problems:
            return 1
        print('✅ 不同型撞名全部有判定')
        return 0
    _print(rows, problems)
    return 0 if not problems else 1


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:                              # noqa: BLE001
        pass
    raise SystemExit(main())
