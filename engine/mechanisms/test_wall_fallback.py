# -*- coding: utf-8 -*-
"""test_wall_fallback.py — 撞墙管线的兜底枝纪律（③ 验证轴 · 第八批）

为什么要有这份文件：
    `wall_pipeline` 是"五选一诊断"的编排件——**判定树最怕的就是兜底枝**。
    规程里点名的历史事故正是这一类："判定树要有兜底取值，否则'一条都不匹配'
    就落空"。本件的问题更刁钻：**兜底枝在，但兜底值在说谎**——

        旧版 2.3 钻墙在"没匹配到自指关键词"时，默认拿一个翻转函数
        （`lambda x: not x`）跑一遍；那必然给出周期 2，于是**任何普通输入
        都被报成 `resonance_selfref`（共振带自指）**。
        实测：`wall='随便一个说法'` → `resonance_selfref`（把普通输入说成悖论型自指）。

本文件把四条纪律钉住：
    ① **兜底不落空**：任何输入都要给出声明集合里的判词，不许 None、不许抛异常；
    ② **兜底不说谎**：非自指输入**不许**被判进自指谱系（共振带/良性/结构性/发散）；
    ③ **可选步要如实 skip**：2.3 没真跑就标 skip，不假装跑过（它 boundary 的承诺）；
    ④ **声明过的判词要有人能走到**：逐个点名"哪些可达、哪个目前不可达"。

运行：python engine/mechanisms/test_wall_fallback.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.mechanisms import wall_pipeline as WP   # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=''):
    global PASS
    if cond:
        PASS += 1
        print('✅ %s' % label)
    else:
        print('❌ %s  %s' % (label, detail))


DECLARED = {'input_pending', 'benign_selfref', 'resonance_selfref',
            'divergent_wall', 'structural_wall', 'creatable',
            'decidable_elsewhere'}
SELFREF_FAMILY = {'benign_selfref', 'resonance_selfref', 'divergent_wall',
                  'structural_wall'}

# 输入表（垃圾/空/极短/超长/只有一半线索/含关键词）
TABLE = [
    ({}, '全空'),
    ({'wall': '随便一个说法'}, '只有无关 wall'),
    ({'wall': '随便一个说法', 'thesis': '正面', 'antithesis': '反面'}, '无关 wall + 对立'),
    ({'thesis': '正面', 'antithesis': '反面'}, '只有对立（无 wall）'),
    ({'wall': ''}, 'wall 是空串'),
    ({'wall': ' '}, 'wall 是空格'),
    ({'wall': '这句话是假的'}, '说谎者'),
    ({'wall': '本句为真'}, '真话者'),
    ({'wall': '本命题不可证'}, '哥德尔型'),
    ({'wall': '自己在说自己'}, '有自指味但非内置句'),
    ({'wall': '假'}, '只有"假"字'),
    ({'wall': '堵' * 2000}, '超长无关文本'),
    ({'wall': '扩容反而更堵', 'thesis': '修路', 'antithesis': '不修路'}, '扩容悖论'),
]

print('=' * 70)
print('一、兜底不落空：任何输入都要给出声明集合里的判词（不许 None/异常）')
_bad, _err, _seen = [], [], set()
for _inp, _tag in TABLE:
    try:
        _r = WP.run(dict(_inp))
    except Exception as _exc:                              # noqa: BLE001
        _err.append((_tag, type(_exc).__name__))
        continue
    _v = _r.get('verdict')
    _seen.add(_v)
    if _v not in DECLARED:
        _bad.append((_tag, _v))
check('十三条输入全部给出**声明集合内**的判词（含垃圾/空/超长）', _bad == [],
      _bad)
check('一条都不许抛异常（判定树不许炸）', _err == [], _err)
check('实际走到的判词有 %d 种：%s' % (len(_seen), sorted(_seen)),
      len(_seen) >= 4)

print()
print('=' * 70)
print('二、★兜底不说谎：非自指输入不许被判进自指谱系')
_SELFREF_HINTED = ('这句话', '本句', '不可证', '自己', '假')
_lied = []
for _inp, _tag in TABLE:
    _r = WP.run(dict(_inp))
    _wall = _inp.get('wall') or ''
    _has_hint = any(k in _wall for k in _SELFREF_HINTED)
    if not _has_hint and _r['verdict'] in SELFREF_FAMILY:
        _lied.append((_tag, _wall[:12], _r['verdict']))
check('六条**无自指线索**的输入，一条都没被判进自指谱系'
      '（旧版这里会把"随便一个说法"报成 resonance_selfref）',
      _lied == [], _lied[:2])
check('对照：真自指句仍然判进谱系（说谎者→resonance_selfref，'
      '没被"一刀切 skip"误伤）',
      WP.run({'wall': '这句话是假的'})['verdict'] == 'resonance_selfref'
      and WP.run({'wall': '本命题不可证'})['verdict'] == 'structural_wall'
      and WP.run({'wall': '本句为真'})['verdict'] == 'benign_selfref')
check('无关输入落到诚实分支：给了对立 → creatable；只给 wall → decidable_elsewhere',
      WP.run({'wall': '随便一个说法', 'thesis': '正面',
              'antithesis': '反面'})['verdict'] == 'creatable'
      and WP.run({'wall': '随便一个说法'})['verdict'] == 'decidable_elsewhere')

print()
print('=' * 70)
print('三、可选步如实 skip（不假装跑过）')
_skip_ok, _run_ok = [], []
for _inp, _tag in TABLE:
    _r = WP.run(dict(_inp))
    if not _r['steps']:
        continue
    _d = _r['steps'][2]
    _fv = _r['diagnosis'].get('drill')
    if _d['status'] == 'skip' and str(_fv).startswith('skip'):
        _skip_ok.append(_tag)
    elif _d['status'] == 'run' and _fv in ('liar_cycle', 'fixed_point',
                                           'annotated_pa',
                                           'resonance_band', 'diverge'):
        _run_ok.append(_tag)
check('2.3 的状态与判词自洽：skip 时 drill 也是 skip；run 时 drill 是修正序列判词'
      '（skip %d 例 · run %d 例）' % (len(_skip_ok), len(_run_ok)),
      len(_skip_ok) + len(_run_ok) == len([t for t in TABLE
                                           if WP.run(dict(t[0]))['steps']]))
check('无关 wall 的 2.3 明确标 skip 并说明"不拿默认函数顶替"',
      '不拿默认函数顶替' in str(WP.run({'wall': '随便一个说法'})['steps'][2]))
check('boundary 承诺"可选步缺输入则 skip——不假装跑过"仍在',
      '不假装跑过' in WP.run({'wall': '这句话是假的'})['boundary'])

print()
print('=' * 70)
print('四、声明过的判词：逐个点名可达性')
check('六种判词实测可达（input_pending/creatable/decidable_elsewhere/'
      'resonance_selfref/structural_wall/benign_selfref）',
      {'input_pending', 'creatable', 'decidable_elsewhere',
       'resonance_selfref', 'structural_wall',
       'benign_selfref'} <= _seen
      and 'divergent_wall' not in _seen,
      sorted(_seen))
check('★`divergent_wall` 目前**无路径可达**（三条内置句只给 liar_cycle/'
      'fixed_point/annotated_pa；修掉假兜底后连"假发散"也没了）'
      '——本件仍声明着它，属于"声明了但接不上"，改内置句时要同步这条',
      'divergent_wall' not in _seen)
check('关键词口径：能映射到内置句 ⇒ 宽口径"有自指味"也必为真（两套口径同源）',
      all(WP._looks_selfref(w) for w in
          ('这句话是假的', '本句为真', '本命题不可证', '自己在说自己'))
      and WP._selfref_sentence('自己在说自己') is None
      and WP._selfref_sentence('本句为真') == 'truth_teller')

print()
print('=' * 70)
print('五、变异接受：把识别函数改回"总是匹配说谎者"，第二条判据必须抓住')
_orig = WP._selfref_sentence
WP._selfref_sentence = lambda wall: 'liar'          # 模拟旧版的顶替行为
try:
    _mut_lied = [t for t, _tag in ((WP.run(dict(i))['verdict'], tag)
                                   for i, tag in TABLE)
                 if t in SELFREF_FAMILY]
    _caught = len(_mut_lied) > 4
finally:
    WP._selfref_sentence = _orig
check('变异接受：顶替成"一律说谎者"后，自指谱系判词数量暴涨（对拍有咬合力）'
      '（%d 例）' % len(_mut_lied), _caught)
check('变异已还原（_selfref_sentence 与原来同一个函数）',
      WP._selfref_sentence is _orig)

print()
print('=' * 70)
print(f'结果: {PASS}/14 通过')
raise SystemExit(0 if PASS == 14 else 1)
