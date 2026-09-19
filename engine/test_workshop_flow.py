# -*- coding: utf-8 -*-
"""
test_workshop_flow.py — 端到端走查：一条工作流从材料到台账
================================================================
用途：会话台账 / 场景复核 / 复核落笔 / 批次汇总 / 台账导出 四块各自有测试，
      这里跑**一条完整工作流**把它们串起来，断言各步产物互相自洽
      （跨块回归：单块绿不等于串起来绿）。

不做什么：**不替作者落笔**——流程里只跑到 --review（记依据），
      场景表的 `checked` 一个字都不改（本文件用 sha256 守着）。
运行：python engine/test_workshop_flow.py
"""
import hashlib
import io
import json
import os
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
    """跑 CLI main，捕获 stdout，返回 (exit_code, stdout_text)。"""
    buf = io.StringIO()
    code = 0
    try:
        with redirect_stdout(buf):
            code = main(list(argv))
    except SystemExit as e:
        code = e.code if e.code is not None else 0
    return code, buf.getvalue()


def read(path):
    with io.open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


print("工作流端到端走查 · 正式测试")
print("=" * 60)

d = tempfile.mkdtemp(prefix='pe_flow_')
mat = os.path.join(d, '材料.md')
sess = os.path.join(d, '会话.json')
ledger = os.path.join(d, '台账.md')
scen_path = os.path.join(_HERE, 'scenarios', 'scenarios.py')
scen_before = sha(scen_path)

MATERIAL = ('产品既要三周上线抢占市场，又要十二周合规审查\n\n'
            '原来以为这个方案要十二周，现在发现三周就行\n\n'
            '研究说这种肥料增产有效，另一份研究说无效，数据互相矛盾\n\n'
            '这句话是假的，反复震荡\n')
with io.open(mat, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(MATERIAL)

try:
    # ── 第 1 步：导材料 → 逐段诊断记账
    code, out = run_cli('--session', sess, '--add-file', mat)
    st_json = json.loads(read(sess))
    check("① 导材料 exit=0 且四段都记下",
          code == 0 and len(st_json['turns']) == 4, out[-200:])
    check("① 每段的判类/复杂度都取自引擎（有值）",
          all(t['type'] and t['level'] for t in st_json['turns']),
          str([(t['type'], t['level']) for t in st_json['turns']]))

    # ── 第 2 步：挂一条 T5 材料的信念修正
    t5_ix = [t['i'] for t in st_json['turns'] if t['type'] == 'T5']
    check("② 材料里确实有被判成 T5 的（否则本流程少一环）",
          bool(t5_ix), str([t['type'] for t in st_json['turns']]))
    code, out = run_cli('--session', sess, '--revise', '¬Q', '--beliefs',
                        'P→Q,P', '--turn', str(t5_ix[0]))
    check("② 挂轮次修正 exit=0 且记下 source_turn",
          code == 0 and json.loads(read(sess))['revisions'][0]['source_turn']
          == t5_ix[0], out[-160:])

    # ── 第 3 步：复核依据落账（只记依据，不落笔）
    code, out = run_cli('--session', sess, '--review', '--scene', 'S13')
    st_json = json.loads(read(sess))
    check("③ 复核依据进会话 exit=0",
          code == 0 and len(st_json['reviews']) == 1,
          out[-160:])
    check("③ 复核记录带期望/实际/命中信号",
          st_json['reviews'][0]['expect'] and st_json['reviews'][0]['actual']
          and st_json['reviews'][0]['signals'], str(st_json['reviews'][0]))
    check("③ 记依据不等于落笔：场景表 sha256 未变",
          sha(scen_path) == scen_before)

    # ── 第 4 步：批次汇总
    code, out = run_cli('--session', sess, '--overview')
    check("④ 批次汇总 exit=0 且列出判类分布",
          code == 0 and '判类 T' in out, out[:200])
    check("④ 汇总里的轮次数与会话文件一致",
          ('轮次 %d' % len(st_json['turns'])) in out, out[:160])
    check("④ 汇总带 T5 对接情况（已接/还欠）",
          'T5（知识更新）材料' in out and '已接信念集' in out, out[-400:])

    # ── 第 5 步：导台账
    code, out = run_cli('--session', sess, '--export', ledger)
    body = read(ledger)
    check("⑤ 导台账 exit=0 且文件落地",
          code == 0 and os.path.exists(ledger), out[-160:])
    for sec in ('## 批次汇总', '## 逐条诊断', '## 场景复核记录',
                '## 信念修正史', '## 边界'):
        check(f"⑤ 台账含「{sec}」段", sec in body)
    check("⑤ 台账行尾 LF（无 CR）", '\r' not in body)
    check("⑤ 台账逐条诊断条数 = 会话轮次数",
          body.count('\n### ') == len(st_json['turns']),
          str(body.count('\n### ')))
    check("⑤ 台账修正史写出「挂在轮次 N」",
          ('挂在轮次 %d' % t5_ix[0]) in body)
    check("⑤ 台账复核段含 S13 与当前标记列",
          'S13' in body and '当前复核标记' in body)

    # ── 第 6 步：台账与汇总数字自洽（跨块一致性）
    code, out = run_cli('--session', sess, '--overview')
    per_type = {}
    for t in st_json['turns']:
        per_type[t['type']] = per_type.get(t['type'], 0) + 1
    check("⑥ 汇总的每个判类计数都能在台账里找到",
          all(('判类 %s：%d 条' % (k, v)) in out
              for k, v in per_type.items()), out[:300])
    check("⑥ 台账批次汇总段的轮次数与汇总一致",
          ('- 轮次 %d' % len(st_json['turns'])) in body,
          [l for l in body.split('\n') if l.startswith('- 轮次')][:1])

    # ── 第 7 步：重复导出默认不覆盖
    ledger_sha = sha(ledger)
    code, out = run_cli('--session', sess, '--export', ledger)
    check("⑦ 再导一次（不覆盖）→ exit 2 且台账字节不变",
          code == 2 and sha(ledger) == ledger_sha, out[-160:])

    # ── 第 8 步：真入口（子进程）也能跑通
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, '-m', 'engine.cli', '--session',
                        sess, '--overview'], cwd=_REPO, env=env,
                       capture_output=True)
    sout = p.stdout.decode('utf-8', 'replace')
    check("⑧ 子进程跑 python -m engine.cli --overview 退出 0",
          p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-200:])
    check("⑧ 子进程输出含批次汇总标题",
          '批次汇总' in sout, sout[:160])

    # ── 第 9 步：全程不改场景表、不残留临时文件
    check("⑨ 走完整条流程后场景表仍未被改动",
          sha(scen_path) == scen_before)
    check("⑨ 工作目录没留临时文件",
          not [f for f in os.listdir(d) if f.startswith('.session-')],
          str(os.listdir(d)))
    check("⑨ 会话文件仍是合法 JSON 且 LF",
          isinstance(json.loads(read(sess)), dict)
          and '\r' not in read(sess))

    # ── 第 10 步：清空后重导 → 诚实报空（不产出假台账）
    code, out = run_cli('--session', sess, '--session-reset')
    check("⑩ 清空会话 exit=0", code == 0, out[-160:])
    code, out = run_cli('--session', sess, '--export', '-')
    check("⑩ 空会话导台账 → exit 2（不编内容）", code == 2, out[-160:])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/30 通过")
raise SystemExit(0 if PASS == 30 else 1)
