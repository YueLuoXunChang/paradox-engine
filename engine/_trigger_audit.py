# -*- coding: utf-8 -*-
"""
_trigger_audit.py — 触发实测（钝点定位）：谁"排进了管线"却"从没真跑"
========================================================================
为什么有它：能力矩阵登记的是**接线状态**——只保证"材料会被送到"，**不保证送过去能跑起来**。
实测（2026-09-21）发现：默认管线里有的构件在 28 个真实场景上**一次都没真跑**（每次都以
`missing_input` 收场），"线索触发补跑"那批更是一件都没被真触发过。这两种"看起来接了、
其实空转"的状态，矩阵的口径盖不住——**所以要有一张"候选集 × 触发集"的表**。

口径（写进产物，免得被误读）：
    - **候选集** = 该构件被**排进管线**的场景数（判类器认为该跑它）；
    - **触发集** = 其中 **status=='run'** 的场景数（真跑起来了）；
    - **钝点** = 候选 > 0 而触发 == 0（排了，一次没真跑）；
    - **半空转** = 0 < 触发 < 候选；
    - **全触发** = 触发 == 候选 > 0。
    ★ 三者都是**对当前语料**的实测，不是构件的性质：材料不给结构化线索，谁都跑不起来。
    所以本表**不许当"构件好不好用"的判据**读，只当"接线到不到位"的判据读。

用法：
    python engine/_trigger_audit.py           # 打印
    python engine/_trigger_audit.py --write   # 落盘 docs/trigger_audit.md
    python engine/_trigger_audit.py --check   # 与现有文件比对（漂移即非零退出）
"""

import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
DOC = os.path.join(_REPO, 'docs', 'trigger_audit.md')

if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _audit():
    """跑一遍真实语料，算候选集 / 触发集 / 判定。只读，不改场景表。"""
    from scenarios import scenarios as sc
    from control.controller import CLUE_SUPPLEMENT

    rows = sc.run_all()
    cand, fired, stuck_reason = {}, {}, {}
    for r in rows:
        for e in r.get('execution', []):
            comp, status = e['component'], e['status']
            cand.setdefault(comp, set()).add(r['id'])
            if status == 'run':
                fired.setdefault(comp, set()).add(r['id'])
            else:
                # 记"没跑起来"的原因（取该构件首次出现的那个状态）
                stuck_reason.setdefault(comp, status)
    sup = [(c, list(t), w) for c, t, w in CLUE_SUPPLEMENT]
    return rows, cand, fired, stuck_reason, sup


def _verdict(n_cand, n_fire):
    if n_cand > 0 and n_fire == 0:
        return '钝点'
    if 0 < n_fire < n_cand:
        return '半空转'
    if n_fire == n_cand and n_cand > 0:
        return '全触发'
    return '未出现'


def render():
    rows, cand, fired, stuck, sup = _audit()
    types = {}
    for r in rows:
        types[r['expect_type']] = types.get(r['expect_type'], 0) + 1

    L = []
    L.append('# 触发实测（钝点定位）：候选集 × 触发集')
    L.append('')
    L.append('> 本文件由 `python engine/_trigger_audit.py` 从**真实语料**自动生成'
             '（`engine/scenarios` 全库，跑控制器五步流水线 + 线索触发补跑），请勿手改；'
             '漂移检查见 `engine/test_trigger_audit.py`。')
    L.append('>')
    L.append('> **口径**：**候选集** = 被判类器**排进管线**的场景数；**触发集** = 其中 '
             '`status==run`（真跑起来）的场景数。**钝点** = 排了却一次没真跑；'
             '**半空转** = 跑了但没跑满候选；**全触发** = 跑满。')
    L.append('>')
    L.append('> **★ 读法警告**：三者都是**对当前语料**的实测，**不是构件的性质**——'
             '材料不给结构化线索，任何构件都跑不起来。本表只回答"接线到不到位"，'
             '**不许当"构件好不好用"读**。')
    L.append('')
    L.append('## 一、语料（实测）')
    L.append('')
    L.append('- 场景数：**%d**' % len(rows))
    L.append('- 题型分布：%s' % '、'.join('%s×%d' % (k, types[k])
                                          for k in sorted(types)))
    L.append('')
    L.append('## 二、逐件触发表（候选集 → 触发集）')
    L.append('')
    L.append('| 构件 | 候选（被排进管线） | 触发（真跑） | 没跑起来的原因 | 判定 |')
    L.append('|---|---:|---:|---|---|')
    order = sorted(cand, key=lambda c: (-len(cand[c]), c))
    for c in order:
        n_c, n_f = len(cand[c]), len(fired.get(c, ()))
        L.append('| `%s` | %d | %d | %s | %s |'
                 % (c, n_c, n_f, stuck.get(c, '—'), _verdict(n_c, n_f)))
    L.append('')
    L.append('## 三、三态小结（机器算）')
    L.append('')
    groups = {'钝点': [], '半空转': [], '全触发': []}
    for c in order:
        v = _verdict(len(cand[c]), len(fired.get(c, ())))
        if v in groups:
            groups[v].append(c)
    for k in ('钝点', '半空转', '全触发'):
        names = groups[k]
        L.append('- **%s %d 件**：%s'
                 % (k, len(names), '、'.join('`%s`' % n for n in names) or '—'))
    L.append('')
    L.append('## 四、线索触发补跑：挂在哪些题型、真跑几次')
    L.append('')
    L.append('| 构件 | 适用题型 | 该题型本库材料数 | 真跑次数 | 说明 |')
    L.append('|---|---|---:|---:|---|')
    for comp, tps, why in sup:
        avail = sum(types.get(t, 0) for t in tps)
        n_f = len(fired.get(comp, ()))
        if n_f == 0 and avail > 0:
            note = '题型有材料，但材料没带它要的结构化线索'
        elif n_f == 0:
            note = '该题型本库无材料'
        else:
            note = '已真跑'
        L.append('| `%s` | %s | %d | %d | %s |'
                 % (comp, ' · '.join(tps), avail, n_f, note))
    L.append('')
    L.append('## 五、小结（机器算）')
    L.append('')
    n_dead = len(groups['钝点'])
    n_half = len(groups['半空转'])
    n_sup_dead = sum(1 for c, t, _w in sup
                     if len(fired.get(c, ())) == 0
                     and sum(types.get(t2, 0) for t2 in t) > 0)
    L.append('- 出现在语料里的构件：**%d** 件；其中 钝点 **%d** · 半空转 **%d** · 全触发 **%d**'
             % (len(cand), n_dead, n_half, len(groups['全触发'])))
    L.append('- 线索触发补跑 **%d** 件里，**%d 件**在"题型有材料"的前提下真跑 **0** 次'
             % (len(sup), n_sup_dead))
    L.append('- ⚠️ 这不是"构件坏了"，是**材料侧没给结构化线索**：要让它真跑，得先有带线索的材料'
             '（或改接线口径）——**要不要改属作者设计权**。')
    L.append('')
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    text = render()
    if '--write' in argv:
        io.open(DOC, 'w', encoding='utf-8', newline='\n').write(text)
        print('已写出 %s（%d 字）'
              % (os.path.relpath(DOC, _REPO).replace('\\', '/'), len(text)))
        return 0
    if '--check' in argv:
        have = io.open(DOC, encoding='utf-8').read() if os.path.exists(DOC) else ''
        if have != text:
            print('触发实测与语料现状不一致（跑 --write 更新）')
            return 1
        print('触发实测一致')
        return 0
    print(text)
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
