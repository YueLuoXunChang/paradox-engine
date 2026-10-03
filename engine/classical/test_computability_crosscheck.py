# -*- coding: utf-8 -*-
"""test_computability_crosscheck.py — 可计算族互验（③ 验证轴 · 第四批）

为什么要有这份文件：
    `turing_machine`（模拟图灵机）· `recursion_theorem`（自指程序的构造）·
    `lambda_calculus`（λ 项归约）三件都在讲"计算是什么"，但各自实现、各有各的错法。
    本文件按**形式定义**另写独立 oracle 去夹它们——闸三：工具不可自证；
    对拍有信息量，就靠"两边不是同一份实现"。

本文件目前覆盖：**图灵机 ↔ 自写模拟器**（oracle T）。

    oracle T 照 δ: Q×Γ → Q×Γ×{L,R} 的定义重写一份模拟器（不 import 构件的 simulate），
    用随机 2 符号 3 状态机器 × 随机输入对拍：**判词 + 终止配置（纸带/读写头）**都要一致。

判据与约定：
    · 两边都是**确定性模拟** → 要求**精确一致**；
    · 非停机一律报"步数用尽"（诚实：模拟器不判"永不停"）；
    · 未定义转移 → `halt_undefined`（不是"拒绝"，也不是静默停机）；
    · 构件在"卡住"那一格会**多留一行轨迹**（卡住也留痕）——这是它的留痕约定，
      对拍时按约定扣掉，不当分歧；
    · 构件的 `run` 只回传**末尾 5 行**轨迹（白箱够用），所以比"步数"要另想办法——
      本文件比**终止配置**（末行的纸带字符串）而不是比行数。
运行：python engine/classical/test_computability_crosscheck.py
"""
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical import turing_machine as TM   # noqa: E402

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


# ══════════════════════════════════════════════════════════════
# 一、oracle T：照形式定义重写一份图灵机模拟器
# ══════════════════════════════════════════════════════════════
def simulate_mine(program, tape_input, steps_limit):
    """返回 (judge, steps, tape_dict, head)。

    配置 = (状态, 纸带, 读写头)；一步 = 读符号 → 查 δ → 写 → 移 → 换状态。
    accept / reject 是**停机状态**：一进入就停（**初始就在终态也算停机**）。
    未定义转移 = 停机（无转移可走）。纸带用 {位置: 符号}，空白不落格；R=+1、L=−1。
    """
    blank = program.get('blank', '_')
    tape = {i: ch for i, ch in enumerate(tape_input)}
    head, state = 0, program['start']
    steps = 0
    while True:
        if state == program['accept']:
            return 'accept', steps, tape, head
        if state == program['reject']:
            return 'reject', steps, tape, head
        if steps >= steps_limit:
            break
        sym = tape.get(head, blank)
        trans = program['delta'].get(state, {}).get(sym)
        if trans is None:
            return 'halt_undefined', steps, tape, head
        new_state, write, move = trans
        if write == blank:
            tape.pop(head, None)
        else:
            tape[head] = write
        head += 1 if move == 'R' else (-1 if move == 'L' else 0)
        state = new_state
        steps += 1
    return 'steps_exceeded', steps, tape, head


def tape_render(tape, head, blank='_', width=20):
    """与构件 `_tape_str` 同一口径：以读写头为中心 ±width/2 渲染。"""
    lo = min(tape.keys()) if tape else 0
    hi = max(tape.keys()) if tape else 0
    lo = min(lo, head - width // 2)
    hi = max(hi, head + width // 2)
    return ''.join(tape.get(i, blank) for i in range(lo, hi + 1))


def make_increment_machine():
    """二进制 +1 机：先一路向右走到空白，再从右往左进位。"""
    return {
        'states': ['q_right', 'q_add', 'q_acc', 'q_rej'],
        'start': 'q_right', 'accept': 'q_acc', 'reject': 'q_rej',
        'blank': '_',
        'delta': {
            'q_right': {'0': ['q_right', '0', 'R'],
                        '1': ['q_right', '1', 'R'],
                        '_': ['q_add', '_', 'L']},
            'q_add': {'0': ['q_acc', '1', 'R'],
                      '1': ['q_add', '0', 'L'],
                      '_': ['q_acc', '1', 'R']},
        },
    }


def make_loop_machine():
    """永不停机机：原地向右打转（验"步数用尽"的诚实报告）。"""
    return {
        'states': ['q0', 'q_acc', 'q_rej'],
        'start': 'q0', 'accept': 'q_acc', 'reject': 'q_rej',
        'blank': '_',
        'delta': {'q0': {'_': ['q0', '_', 'R']}},
    }


def make_undefined_machine():
    """未定义转移机：q0 只认 '1'，输入 '0' 时无转移可走。"""
    return {
        'states': ['q0', 'q_acc', 'q_rej'],
        'start': 'q0', 'accept': 'q_acc', 'reject': 'q_rej',
        'blank': '_',
        'delta': {'q0': {'1': ['q_acc', '1', 'R']}},
    }


print('=' * 70)
print('一、oracle T 自检（手算过的机器）')
inc = make_increment_machine()
_m_1011 = simulate_mine(inc, '1011', 100)
check('增量机 "1011" + 1 = "1100"',
      _m_1011[0] == 'accept'
      and ''.join(_m_1011[2].get(i, '_') for i in range(4)) == '1100',
      ''.join(_m_1011[2].get(i, '_') for i in range(4)))
_m_1111 = simulate_mine(inc, '1111', 100)
check('增量机 "1111" 全进位、左侧补 1（得到 10000）',
      _m_1111[0] == 'accept'
      and ''.join(_m_1111[2].get(i, '_') for i in range(-1, 4)) == '10000',
      ''.join(_m_1111[2].get(i, '_') for i in range(-1, 4)))
check('永不停机机在给定步数内必然 steps_exceeded（不假装判停机）',
      simulate_mine(make_loop_machine(), '', 50)[0] == 'steps_exceeded')
check('未定义转移机 → halt_undefined（不是 reject，也不静默停机）',
      simulate_mine(make_undefined_machine(), '0', 50)[0] == 'halt_undefined')

# ══════════════════════════════════════════════════════════════
# 二、随机小机器对拍：判词 + 终止配置 都要一致
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('二、turing_machine ↔ oracle T（随机 2 符号 3 状态机器 × 随机输入）')


def random_machine(rng):
    states = ['q0', 'q1']
    delta = {}
    for s in states:
        for sym in ('0', '1', '_'):
            if rng.random() < 0.75:
                delta.setdefault(s, {})[sym] = [
                    rng.choice(states + ['q_acc', 'q_rej']),
                    rng.choice(['0', '1', '_']),
                    rng.choice(['L', 'R'])]
    return {'states': states + ['q_acc', 'q_rej'], 'start': 'q0',
            'accept': 'q_acc', 'reject': 'q_rej', 'blank': '_', 'delta': delta}


rng = random.Random(20261009)
mis_t, mis_tape = [], []
n_acc, n_rej, n_exc, n_und = 0, 0, 0, 0
TRIALS_T = 60
for _ in range(TRIALS_T):
    prog = random_machine(rng)
    tape_in = ''.join(rng.choice('01') for _ in range(rng.choice([0, 1, 2, 3])))
    limit = 40
    mine = simulate_mine(prog, tape_in, limit)
    r = TM.run({'program': prog, 'input': tape_in, 'mode': 'simulate',
                'steps_limit': limit})
    got = r['verdict']
    n_acc += got == 'accept'
    n_rej += got == 'reject'
    n_exc += got == 'steps_exceeded'
    n_und += got == 'halt_undefined'
    if got != mine[0]:
        mis_t.append((tape_in, got, mine[0]))
        continue
    if r['trace']:
        want_tape = tape_render(mine[2], mine[3])
        if r['trace'][-1]['tape'] != want_tape:
            mis_tape.append((tape_in, got, r['trace'][-1]['tape'], want_tape))
check('判词与 oracle T 精确一致（%d 例）' % TRIALS_T, mis_t == [], mis_t[:2])
check('终止配置（纸带渲染）也一致（%d 例有轨迹可比）' % TRIALS_T,
      mis_tape == [], mis_tape[:2])
check('四种结果都被覆盖到（accept %d · reject %d · 步数用尽 %d · 未定义转移 %d）'
      % (n_acc, n_rej, n_exc, n_und),
      n_acc > 0 and n_exc > 0 and n_und > 0,
      (n_acc, n_rej, n_exc, n_und))
check('预置奇偶机与 oracle T 也一致（拿现成机器再对一次）',
      all(TM.run({'program': TM.parity_machine(), 'input': s,
                  'steps_limit': 60})['verdict']
          == simulate_mine(TM.parity_machine(), s, 60)[0]
          for s in ('', '0', '1', '000', '101', '1111')))

# ══════════════════════════════════════════════════════════════
# 三、留痕约定与退化情形（对拍查出来的两处，都钉住）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、留痕约定与退化情形')
_r_stuck = TM.run({'program': make_undefined_machine(), 'input': '0',
                   'steps_limit': 20})
check('未定义转移时**卡住那一格也留痕**（多一行轨迹，构件约定）',
      _r_stuck['verdict'] == 'halt_undefined'
      and len(_r_stuck['trace']) == 1
      and _r_stuck['trace'][-1]['state'] == 'q0', _r_stuck['trace'])
_p_acc = {'states': ['q0', 'q_acc', 'q_rej'], 'start': 'q_acc',
          'accept': 'q_acc', 'reject': 'q_rej', 'blank': '_', 'delta': {}}
check('初始态就在接受态 → 立刻 accept（**曾经报成 steps_exceeded**）',
      TM.run({'program': _p_acc, 'input': '0',
              'steps_limit': 10})['verdict'] == 'accept')
_p_rej = dict(_p_acc, start='q_rej', accept='q_acc', reject='q_rej')
check('初始态就在拒绝态 → 立刻 reject（同一处错的另一半）',
      TM.run({'program': _p_rej, 'input': '0',
              'steps_limit': 10})['verdict'] == 'reject')
check('步数上限为 0 时如实报 steps_exceeded（没有偷跑一步）',
      TM.run({'program': inc, 'input': '1',
              'steps_limit': 0})['verdict'] == 'steps_exceeded')

print()
print('=' * 70)
print(f'结果: {PASS}/12 通过')
raise SystemExit(0 if PASS == 12 else 1)
