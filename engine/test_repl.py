# -*- coding: utf-8 -*-
"""
test_repl.py — 正式测试：交互式诊断台（可测内核 + 端到端管道）
================================================================
为什么这么测：
    交互台原本最难测的就是"人来敲"这一步。所以内核被拆成**纯函数**
    `handle(line, state) -> {verdict, lines, state, quit}`——正式测试直接喂行驱动，
    不必人去敲；再用一次**子进程 + 管道**跑真循环，确认 stdin 那条路也通。

守两条纪律（本构件的红线）：
    ① **不代签复核**：`/mark` 必须被明确拒绝并指出落笔在命令行；
    ② **不偷偷落文件**：没有 `/session` 时就只诊断；有会话时只写那个文件；
       全程**不写场景表**（sha256 前后一致守着）。
运行：python engine/test_repl.py
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

from engine.repl import handle, new_state, run as repl_run  # noqa: E402

PASS = 0
_SCENES = os.path.join(_REPO, 'engine', 'scenarios', 'scenarios.py')

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


def _sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _joined(r):
    return '\n'.join(r['lines'])


print("交互式诊断台 · 正式测试")
print("=" * 60)

_sha_before = _sha(_SCENES)
_tmp = tempfile.mkdtemp(prefix='pe_repl_test_')

# ── 一、内核：逐行驱动（不需要人敲）
r = handle('')
check("空行 → idle，无输出", r['verdict'] == 'idle' and r['lines'] == [], str(r))
r = handle('/help')
check("/help → help，列出命令清单",
      r['verdict'] == 'help' and any('/session' in x for x in r['lines'])
      and len(r['lines']) >= 10, str(len(r['lines'])))
r = handle('产品既要三周上线又要十二周合规')
check("材料（没开会话）→ 出诊断，并说明这次不记账",
      r['verdict'] == 'material_diagnosed'
      and '【类型】' in _joined(r) and '不记账' in _joined(r), _joined(r)[:120])
check("诊断输出带判类/复杂度/路由三样（与命令行同一套）",
      '【类型】' in _joined(r) and '复杂度' in _joined(r)
      and '路由' in _joined(r))
r = handle('　\ufeff/help')          # 全角空格 + BOM：输入边界要健壮
check("带 BOM / 空白的行也能认出命令（PowerShell 管道会塞 BOM，踩过）",
      r['verdict'] == 'help', str(r['verdict']))

# ── 二、会话：记账只写指定的那个文件
sp = os.path.join(_tmp, '会话.json')
r = handle('/session ' + sp)
check("/session 文件 → 记下会话路径", r['verdict'] == 'handled'
      and r['state']['session'] == sp, str(r['state']))
r = handle('这句话是假的', r['state'])
check("开着会话给材料 → 诊断 + 记账（会话文件真的落盘）",
      r['verdict'] == 'material_diagnosed' and os.path.exists(sp), str(r['verdict']))
try:
    _st = json.load(io.open(sp, encoding='utf-8'))
    _ok = isinstance(_st, dict) and len(_st.get('turns') or []) == 1
except Exception as e:  # noqa: BLE001
    _ok = False
check("会话文件是合法 JSON 且记了 1 条轮次", _ok)
r = handle('/overview', r['state'])
check("/overview → 批次汇总（含轮次）",
      r['verdict'] == 'handled' and '轮次' in _joined(r), _joined(r)[:120])
r = handle('/state', r['state'])
check("/state → 当前状态汇总",
      r['verdict'] == 'handled' and '题型分布' in _joined(r), _joined(r)[:120])
_out = os.path.join(_tmp, '台账.md')
r = handle('/export ' + _out, r['state'])
check("/export 文件 → 真导出台账文件",
      r['verdict'] == 'handled' and os.path.exists(_out), str(r['verdict']))

# ── 三、纪律：不代签复核 + 缺参不猜
r = handle('/mark S05 ok')
check("/mark → 明确拒绝，并指出落笔在命令行（不代签复核）",
      r['verdict'] == 'error' and '不代签' in _joined(r)
      and '--mark' in _joined(r), _joined(r))
r = handle('/state')                      # 新开一台、没有会话
check("没有会话就敲会话类命令 → 诚实报错并给办法（不猜）",
      r['verdict'] == 'error' and '/session' in _joined(r), _joined(r))
r = handle('/export')
check("/export 缺文件且没开会话 → 先报更根本的阻塞（没开会话）",
      r['verdict'] == 'error' and '/session' in _joined(r), _joined(r))
r = handle('/export', new_state(sp))
check("/export 有会话但没给文件 → 报用法（不猜文件名）",
      r['verdict'] == 'error' and '用法' in _joined(r), _joined(r))
r = handle('/revise 3', new_state(sp))
check("/revise 只给轮次不给命题式 → 报用法（命题式由人给）",
      r['verdict'] == 'error' and '命题式' in _joined(r), _joined(r))
r = handle('/不存在的命令')
check("未知命令 → 报错 + 指 /help（不当成材料）",
      r['verdict'] == 'error' and '/help' in _joined(r), _joined(r))
r = handle('/json 也许')
check("/json 非法值 → 报用法", r['verdict'] == 'error', _joined(r))

# ── 四、JSON 模式与退出
r = handle('/json on')
check("/json on → 记下状态", r['verdict'] == 'handled' and r['state']['json'] is True)
r = handle('/stats', r['state'])
try:
    _parsed = json.loads(_joined(r))
    _ok = 'scenes' in _parsed and 'coverage' in _parsed
except Exception:  # noqa: BLE001
    _ok = False
check("JSON 模式下命令输出是合法 JSON（可喂给脚本）", _ok, _joined(r)[:120])
r = handle('/json off', r['state'])
check("/json off → 关掉 JSON", r['state']['json'] is False)
for w in ('/quit', '/q'):
    r = handle(w, r['state'])
    check("%s → 请求退出" % w, r['quit'] is True and r['verdict'] == 'quit')

# ── 五、接口形态与边界声明
check("机制形态 run({line}) 与 handle 等价",
      repl_run({'line': '/help'})['verdict'] == 'help'
      and repl_run({'line': ''})['verdict'] == 'idle')
check("run 可带初始会话（state 由它构造）",
      repl_run({'line': '/state', 'session': sp})['state']['session'] == sp)
check("边界声明写明：薄前端 / 不代签 / 不偷偷落文件",
      all(k in handle('/help')['boundary'] for k in ('薄前端', '不代签', '不偷偷')))
check("状态结构带会话路径与轮次计数",
      set(('session', 'turns', 'json')) <= set(new_state('x.json').keys()))

# ── 八、整篇材料导入与开关（/file /clues /struct）
_mf = os.path.join(_tmp, '材料.md')
io.open(_mf, 'w', encoding='utf-8').write(
    '需求既要三周上线又要十二周合规\n\n这句话是假的\n\n样本只有一百人靠不靠谱\n')
_s2 = os.path.join(_tmp, 's2.json')
st8 = handle('/session ' + _s2)['state']
st8 = handle('/clues on', st8)['state']
check("/clues on → 记下开关", st8['clues'] is True)
r = handle('/file ' + _mf, st8)
st8 = r['state']
check("/file 整篇材料 → 逐段诊断并记账（3 段）",
      r['verdict'] == 'handled' and '材料导入' in _joined(r)
      and '3 段' in _joined(r), _joined(r)[:150])
try:
    _s = json.load(io.open(_s2, encoding='utf-8'))
    _ok = len(_s.get('turns') or []) == 3
except Exception:  # noqa: BLE001
    _ok = False
check("/file 之后会话里真有 3 条轮次", _ok)
check("/file 缺文件名校 → 报用法（不猜）",
      handle('/file', st8)['verdict'] == 'error'
      and '用法' in _joined(handle('/file', st8)))
check("/file 坏选项 → 报错并给用法",
      handle('/file ' + _mf + ' 瞎写', st8)['verdict'] == 'error'
      and '看不懂的选项' in _joined(handle('/file ' + _mf + ' 瞎写', st8)))
r = handle('/file ' + _mf + ' line chunk 2', st8)
check("/file 分段+分块 → 走分块导入（有进度、可续跑）",
      r['verdict'] == 'handled', _joined(r)[:150])
st8 = r['state']
r = handle('/struct {"A":"快","B":"稳","wA":5,"wNotA":5}', st8)
st8 = r['state']
check("/struct 挂结构化线索（合法 JSON）→ 记下",
      r['verdict'] == 'handled' and st8['structured'], _joined(r))
_before_struct = st8['structured']
r = handle('/struct 不是json', st8)
check("/struct 坏 JSON → 报错且不挂（状态不变、不猜）",
      r['verdict'] == 'error' and st8['structured'] == _before_struct,
      _joined(r))
check("/struct 空参 → 显示当前挂的是什么",
      '当前结构化线索' in _joined(handle('/struct', st8)))
r = handle('产品既要快又要稳', st8)
check("挂了线索后材料真跑构件（执行里出现真跑）",
      '【执行】' in _joined(r) or '真跑' in _joined(r), _joined(r)[:150])
r = handle('/struct clear', st8)
check("/struct clear → 清掉线索", r['verdict'] == 'handled'
      and r['state']['structured'] is None, _joined(r))

# ── 六、端到端：子进程 + 管道跑真循环
_ep = os.path.join(_tmp, 'e2e.json')
_lines = '\n'.join(['/session ' + _ep, '需求既要三周上线又要十二周合规',
                    '/overview', '/quit']) + '\n'
_proc = subprocess.run([sys.executable, '-m', 'engine.cli', '--repl'],
                       input=_lines, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=_REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
_out_text = (_proc.stdout or '') + (_proc.stderr or '')
check("管道喂命令能跑真循环并正常退出（exit=0）",
      _proc.returncode == 0, f'rc={_proc.returncode} {_out_text[-200:]}')
check("端到端：材料被记账（轮次 1）且批次汇总出来了",
      '记下第 1 条' in _out_text and '批次汇总' in _out_text, _out_text[-200:])
check("端到端：会话文件被真写出来", os.path.exists(_ep))

# ── 七、只读纪律：全程不动场景表
check("交互台全程不改场景表（sha256 前后一致）", _sha(_SCENES) == _sha_before)
check("没往仓库里落文件（会话/台账都在临时目录）",
      all(os.path.dirname(p).startswith(tempfile.gettempdir())
          for p in (sp, _out, _ep)))

print("=" * 60)
print(f"结果: {PASS}/43 通过")
raise SystemExit(0 if PASS == 43 else 1)
