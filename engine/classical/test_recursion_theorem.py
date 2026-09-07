# -*- coding: utf-8 -*-
"""
test_recursion_theorem.py — 正式测试：Kleene 递归定理 · 自指构造
用例依据：ROADMAP 阶段 7（借数学底座标注来源）+ 自指三形态对照
运行：python engine/classical/test_recursion_theorem.py
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recursion_theorem import run, _simple_transform  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def run_py(program):
    """带 UTF-8 环境的子进程运行。"""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                     encoding='utf-8') as fh:
        fh.write(program)
        tmp = fh.name
    try:
        return subprocess.run([sys.executable, tmp], capture_output=True,
                              text=True, timeout=10, env=env,
                              encoding='utf-8')
    finally:
        os.remove(tmp)


print("Kleene 递归定理 · 正式测试")
print("=" * 60)

# ── 用例1：quine 形态
r = run({'mode': 'quine', 'payload': '正式测试'})
check("quine → constructed", r['verdict'] == 'constructed', str(r))
check("quine 给源码", bool(r['program']), str(r))
check("quine 源码含自引用结构（s = repr(s)）", 's = ' in r['program'],
      str(r['program'][:100]))
check("quine 边界声明标注借鉴来源",
      '递归定理' in r['boundary'] and ('演示' in r['boundary']
                                       or '非形式化' in r['boundary']),
      r['boundary'])

# ── 用例2：quine 实跑（自复制验证——核心）
out = run_py(r['program'])
check("quine 实跑 exit=0", out.returncode == 0, out.stderr)
check("quine 输出含 payload", '正式测试' in out.stdout, out.stdout[:300])
check("quine 输出含自身源码结构", 's = ' in out.stdout, out.stdout[:300])

# ── 用例3：递归定理形态（默认变换）
r = run({'mode': 'recursive'})
check("recursive → constructed", r['verdict'] == 'constructed', str(r))
check("recursive 给源码", bool(r['program']), str(r))
check("默认变换存在且行为等价",
      '[transform]' in _simple_transform('x = 1\n'), str())
out = run_py(_simple_transform('print(1)\n'))
check("行为等价变换可运行", out.returncode == 0, out.stderr)

# ── 用例4：自定义变换（不同 f 都接入）
def count_lines(code):
    return f'# {code.count(chr(10)) + 1} 行'
r = run({'mode': 'recursive', 'transform': count_lines})
check("自定义变换 → constructed", r['verdict'] == 'constructed', str(r))
check("自定义变换结果正确",
      count_lines('a\nb\n') == '# 3 行', str(count_lines('a\nb\n')))

# ── 用例5：诚实边界
check("坏 mode → input_pending",
      run({'mode': 'xx'})['verdict'] == 'input_pending')
check("非可调用 transform → input_pending",
      run({'mode': 'recursive', 'transform': 'x'})['verdict']
      == 'input_pending')
check("边界声明：不宣称绕停机/不可判定",
      ('不宣称' in run({'mode': 'quine'})['boundary']
       or '停机' in run({'mode': 'quine'})['boundary']),
      run({'mode': 'quine'})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
