# -*- coding: utf-8 -*-
"""
test_doc_examples_live.py — 文档示例**真跑一遍**
================================================================
为什么要有这条：`test_doc_commands.py` 只证明"示例里的旗标名字对"，
证明不了"这条命令真能跑通"。读者复制 README 里的命令，跑不通就是跑不通。

做法：把中英 README 里带旗标的命令示例提取出来，**把占位路径换成临时路径**，
逐条真调 CLI，断言退出码与产出。有副作用的示例**不在此列**：
    --mark（会写场景表，那是作者的落笔动作）· --demo（跑整段演示，重）
对 --mark 改用派生检查：跑 `--mark S99`（不存在的场景）应当退 2 且场景表不变——
既能证明这条路是活的，又不会替作者落笔。

运行：python engine/test_doc_examples_live.py
"""
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli import main  # noqa: E402

PASS = 0

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


def run_cli(*argv):
    buf = io.StringIO()
    code = 0
    try:
        with redirect_stdout(buf):
            code = main(list(argv))
    except SystemExit as e:
        code = e.code if e.code is not None else 0
    return code, buf.getvalue()


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


_CMD = re.compile(r'(?:paradox-engine|python -m engine\.cli)\s+([^\n`]*)')

print("文档示例真跑 · 测试")
print("=" * 60)

d = tempfile.mkdtemp(prefix='pe_docs_live_')
sess = os.path.join(d, '会话.json')
mat = os.path.join(d, '材料.md')
inp = os.path.join(d, '输入.txt')
with io.open(mat, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('产品既要三周上线又要十二周合规\n\n这句话是假的\n')
with io.open(inp, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('产品既要快又要稳\n')
big = os.path.join(d, 'big.md')
with io.open(big, 'w', encoding='utf-8', newline='\n') as fh:
    for i in range(1, 51):        # 大材料示例要真有 50 段才跑得动
        fh.write('第 %d 段：产品既要快又要稳' % i + '\n\n')

scen = os.path.join(_HERE, 'scenarios', 'scenarios.py')
scen_sha = sha(scen)

# 占位符 → 临时路径（文档里写的是示例名，跑的时候得换成真路径）
SUBS = {'会话.json': sess, 's.json': sess, '材料.md': mat,
        'material.md': mat, '台账.md': None, 'ledger.md': None,
        '工作单.md': None, '简报.md': None, '输入.txt': inp,
        '大材料.md': big, 'big.md': big,
        '复核包.md': None, 'packet.md': None}
SKIP_REASONS = {}


def _repo_state():
    """仓库当前状态（未跟踪文件也算）——用来查"真跑有没有往仓库里落东西"。"""
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=_REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return sorted(p.stdout.split('\n'))


_state_before = _repo_state()
_root_before = set(os.listdir(_REPO))


def prepare(frag, doc, idx):
    body = frag.split('#')[0].strip()
    try:
        toks = shlex.split(body)
    except ValueError:
        return None, '引号不配对'
    if re.search(r'--[a-z-]+/', frag):        # 散文式列举（--text/--json/--file）
        return None, '散文式列举不是命令'
    if '--mark' in toks:
        return None, '落笔动作（会写场景表），改用派生检查'
    if '--demo' in toks:
        return None, '整段演示，太重'
    out = []
    for tk in toks:
        if tk in SUBS:
            rep = SUBS[tk]
            if rep is None:                   # 产出文件：**每个示例各用一个**
                base, ext = os.path.splitext(tk)
                rep = os.path.join(d, '%s-%s%d%s' % (base, doc, idx, ext))
                # 不复用：两个示例都写同一个路径时，第二个会撞上
                # 「已存在默认不覆盖」而退 2（那是别的用例在测的行为）
            out.append(rep)
        else:
            out.append(tk)
    return out, None


examples = []
for doc in ('README.md', 'README.en.md'):
    t = io.open(os.path.join(_REPO, doc), encoding='utf-8').read()
    for idx, m in enumerate(_CMD.finditer(t), 1):
        frag = m.group(1).strip()
        if '--' not in frag:
            continue
        argv, why = prepare(frag, doc.split('.')[0], idx)
        if argv is None:
            SKIP_REASONS.setdefault(why, []).append(frag.split('#')[0].strip()[:60])
        else:
            examples.append((doc, frag.split('#')[0].strip()[:70], argv))

check("提取到可安全真跑的示例 ≥ 18 条", len(examples) >= 18,
      str(len(examples)))
check("跳过的只有「落笔动作/整段演示/散文式列举」这几类",
      set(SKIP_REASONS) <= {'落笔动作（会写场景表），改用派生检查',
                            '整段演示，太重', '散文式列举不是命令'},
      str({k: len(v) for k, v in SKIP_REASONS.items()}))

fails, empties, json_bad = [], [], []
for doc, shown, argv in examples:
    code, out = run_cli(*argv)
    if code != 0:
        fails.append((doc, shown, code, out[-120:]))
    if not out.strip():
        empties.append((doc, shown))
    if '--json' in argv:
        try:
            json.loads(out)
        except ValueError as e:
            json_bad.append((shown, str(e)))

check("示例逐条真跑：退出码全为 0", not fails,
      '; '.join('%s → %s（%s）' % f[:3] for f in fails[:4]))
check("示例逐条真跑：都有输出（不是空跑）", not empties,
      str([e[1] for e in empties][:4]))
check("带 --json 的示例输出能被解析", not json_bad, str(json_bad[:3]))
check("中英 README 的示例都被跑到",
      {doc for doc, _, _ in examples} == {'README.md', 'README.en.md'},
      str({doc for doc, _, _ in examples}))

# ── 写文件的示例确实产出文件
made = [os.path.join(d, f) for f in os.listdir(d)
        if f.startswith(('台账-', 'ledger-')) and f.endswith('.md')]
check("导出类示例真的写出了文件（且非空）",
      made and all(os.path.exists(p) and os.path.getsize(p) > 0
                   for p in made), str(made))

# ── 派生检查：落笔那条不能用不存在的场景生效，且场景表不动
code, out = run_cli('--mark', 'S99', '--verdict', 'ok')
check("派生：--mark S99 退 2（不替作者落笔、也不误落）",
      code == 2, f"exit={code}")
check("真跑全程没有改动场景表（sha256 一致）", sha(scen) == scen_sha)

# ── 真跑产生的会话/产出都落在临时目录，且不留半成品
check("临时目录里没有 .session- 残留（原子写收尾干净）",
      not [f for f in os.listdir(d) if f.startswith('.session-')],
      str([f for f in os.listdir(d) if f.startswith('.session-')]))
sess_ok = os.path.exists(sess) and isinstance(
    json.loads(io.open(sess, encoding='utf-8').read()), dict)
check("会话示例跑出的会话文件是合法 JSON", sess_ok)
# 这条原先只按文件名前缀查（台账/ledger/.session-），于是新示例落下的
# 「复核包.md / packet.md」没被认出来、还进了提交——改成**比对仓库整体状态**：
# 真跑一条示例都不许往仓库里留东西（新文件、改动的文件都算）。
_new_root = sorted(set(os.listdir(_REPO)) - _root_before)
_state_after = _repo_state()
check("真跑不往仓库里落文件（仓库状态前后一致，不只查文件名前缀）",
      not _new_root and _state_after == _state_before,
      '新出现的根文件：%s；git status 变化：%s'
      % (_new_root, [x for x in _state_after if x not in _state_before][:4]))

shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/12 通过")
raise SystemExit(0 if PASS == 12 else 1)
