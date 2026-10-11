# -*- coding: utf-8 -*-
"""test_entry_parity.py — 两个入口的一致性（③ 验证轴 · 契约型对照）

为什么要有这份文件：
    `repl`（交互台）的 BOUNDARY 明写"是命令行的**薄前端**：每条命令都交给
    engine.cli 执行，**不重写业务逻辑**"。这句话必须有判据——否则哪天台里悄悄
    自己格式化一遍诊断，用户就会看到"同一个问题两个入口两个答案"。
    本文件就是那句声明的判据：**同一件事，两个入口必须给同一结果**。

四条：
    ① **材料**：交互台喂材料 vs 命令行 `--text`，输出逐行一致（交互台只多一条
       "没开会话所以不记账"的说明，那条单独验）；
    ② **斜杠命令**：拿交互台**自己翻出来的 argv** 去真跑命令行（subprocess，
       确实是另一个入口），两边输出逐行一致；同时验 argv 是**命令行认得的**
       （翻了但命令行不认 = 翻译坏了，不能只说"两边一样"）；
    ③ **需要会话的命令**：无会话时明确拒绝并指路，不猜、不裸跑；
    ④ **帮助清单 ↔ 实现双向**：帮助里列的，实现要认得；实现认得的，帮助要列。

变异接受：把一条命令的 argv 翻译改坏 → 平价比对必须报出差异，且**交互台不许崩**
（踩过：argv 不被命令行认时 argparse 抛 SystemExit，旧 `_capture` 没接住，
整个交互台会带着 usage 退出——那是真修过的一处）。
运行：python engine/test_entry_parity.py
"""
import io
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine import repl as RP   # noqa: E402

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


def cli_run(argv, timeout=180):
    """真跑另一个入口（subprocess），返回 (退出码, 输出行, stderr)。"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, '-B', '-m', 'engine.cli'] + list(argv),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=timeout, env=env, cwd=_REPO)
    text = (r.stdout or '').rstrip('\n')
    return (r.returncode, (text.split('\n') if text else []), (r.stderr or ''))


def trim_tail(lines):
    """去掉尾部空行（两侧终端处理不同，不算差异）。"""
    out = list(lines)
    while out and out[-1].strip() == '':
        out.pop()
    return out


_STATE = {'json': False, 'session': None}
MATERIAL = ('销售坚持三周内必须上线抢占市场，研发坚持合规审查十二周一步不能少，'
            '既要抢占市场，又要完整合规，两边都觉得对方在拖后腿。')

print('=' * 70)
print('一、材料：交互台 ↔ 命令行（同一条材料的诊断必须一样）')
_repl_mat = RP.handle(MATERIAL, dict(_STATE))
_cli_rc, _cli_lines, _cli_err = cli_run(['--text', MATERIAL])
_NOTE = '（没有会话文件：这次只诊断、不记账'
_mine = [x for x in _repl_mat['lines'] if not x.startswith(_NOTE)]
check('交互台把"没开会话所以不记账"说明清楚了（该说的要说）',
      any(x.startswith(_NOTE) for x in _repl_mat['lines']))
check('材料诊断：两个入口输出逐行一致（交互台不重写业务逻辑）',
      trim_tail(_mine) == trim_tail(_cli_lines),
      (trim_tail(_mine)[:2], trim_tail(_cli_lines)[:2]))
check('材料诊断：两边都不是空输出（不是"空对空"地一致）',
      len(trim_tail(_cli_lines)) > 3 and any('T' in x for x in _cli_lines))

print()
print('=' * 70)
print('二、斜杠命令：拿交互台**自己翻出来的 argv** 去跑另一个入口')
_CMDS = ['/scenes', '/stats', '/scene S01', '/call bisimulation {}']
_bad_argv, _mis = [], []
for _line in _CMDS:
    _argv, _err, _q = RP.to_argv(_line, dict(_STATE))
    if not _argv:
        _bad_argv.append((_line, '翻译不出 argv：%s' % _err))
        continue
    _rc, _lines, _errout = cli_run(_argv)
    if _rc != 0 or 'unrecognized arguments' in (_errout or ''):
        _bad_argv.append((_line, _argv, _rc, (_errout or '')[-90:]))
        continue
    _r = RP.handle(_line, dict(_STATE))
    if trim_tail(_r['lines']) != trim_tail(_lines):
        _mis.append((_line, trim_tail(_r['lines'])[:2], trim_tail(_lines)[:2]))
check('四条命令的 argv 都**命令行认得**（翻译坏了会被这条抓住，不只是"两边一样"）',
      _bad_argv == [], _bad_argv[:1])
check('四条斜杠命令：交互台输出与另一个入口逐行一致', _mis == [], _mis[:1])
check('这四条命令都真的产出了内容（不是两边都空）',
      all(len(trim_tail(RP.handle(_l, dict(_STATE))['lines'])) > 0
          for _l in _CMDS))
_NEED_SESSION = ['/review S01', '/brief', '/progress']
_miss_guard = [(l, RP.handle(l, dict(_STATE))['verdict']) for l in _NEED_SESSION
               if '/session' not in ' '.join(
                   RP.handle(l, dict(_STATE))['lines'])]
check('需要会话的三条命令：无会话时明确拒绝并**指路 /session**（不猜、不裸跑）',
      _miss_guard == [], _miss_guard)

print()
print('=' * 70)
print('三、帮助清单 ↔ 实现（双向点名）')
# 口径说明（第一版判据太粗，改过两轮）：
#   · 帮助里的命令**有的写在行中间**（如 "· /scenes 场景清单 · /stats 统计"），
#     所以不能只认行首——但也不能"见斜杠就收"：正文里的 "状态/欠什么/复核到哪"
#     会被当成命令名。**命令形状 = ASCII 名**（/[a-z][a-z0-9_-]*）；
#   · 实现侧不止 `cmd == '/x'` 一种写法——`/state` `/overview` `/progress` 走的是
#     `simple = {'/state': '--session-state', ...}` 那个字典。所以判据取
#     "这个命令名在实现源码里**以引号字面量**出现过吗"；
#   · 两处**故意不对称**，各有理由，写在这里当下游白名单：
#     `/mark` 不列进帮助（本台不代签复核，用户被明确指到命令行落笔）；
#     `/bye` `/exit` `/q` 是 `/quit` 的别名，帮助只列正名。
_SRC = io.open(RP.__file__, encoding='utf-8').read()
_HELP_TEXT = '\n'.join(RP._HELP)
_HELP_CMD_RE = re.compile(r'/([a-z][a-z0-9_-]*)')
_help_cmds = sorted({m.group(1) for m in _HELP_CMD_RE.finditer(_HELP_TEXT)})
_impl_cmds = sorted({m.group(2) for m in
                     re.finditer(r"'(/([a-z][a-z0-9_-]*))'", _SRC)})
_IMPL_OK_NOT_IN_HELP = {'mark', 'bye', 'exit', 'q'}
_missing_in_impl = [c for c in _help_cmds if c not in _impl_cmds]
check('帮助里列的每个命令，实现源码里都以引号字面量出现过（帮助共 %d 条）'
      % len(_help_cmds), _missing_in_impl == [], _missing_in_impl)
_missing_in_help = [c for c in _impl_cmds
                    if c not in _help_cmds and c not in _IMPL_OK_NOT_IN_HELP]
check('实现认得的每个命令，帮助里都列了（实现共 %d 条；/mark 与 /bye·/exit·/q '
      '故意不列，理由见上）' % len(_impl_cmds), _missing_in_help == [],
      _missing_in_help)
check('帮助清单本身不是空的（%d 条）' % len(_help_cmds), len(_help_cmds) >= 15)

print()
print('=' * 70)
print('四、变异接受：把 argv 翻译改坏（顺带钉住"交互台不许崩"）')
_orig_to_argv = RP.to_argv


def _broken_to_argv(line, state):
    argv, err, quit_ = _orig_to_argv(line, state)
    if line.strip() == '/stats':
        return ['--scenes'], err, quit_          # 故意翻成命令行不认的命令
    return argv, err, quit_


RP.to_argv = _broken_to_argv
try:
    _broken = RP.handle('/stats', dict(_STATE))       # 旧版这里会 SystemExit 逃出去
    _crashed = False
except SystemExit:                                     # noqa: PERF203
    _crashed = True
    _broken = {'lines': []}
finally:
    RP.to_argv = _orig_to_argv
_rc_ok, _right, _e_ok = cli_run(['--stats'])
check('变异接受：命令翻错时平价比对确实报出差异（对拍有咬合力）',
      not _crashed
      and trim_tail(_broken['lines']) != trim_tail(_right))
check('翻错时**交互台不崩**，而是如实报错（旧版会带 usage 直接退出）',
      not _crashed and _broken.get('lines'))
check('变异已还原（to_argv 与原来同一个函数）', RP.to_argv is _orig_to_argv)

print()
print('=' * 70)
print(f'结果: {PASS}/13 通过')
raise SystemExit(0 if PASS == 13 else 1)
