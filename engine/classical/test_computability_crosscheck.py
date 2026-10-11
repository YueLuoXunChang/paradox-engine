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

from engine.classical import lambda_calculus as LC   # noqa: E402
from engine.classical import recursion_theorem as RT   # noqa: E402
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

# ══════════════════════════════════════════════════════════════
# 四、recursion_theorem：不只看产物长得对不对，**执行它**
# ══════════════════════════════════════════════════════════════
# 为什么这么验：这一件产出的是**真能跑的 Python 源码**，所以"能不能跑、跑出来对不对"
# 是硬判据——比读源码猜语义强。本批就是靠它撞出旧版 recursive 产物一跑就
# `NameError: _TRANSFORM is not defined`（返回一个跑不起来的产物，而 runs_like
# 却描述成能跑的行为）。
print()
print('=' * 70)
print('四、recursion_theorem ↔ 执行产物（subprocess 实跑）')
import re      # noqa: E402
import subprocess   # noqa: E402
import tempfile     # noqa: E402


def run_source(src, timeout=25):
    """把源码写成临时文件跑一遍，返回 (退出码, stdout, stderr)。"""
    d = tempfile.mkdtemp(prefix='rt_check_')
    p = os.path.join(d, 'prog.py')
    with open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(src)
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, '-B', p], capture_output=True,
                       text=True, encoding='utf-8', errors='replace',
                       timeout=timeout, env=env, cwd=d)
    return r.returncode, r.stdout or '', r.stderr or ''


PAYLOAD = '好，自指'
_pq = RT.run({'mode': 'quine', 'payload': PAYLOAD})['program']
rc_q, out_q, err_q = run_source(_pq)
check('quine 产物能跑（退出码 0）', rc_q == 0, err_q[-120:])
check('quine 产物真把 payload 打出来了',
      PAYLOAD in out_q, out_q[:80])
# 自复制链：产物 → 打印出一段"程序源码" → 那段源码跑起来又打印 payload 源码 → 再跑打印 payload
_blocks = re.split(r'--- 程序源码 ---|--- 运行输出 ---', out_q)
printed_src = _blocks[1].strip('\n') if len(_blocks) > 2 else ''
rc_p, out_p, err_p = run_source(printed_src)
check('产物打印出的那段"程序源码"自己也能跑（退出码 0）', rc_p == 0,
      err_p[-120:])
payload_src = out_p.strip('\n')
rc_pp, out_pp, _e = run_source(payload_src + '\n') if payload_src else (1, '', '')
check('自复制链走通：产物 → 打印出的源码 → 再跑出 payload',
      'msg = ' in payload_src and 'print(msg)' in payload_src
      and out_pp.strip() == PAYLOAD, (payload_src[:40], out_pp[:40]))
check('同一份产物跑两次输出相同（确定性）',
      run_source(_pq)[1] == out_q)

_pr = RT.run({'mode': 'recursive'})['program']
rc_r, out_r, err_r = run_source(_pr)
check('recursive 产物能跑（**旧版一跑就 NameError**，这是回归）',
      rc_r == 0 and 'NameError' not in err_r, err_r[-140:])
check('recursive 产物确实拿到了**自己的源码**（递归定理的核心动作）',
      _pr.rstrip('\n') in out_r)
_m = re.search(r'源码 (\d+) 字符 → f\(e\) (\d+) 字符', out_r)
check('recursive 产物报出变换前后长度，且 f 真的改了东西（长度差 > 0）',
      bool(_m) and int(_m.group(2)) > int(_m.group(1)),
      _m.group(0) if _m else out_r[-80:])
check('recursive 的 runs_like 描述的是**实际行为**（内联默认变换、不 exec）',
      '内联' in RT.run({'mode': 'recursive'})['runs_like']
      and '不 exec' in RT.run({'mode': 'recursive'})['boundary'])

# ══════════════════════════════════════════════════════════════
# 五、lambda_calculus ↔ oracle L：自己写一份归约器
# ══════════════════════════════════════════════════════════════
# 要点三条（每一条都容易写错、也就容易对不上）：
#   ① **捕获避免**：替换进 λ 体时，若被绑定名出现在替换项的**自由变量**里，
#      必须先 α-改名，否则自由变量会被"吞"进绑定里；
#   ② **最左最外**（normal order）：范式唯一，所以两边算出来的范式必须 α-等价；
#   ③ 比范式**不能比字符串**——换名、括号写法都可能不同，要转到 **de Bruijn** 再比。
print()
print('=' * 70)
print('五、lambda_calculus ↔ oracle L（自写捕获避免归约器，按 α-等价比较）')
_TOK = re.compile(r'\\|λ|[.()]|[A-Za-z_][A-Za-z0-9_]*')


def lam_parse(s):
    toks = _TOK.findall(s)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def parse_atom():
        t = take()
        if t in ('\\', 'λ'):
            var = take()
            if take() != '.':
                raise ValueError('λ 缺 .')
            return ('lam', var, parse_term())
        if t == '(':
            inner = parse_term()
            if take() != ')':
                raise ValueError('缺右括号')
            return inner
        return ('var', t)

    def parse_term():
        t = parse_atom()
        while peek() is not None and peek() not in (')', '.'):
            t = ('app', t, parse_atom())
        return t

    out = parse_term()
    if pos[0] != len(toks):
        raise ValueError('多余内容 %r' % toks[pos[0]:])
    return out


def free_vars(t):
    if t[0] == 'var':
        return {t[1]}
    if t[0] == 'lam':
        return free_vars(t[2]) - {t[1]}
    return free_vars(t[1]) | free_vars(t[2])


def rename(t, old, new):
    """α-改名：把绑定名 old 换成 new（调用方保证 new 不撞自由变量）。"""
    if t[0] == 'var':
        return ('var', new) if t[1] == old else t
    if t[0] == 'lam':
        if t[1] == old:
            return ('lam', new, t[2])
        return ('lam', t[1], rename(t[2], old, new))
    return ('app', rename(t[1], old, new), rename(t[2], old, new))


def subst(t, var, rep, capture_avoid=True):
    """t[var := rep]；capture_avoid=False 时**故意不改名**（变异用）。"""
    if t[0] == 'var':
        return rep if t[1] == var else t
    if t[0] == 'app':
        return ('app', subst(t[1], var, rep, capture_avoid),
                subst(t[2], var, rep, capture_avoid))
    _k, x, body = t
    if x == var:
        return t
    if capture_avoid and x in free_vars(rep):
        used = free_vars(rep) | free_vars(body) | {var}
        i = 1
        while '%s%d' % (x, i) in used:
            i += 1
        x2 = '%s%d' % (x, i)
        return ('lam', x2, subst(rename(body, x, x2), var, rep, capture_avoid))
    return ('lam', x, subst(body, var, rep, capture_avoid))


def step_once(t, capture_avoid=True):
    """最左最外找一步 β-收缩；没有可收缩的就返回 None。"""
    if t[0] == 'app':
        f, a = t[1], t[2]
        if f[0] == 'lam':
            return subst(f[2], f[1], a, capture_avoid)
        nf = step_once(f, capture_avoid)
        if nf is not None:
            return ('app', nf, a)
        na = step_once(a, capture_avoid)
        return ('app', f, na) if na is not None else None
    if t[0] == 'lam':
        nb = step_once(t[2], capture_avoid)
        return ('lam', t[1], nb) if nb is not None else None
    return None


def normalize_mine(t, limit=200, capture_avoid=True):
    for i in range(limit):
        nx = step_once(t, capture_avoid)
        if nx is None:
            return 'normalized', t
        t = nx
    return 'step_limit', t


def debruijn(t, env=()):
    """去名字：α-等价 ⟺ de Bruijn 形式相等（自由变量仍留名）。"""
    if t[0] == 'var':
        return ('b', env.index(t[1])) if t[1] in env else ('f', t[1])
    if t[0] == 'lam':
        return ('l', debruijn(t[2], (t[1],) + env))
    return ('a', debruijn(t[1], env), debruijn(t[2], env))


def canon_of(term_str, capture_avoid=True, limit=200):
    """表达式字符串 → (判词, de Bruijn 范式)。"""
    v, t = normalize_mine(lam_parse(term_str), limit, capture_avoid)
    return v, debruijn(t)


I_TERM = r'(\x.x)'
K_TERM = r'(\x.\y.x)'
S_TERM = r'(\f.\g.\x.(f x)(g x))'
_SKK = '(%s %s %s)' % (S_TERM, K_TERM, K_TERM)
_KNOWN = [
    (r'(\x.x) y', 'y'),
    (r'(\x.\y.x) a b', 'a'),
    (r'(\x.\y.y) a b', 'b'),
    (r'(\x.(x x)) (\y.y)', r'(\z.z)'),
    (_SKK, r'(\x.x)'),
    (r'(\x.\y.x) y', r'(\y1.y)'),
    (r'(\f.\x.f (f x)) (\y.y)', r'(\x.x)'),
]
_mis_lam = []
for _src, _want in _KNOWN:
    _v, _mine = canon_of(_src)
    _wv, _want_db = canon_of(_want)
    if _mine != _want_db:
        _mis_lam.append((_src, _mine, _want_db))
check('七条已知项：oracle L 算出的范式与手算目标 α-等价', _mis_lam == [],
      _mis_lam[:1])
_mis_lc = []
for _src, _want in _KNOWN:
    _wv, _want_db = canon_of(_want)
    _r = LC.run({'mode': 'beta_normal', 'expr': _src})
    if _r['verdict'] != 'normalized':
        _mis_lc.append((_src, _r['verdict']))
        continue
    _v2, _got = canon_of(_r['normal_form'] or '')
    if _got != _want_db:
        _mis_lc.append((_src, _r['normal_form'], _want))
check('lambda_calculus ↔ oracle L：七条已知项的范式 α-等价', _mis_lc == [],
      _mis_lc[:2])
_r_cap = LC.run({'mode': 'beta_normal', 'expr': r'(\x.\y.x) y'})
check('捕获避免真的做了：(\\x.\\y.x) y 的范式里自由 y **没被吞掉**（绑定名改成 y1）',
      _r_cap['verdict'] == 'normalized' and 'y1' in (_r_cap['normal_form'] or ''),
      _r_cap['normal_form'])
check('SKK = I（组合子化简，两边都算到 λx.x）',
      canon_of(_SKK)[1] == canon_of(I_TERM)[1]
      and canon_of(LC.run({'mode': 'beta_normal',
                           'expr': _SKK})['normal_form'])[1]
      == canon_of(I_TERM)[1])
check('发散项 Ω 两边都**不假装收敛**：构件报 step_limit，oracle L 同样用尽步数',
      LC.run({'mode': 'beta_normal',
              'expr': r'(\x.x x)(\x.x x)'})['verdict'] == 'step_limit'
      and normalize_mine(lam_parse(r'(\x.x x)(\x.x x)'), 200)[0]
      == 'step_limit')
check('默认 mode 就是 beta_normal（同一套语义，不是两套）',
      LC.run({'expr': r'(\x.x) y'})['normal_form']
      == LC.run({'mode': 'beta_normal', 'expr': r'(\x.x) y'})['normal_form'])

# Church 数：构件的 church 模式是"取 n，应用 succ，报 n+1"——
# 用**自己的** succ 编码与解码再算一遍，比的是同一件事：succ(n) 到底是几。
SUCC_MINE = lam_parse(r'(\n.\f.\x.f (n f x))')


def decode_church(t):
    if t[0] != 'lam' or t[2][0] != 'lam':
        return None
    inner = t[2][2]
    k = 0
    while inner[0] == 'app' and inner[1] == ('var', 'f'):
        k += 1
        inner = inner[2]
    return k if inner == ('var', 'x') else None


def church_mine(n):
    body = ('var', 'x')
    for _ in range(n):
        body = ('app', ('var', 'f'), body)
    return ('lam', 'f', ('lam', 'x', body))


_mis_ch = []
for _n in range(0, 6):
    _v3, _t = normalize_mine(('app', SUCC_MINE, church_mine(_n)))
    _mine_n = decode_church(_t)
    _got_n = LC.run({'mode': 'church', 'church_arg': _n})['church_number']
    if _mine_n != _got_n or _mine_n != _n + 1:
        _mis_ch.append((_n, _mine_n, _got_n))
check('Church 数：n=0..5 上，构件的 σ(n) 与我自写编码算出的 n+1 一致',
      _mis_ch == [], _mis_ch[:2])
import math   # noqa: E402
check('factorial：n=0..6 的阶乘值与独立算术一致',
      all(LC.run({'mode': 'factorial', 'fact_n': _n})['factorial_value']
          == math.factorial(_n) for _n in range(0, 7)))
check('变异接受：把 oracle L 的**捕获避免**去掉后，捕获那一例立刻对不上'
      '（证明这条对拍真在盯这件事）',
      canon_of(r'(\x.\y.x) y', capture_avoid=False)[1]
      != canon_of(r'(\x.\y.x) y', capture_avoid=True)[1])

print()
print('=' * 70)
print(f'结果: {PASS}/30 通过')
raise SystemExit(0 if PASS == 30 else 1)
