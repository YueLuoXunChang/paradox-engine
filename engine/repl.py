# -*- coding: utf-8 -*-
"""
repl.py — 交互式诊断台（诊断工作台的交互版）
================================================================================
概念来源：轨 C（生态接口）+ 诊断工作台姿态——工作台线原先要**拼命令行参数**
（`--session 文件 --add "材料" --clues` 一条条来），交互台把同一批能力收进一个
提示符里：粘一段材料就出诊断，敲一个命令就看汇总/简报/场景。

本构件做什么（一句话）：
    一个读一行的交互台：**普通文字＝材料**（当场诊断，开着会话就顺手记账），
    **斜杠开头＝命令**（会话状态、批次汇总、一页简报、线索与工作单、复核查看、
    对账、导出、信念修正、场景与统计）。

怎么做（设计上的一条硬规矩）：
    交互台**不重写任何业务逻辑**——它是 CLI 的**薄前端**：每条命令翻成 CLI 参数，
    交给 `engine.cli` 去执行，再把输出抓回来。这样"命令行能做的交互台都能做"，
    而且两边永远一致（一个地方改，两边同时生效）。

命令一览（`/help` 里也有一份，带例子）：
    /session 文件      打开/切换会话台账（之后每段材料都会记账）
    /state            当前状态汇总     /overview  批次汇总（按引擎自己的标签分组）
    /brief [文件]     一页简报         /progress  复核进度快照
    /suggest 文本     结构化线索建议   /pending [文件]  欠线索工作单
    /review [场景|all] 看复核（只读）  /reconcile [文件] 会话依据 vs 场景表落笔对账
    /export 文件      导出 Markdown 台账（可加 --redact 走隐私导出）
    /revise 命题式    给新信息触发信念修正（第 N 轮可写 /revise N 命题式）
    /scene 场景号     跑单个场景（期望 vs 实际）  /scenes  场景清单  /stats 场景库统计
    '  /call 工具 {参数JSON}  直接调一个工具（不经判类路由；清单 paradox-engine --tools）',
    /json on|off      命令输出是否走 JSON      /help  本帮助   /quit 退出

诚实边界（本构件的红线）：
    - **不提供复核落笔**：`--mark` 只留在命令行——复核结论是作者的动作，交互台不给
      "顺手点一下就把 checked 落了"的口子（`/mark` 会被明确拒绝并说明去哪落）；
    - **没有会话文件就只诊断不记账**（不偷偷在别处落文件）；记账只写在 `/session` 指定的
      那个文件上；
    - 交互台只搬运引擎的输出，**不替人下结论、不补内容**：命令跑不动就把 CLI 的话原样给你；
    - 命令写错（缺参数/未知命令）→ 诚实报错 + 提示可用命令，不猜你要干什么。

统一接口：
    run(inputs: dict) -> dict
    输入:
        line: str——一行输入（材料或命令）
        state: dict——交互台状态（可省，省了就是新开一台）
        session: str——初始会话文件（可省）
    输出:
        verdict: str——'handled'|'material_diagnosed'|'error'|'quit'|'idle'|'help'
        lines: list——这一行产生的输出（逐行字符串）
        state: dict——更新后的状态
        quit: bool——是否该退出
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'line': 'str?', 'state': 'dict?', 'session': 'str?'},
    'out': {'verdict': 'str', 'lines': 'list', 'state': 'dict',
            'quit': 'bool', 'boundary': 'str'},
}

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BOUNDARY = ('交互式诊断台是命令行的薄前端：每条命令都交给 engine.cli 执行，不重写业务逻辑，'
            '所以两边结果一致。**不代签复核**：不提供复核落笔（--mark 只留在命令行，'
            '复核是作者的动作）。没有会话文件时就只诊断不记账（不偷偷在别处落文件）。'
            '引擎只诊断不决策，交互台只搬运输出、不替人下结论。')

_QUIT_WORDS = ('/quit', '/exit', '/q', '/bye')

_HELP = [
    '可用命令（普通文字＝材料，斜杠开头＝命令）：',
    '  /session 文件        打开/切换会话台账（之后每段材料都会记账）',
    '  /state              当前状态汇总（轮次/题型分布/墙清单/信念集）',
    '  /overview           批次汇总（按引擎自己的标签分组计数）',
    '  /brief [文件]       一页简报（状态/欠什么/复核到哪/下一步）',
    '  /progress           复核进度快照（与上次比：又复核了哪些）',
    '  /suggest 文本       结构化线索建议（只建议，不产生逻辑式）',
    '  /pending [文件]     欠线索工作单（能拼成可粘贴命令）',
    '  /review [场景|all]  看复核依据（只读，不替作者落笔）',
    '  /reconcile [文件]   会话依据 vs 场景表落笔 对账（两边都不改）',
    '  /export 文件        导出 Markdown 台账（加 redact 走隐私导出：/export 文件 redact）',
    '  /revise [轮次] 命题式  新信息触发 AGM 信念修正（命题式由人给，引擎不抽公式）',
    '  /scene 场景号       跑单个场景（期望 vs 实际）  ·  /scenes 场景清单  ·  /stats 统计',
    '  /call 工具 {参数JSON}  直接调一个工具（不经判类路由；清单 paradox-engine --tools）',
    '  /file 材料.md [para|line] [chunk N] [from N]  整篇材料逐段诊断并记账（分段/分块/续跑）',
    '  /clues on|off       材料记账时是否顺手记下线索建议（默认关）',
    '  /struct {...}       给下一段材料挂结构化线索（JSON），好让构件真跑；/struct clear 清掉',
    '  /json on|off        命令输出是否走 JSON（默认 off，人读）',
    '  /help               本帮助          ·  /quit 退出',
    '说明：命令不完整或未知 → 只报错并提示，不猜你的意思；'
    '复核落笔请用命令行 `paradox-engine --mark S05 --verdict ok`（本台不代签）。',
]


def new_state(session=None):
    """新开一台（session 可省——省了就只诊断不记账）。"""
    return {'session': session, 'turns': 0, 'json': False, 'last_rc': 0,
            'clues': False, 'structured': None}


def _cli():
    """取 CLI 入口（薄前端只依赖这一个函数）。"""
    try:
        from engine import cli
    except ImportError:
        sys.path.insert(0, _REPO)
        from engine import cli
    return cli


def _capture(argv):
    """跑一次 CLI，把这轮的输出抓成行（交互台不重写业务逻辑，只搬运输出）。"""
    cli = _cli()
    buf = io.StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        rc = cli.main(argv)
    finally:
        sys.stdout = old
    text = buf.getvalue().rstrip('\n')
    return rc, (text.split('\n') if text else [])


def _need_session(state):
    if not state.get('session'):
        return ('还没有会话台账：先 `/session 文件.json`（之后的材料才会记账；'
                '不打开会话就只诊断、不落文件）')
    return None


def to_argv(line, state):
    """把一行命令翻成 CLI 参数。返回 (argv, error, quit)。"""
    text = line.strip()
    if text in _QUIT_WORDS:
        return None, None, True
    if text in ('/help', '/?', '?'):
        return None, None, None
    if text.startswith('/mark'):
        return None, ('复核落笔不在这儿：请用命令行 '
                      '`paradox-engine --mark S05 --verdict ok`（作者的动作，'
                      '交互台不代签）'), None

    parts = text.split(maxsplit=1)
    cmd, rest = parts[0], (parts[1].strip() if len(parts) > 1 else '')
    jf = ['--json'] if state.get('json') else []
    S = state.get('session')

    if cmd == '/session':
        if not rest:
            return None, ('用法：/session 文件.json（当前：%s）'
                          % (S or '未打开')), None
        return None, None, None                    # 由 handle 处理（只改状态）
    if cmd == '/json':
        if rest not in ('on', 'off'):
            return None, '用法：/json on|off', None
        return None, None, None
    if cmd == '/suggest':
        if not rest:
            return None, '用法：/suggest 一段材料', None
        return ['--suggest', rest] + jf, None, None
    if cmd == '/stats':
        return ['--stats'] + jf, None, None
    if cmd == '/call':
        if not rest:
            return None, ('用法：/call 工具名 {"参数": ...}——直接调一个工具，'
                          '不经判类路由；工具清单用命令行 `paradox-engine --tools`'), None
        bits = rest.split(maxsplit=1)
        name = bits[0]
        raw = bits[1].strip() if len(bits) > 1 else '{}'
        return ['--call', name, '--args', raw] + jf, None, None
    if cmd == '/scenes':
        return ['--scenarios'] + jf, None, None
    if cmd == '/file':
        miss = _need_session(state)
        if miss:
            return None, miss, None
        if not rest:
            return None, ('用法：/file 材料.md [para|line] [chunk N] [from N] ——'
                          '整篇材料逐段诊断并记账（分段/分块/可续跑）'), None
        bits = rest.split()
        argv = ['--session', S, '--add-file', bits[0]]
        i = 1
        while i < len(bits):
            b = bits[i]
            if b in ('para', 'line'):
                argv += ['--split', b]
            elif b in ('chunk', 'from'):
                if i + 1 >= len(bits):
                    return None, ('%s 后面要跟一个数字（如 /file 材料.md chunk 20）' % b), None
                argv += ['--chunk' if b == 'chunk' else '--from-seg', bits[i + 1]]
                i += 1
            else:
                return None, ('看不懂的选项：%s —— 用法：/file 材料.md [para|line] '
                              '[chunk N] [from N]' % b), None
            i += 1
        if state.get('clues'):
            argv.append('--clues')
        return argv + jf, None, None
    if cmd == '/scene':
        if not rest:
            return None, '用法：/scene S01（场景号见 /scenes）', None
        return ['--scene', rest.split()[0]] + jf, None, None

    simple = {'/state': '--session-state', '/overview': '--overview',
              '/brief': '--brief', '/progress': '--progress',
              '/pending': '--pending', '/reconcile': '--reconcile',
              '/reset': '--session-reset'}
    if cmd in simple:
        miss = _need_session(state)
        if miss:
            return None, miss, None
        argv = ['--session', S, simple[cmd]] + jf
        if cmd == '/brief' and rest:
            argv += ['--brief-out', rest]
        if cmd == '/pending' and rest:
            argv += ['--pending-out', rest]
        if cmd == '/reconcile' and rest:
            argv += ['--reconcile-out', rest]
        return argv, None, None
    if cmd == '/export':
        miss = _need_session(state)
        if miss:
            return None, miss, None
        if not rest:
            return None, ('用法：/export 台账.md（默认不覆盖已存在文件；'
                          '末尾加 redact 走隐私导出）'), None
        bits = rest.split()
        argv = ['--session', S, '--export', bits[0]] + jf
        if 'redact' in bits[1:] or '--redact' in bits[1:]:
            argv.append('--redact')
        if 'overwrite' in bits[1:]:
            argv.append('--export-overwrite')
        return argv, None, None
    if cmd == '/review':
        miss = _need_session(state)
        if miss:
            return None, miss, None
        argv = ['--session', S, '--review', '--scene', (rest or 'all')] + jf
        return argv, None, None
    if cmd == '/revise':
        miss = _need_session(state)
        if miss:
            return None, miss, None
        if not rest:
            return None, ('用法：/revise 命题式（如 ¬Q），或 /revise 3 ¬Q 挂到第 3 轮——'
                          '命题式由人给，引擎不抽公式'), None
        bits = rest.split(maxsplit=1)
        argv = ['--session', S] + jf
        if bits[0].isdigit():                       # /revise 3 ¬Q
            if len(bits) < 2:
                return None, '用法：/revise 轮次 命题式（如 /revise 3 ¬Q）', None
            return ['--session', S, '--revise', bits[1], '--turn', bits[0]] + jf, \
                None, None
        return ['--session', S, '--revise', rest] + jf, None, None
    return None, ('看不懂这条命令：%s —— 敲 /help 看可用命令（普通文字会被当成材料）'
                  % cmd), None


def handle(line, state=None):
    """
    做什么：处理交互台的一行输入（材料或命令），返回输出与更新后的状态。

    返回 dict（PORTS['out']）。这是**可测内核**：正式测试直接喂行来驱动，
    不需要人去敲。
    """
    st = dict(state) if isinstance(state, dict) else new_state()
    st.setdefault('turns', 0)
    st.setdefault('json', False)
    text = '' if line is None else str(line).rstrip('\n').strip()
    # 踩过：PowerShell 管道喂进来的**第一行**前面会带一个 BOM（'\ufeff/help'），
    # 不剥掉的话命令会被当成材料。输入边界上先把 BOM 去掉。
    text = text.lstrip('\ufeff')

    def out(verdict, lines, quit_=False):
        st['last_rc'] = 0
        return {'verdict': verdict, 'lines': lines, 'state': st,
                'quit': quit_, 'boundary': BOUNDARY}

    if not text:                                   # 空行：什么都不做
        return out('idle', [])

    # ── 只看状态、不跑 CLI 的两条
    if text in ('/help', '/?', '?'):
        return out('help', list(_HELP))
    if text.startswith('/session'):
        miss = None
        rest = text[len('/session'):].strip()
        if not rest:
            return out('help', ['当前会话：%s' % (st.get('session') or '未打开'),
                                '用法：/session 文件.json'] +
                       ([] if st.get('session') else
                        ['（不打开会话也能用：材料会被诊断，但不记账、不落文件）']))
        st['session'] = rest
        return out('handled', ['会话台账已指向：%s' % rest,
                               '之后的材料会逐条记账（/state 看汇总，/export 导出台账）'])
    if text.startswith('/json'):
        rest = text[len('/json'):].strip()
        if rest not in ('on', 'off'):
            return out('error', ['用法：/json on|off'])
        st['json'] = (rest == 'on')
        return out('handled', ['命令输出走 JSON：%s' % ('开' if st['json'] else '关')])
    if text.startswith('/clues'):
        rest = text[len('/clues'):].strip()
        if rest in ('on', 'off'):
            st['clues'] = (rest == 'on')
            return out('handled', ['材料记账时顺手记线索建议：%s'
                                   % ('开' if st['clues'] else '关')])
        if rest == '':
            return out('help', ['线索建议当前：%s（用法 /clues on|off）'
                                % ('开' if st.get('clues') else '关')])
        return out('error', ['用法：/clues on|off'])
    if text.startswith('/struct'):
        rest = text[len('/struct'):].strip()
        if rest in ('clear', 'off', 'none'):
            st['structured'] = None
            return out('handled', ['已清掉结构化线索：之后每段材料都按"没有线索"诊断'])
        if not rest:
            cur = st.get('structured')
            return out('help', ['当前结构化线索：%s' % (cur or '（没挂）'),
                                '用法：/struct {"A":"…","B":"…","wA":5,"wNotA":5} '
                                '（挂给下一段材料，好让构件真跑）；/struct clear 清掉'])
        try:
            json.loads(rest)
        except ValueError as e:
            return out('error', ['结构化线索不是合法 JSON（%s）——不挂，也不猜' % e])
        st['structured'] = rest
        return out('handled', ['结构化线索已挂上（下一段材料会带上它真跑构件）；'
                               '/struct clear 可清掉'])

    # ── 斜杠命令 → 翻成 CLI 参数
    if text.startswith('/'):
        argv, err, quit_ = to_argv(text, st)
        if quit_:
            return out('quit', ['（退出交互台）'], quit_=True)
        if err:
            return out('error', [err])
        rc, lines = _capture(argv)
        st['last_rc'] = rc
        res = {'verdict': 'handled', 'lines': lines, 'state': st, 'quit': False,
               'boundary': BOUNDARY}
        if rc not in (0, 1):                       # 0=正常 1=有对照失败；其余多为用法错
            res['lines'] = lines + ['［命令返回码 %d］' % rc]
            res['verdict'] = 'error'
        return res

    # ── 普通文字＝材料：开着会话就顺手记账（走 CLI 的 --add），否则只诊断
    extra = []
    if st.get('clues'):
        extra.append('--clues')
    if st.get('structured'):
        extra += ['--structured-json', st['structured']]
    if st.get('session'):
        rc, lines = _capture(['--session', st['session'], '--add', text] + extra +
                             (['--json'] if st['json'] else []))
        st['turns'] += 1
        st['last_rc'] = rc
        return {'verdict': 'material_diagnosed', 'lines': lines, 'state': st,
                'quit': False, 'boundary': BOUNDARY}
    rc, lines = _capture(['--text', text] + extra +
                         (['--json'] if st['json'] else []))
    st['last_rc'] = rc
    lines = lines + ['（没有会话文件：这次只诊断、不记账——'
                     '想逐条记账先 `/session 文件.json`）']
    return {'verdict': 'material_diagnosed', 'lines': lines, 'state': st,
            'quit': False, 'boundary': BOUNDARY}


def run(inputs):
    """
    做什么：交互台统一入口（机制形态）——给一行，回一段输出与新状态。

    返回 dict（PORTS['out']）。
    """
    if not isinstance(inputs, dict):
        return {'verdict': 'error', 'lines': ['inputs 必须是 dict'],
                'state': new_state(), 'quit': False, 'boundary': BOUNDARY}
    st = inputs.get('state')
    if st is None and inputs.get('session'):
        st = new_state(inputs['session'])
    elif st is None:
        st = new_state()
    if 'line' not in inputs:
        return {'verdict': 'idle', 'lines': [], 'state': st, 'quit': False,
                'boundary': BOUNDARY}
    return handle(inputs.get('line'), st)


def main(argv=None):
    """
    做什么：真交互循环——读一行、处理一行、打印输出（EOF 或 /quit 结束）。

    诚实边界：非交互式（管道）时同样能用：`echo "/help" | paradox-engine --repl`。
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    session = None
    for i, a in enumerate(argv):
        if a == '--session' and i + 1 < len(argv):
            session = argv[i + 1]
    try:                                           # 控制台自愈（emoji/中文）
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    st = new_state(session)
    print('诊断工作台 · 交互台（普通文字＝材料，/help 看命令，/quit 退出）')
    if session:
        print('会话台账：%s' % session)
    interactive = sys.stdin is not None and sys.stdin.isatty()
    while True:
        try:
            if interactive:
                sys.stdout.write('诊断> ')
                sys.stdout.flush()
            line = sys.stdin.readline()
        except (KeyboardInterrupt, EOFError):
            print('\n（退出交互台）')
            return 0
        if line == '':                             # EOF
            if interactive:
                print('（退出交互台）')
            return 0
        r = handle(line, st)
        st = r['state']
        for ln in r['lines']:
            print(ln)
        if r['quit']:
            return 0


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass
    import tempfile

    print('=' * 66)
    print('交互式诊断台 · 自测')
    print('=' * 66)

    r0 = handle('')
    assert r0['verdict'] == 'idle' and r0['lines'] == [], r0
    print('✅ 空行：什么都不做')

    r1 = handle('/help')
    assert r1['verdict'] == 'help' and any('/session' in x for x in r1['lines']), r1
    print('✅ /help：列出可用命令')

    r2 = handle('产品既要三周上线又要十二周合规')
    assert r2['verdict'] == 'material_diagnosed', r2
    assert any('（没有会话文件' in x for x in r2['lines']), r2
    print('✅ 没开会话时给材料：出诊断，并说明这次不记账')

    d = tempfile.mkdtemp(prefix='pe_repl_')
    sp = os.path.join(d, '会话.json')
    r3 = handle('/session ' + sp, r2['state'])
    assert r3['verdict'] == 'handled' and r3['state']['session'] == sp, r3
    r4 = handle('这句话是假的', r3['state'])
    assert r4['verdict'] == 'material_diagnosed' and os.path.exists(sp), r4
    print('✅ /session 之后给材料：诊断并记账（会话文件真的落盘）')

    r5 = handle('/overview', r4['state'])
    assert r5['verdict'] == 'handled' and r5['lines'], r5
    print('✅ /overview：出批次汇总')

    r6 = handle('/mark S05 ok', r4['state'])
    assert r6['verdict'] == 'error' and '不代签' in r6['lines'][0], r6
    print('✅ /mark：明确拒绝并指出落笔在命令行（不代签复核）')

    r7 = handle('/不存在', r4['state'])
    assert r7['verdict'] == 'error' and '/help' in r7['lines'][0], r7
    print('✅ 未知命令：报错并提示 /help')

    r8 = handle('/quit', r4['state'])
    assert r8['quit'] is True, r8
    print('✅ /quit：退出')

    print('=' * 66)
    print('交互式诊断台自测：全部通过 ✅')
    print('=' * 66)
