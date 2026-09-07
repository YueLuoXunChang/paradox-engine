# -*- coding: utf-8 -*-
"""
test_cli.py — 正式测试：命令行入口（CLI）
用例依据：A 批包化（pip install 后 console 命令可用；--text/--json/--file/--tools）
运行：python engine/cli/test_cli.py（或 python -m engine.cli.test_cli）
"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main  # noqa: E402

PASS = 0


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


print("CLI 命令行入口 · 正式测试")
print("=" * 60)

# ── 用例1：中文报告模式（T2 需求冲突端到端）
code, out = run_cli(
    '--text', '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
    '--structured',
    '{"A":"尽快上线(3周)","B":"完整合规(12周)","wA":5,"wNotA":5}')
check("中文报告 exit=0", code == 0, f"exit={code}")
check("报告含【类型】T2", '【类型】T2' in out, out[:200])
check("报告含【五查】", '【五查】' in out, out[:200])
check("报告含【边界】只诊断", '【边界】' in out and '只诊断' in out, out[-200:])

# ── 用例2：JSON 模式（说谎者 T6）
code, out = run_cli('--text', '这句话是假的', '--json')
check("JSON exit=0", code == 0, f"exit={code}")
check("JSON 含 main_type T6", '"main_type": "T6"' in out, out[:300])
check("JSON 含 report", '"report"' in out, out[:300])
import json as _json
parsed = _json.loads(out)
check("JSON 可解析且字段齐", parsed.get('main_type') == 'T6'
      and 'output_check' in parsed and 'report' in parsed, str(parsed)[:200])

# ── 用例3：--file 模式
tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tmp_in.txt')
with open(tmp, 'w', encoding='utf-8') as fh:
    fh.write('产品既要快又要稳')
try:
    code, out = run_cli('--file', tmp)
    check("--file exit=0", code == 0, f"exit={code}")
    check("--file 出报告", '【类型】' in out, out[:200])
finally:
    os.remove(tmp)

# ── 用例4：--tools
code, out = run_cli('--tools')
check("--tools exit=0", code == 0, f"exit={code}")
check("--tools 列工具", '可用工具' in out and '23' in out, out[:200])

# ── 用例5：缺文本 → exit 2 提示
code, out = run_cli()
check("缺文本 exit=2", code == 2, f"exit={code}")
check("缺文本给提示", '需给文本' in out, out[:200])

# ── 用例6：坏 structured JSON → exit 2
code, out = run_cli('--text', 'x', '--structured', '{bad json')
check("坏 JSON exit=2", code == 2, f"exit={code}")
check("坏 JSON 提示解析失败", '解析失败' in out, out[:200])

# ── 用例7：边界——只诊断声明在报告尾部
code, out = run_cli(
    '--text', '产品既要快又要稳',
    '--structured', '{"A":"要快","B":"要稳","wA":5,"wNotA":5}')
check("边界声明不决策", '只诊断不决策' in out or '不决策' in out, out[-300:])

print("=" * 60)
print(f"结果: {PASS}/17 通过")
raise SystemExit(0 if PASS == 17 else 1)
