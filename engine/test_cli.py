# -*- coding: utf-8 -*-
"""
test_cli.py — 正式测试：命令行入口（CLI）
用例依据：A 批包化（pip install 后 console 命令可用；--text/--json/--file/--tools）
运行：python engine/cli/test_cli.py（或 python -m engine.cli.test_cli）
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

# 路径引导（本仓统一写法：钉本仓库根，防顶层包名撞车）
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli import main  # noqa: E402
from ai.tools import _TOOL_REGISTRY  # noqa: E402
from engine.scenarios.scenarios import SCENES as _SC  # noqa: E402

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
check("--tools 列工具", '可用工具' in out, out[:200])
check("--tools 列出全量工具（数=注册表，动态取、不硬编）",
      str(len(_TOOL_REGISTRY)) in out, out[:200])

# ── 用例4b：--scenarios / --scene（场景库暴露到命令行）
code, out = run_cli('--scenarios')
check("--scenarios exit=0", code == 0, f"exit={code}")
check("--scenarios 列场景（含复核状态与题型）",
      '场景库' in out and 'S01' in out and 'T2' in out, out[:200])
from engine.scenarios.scenarios import SCENES as _SC  # noqa: E402
check("--scenarios 场景数与注册表一致", str(len(_SC)) in out,
      f"{len(_SC)} vs {out[:60]}")
code, out = run_cli('--scenarios', '--json')
check("--scenarios --json exit=0", code == 0, f"exit={code}")
try:
    _d = json.loads(out)
    check("--scenarios --json 可解析且场景数与注册表一致",
          _d['count'] == len(_SC), str(_d)[:120])
except Exception as e:  # noqa: BLE001
    check("--scenarios --json 可解析且场景数与注册表一致", False, f'{e}')
code, out = run_cli('--scene', 'S01')
check("--scene S01 exit=0", code == 0, f"exit={code}")
check("--scene 输出期望 vs 实际", '期望' in out and '实际' in out, out[:200])
check("--scene 输出白箱（真跑/缺输入）",
      ('真跑' in out or '未跑' in out), out[:200])
code, out = run_cli('--scene', 'S99')
check("--scene 未知场景 → exit 2（不报假通过）", code == 2, f"exit={code}")
check("--scene 未知场景给可用清单", 'S01' in out and '不存在' in out, out[:150])

# ── 用例4c：--explain（判类白箱）/ --review / --stats
code, out = run_cli('--text', '这个调查说八成的人支持，样本只有一百人，靠不靠谱',
                    '--explain')
check("--explain exit=0", code == 0, f"exit={code}")
check("--explain 给出判类依据（主型+命中信号）",
      '判类依据' in out and '主型' in out and '命中' in out, out[-300:])
check("--explain 给出复杂度构成与路由依据",
      '复杂度' in out and '路由' in out and '置信度' in out, out[-300:])
check("--explain 声明是启发式（不吹完备）",
      '非语言学完备' in out, out[-200:])
code, out = run_cli('--text', '这句话是假的', '--explain')
check("--explain 与普通报告同时给（报告在前、依据在后）",
      '【类型】' in out and out.index('【类型】') < out.index('判类依据'),
      out[:200])

code, out = run_cli('--review', '--scene', 'S01')
check("--review exit=0", code == 0, f"exit={code}")
check("--review 给期望 vs 实际 + 判类命中",
      '期望' in out and '实际' in out and '判类命中' in out, out[:250])
check("--review 给复核状态与勾选指引",
      '复核状态' in out and 'checked=True' in out, out[:250])
check("--review 声明只诊断不决策", '只诊断不决策' in out, out[-160:])
code, out = run_cli('--review', '--scene', 'S99')
check("--review 未知场景 → exit 2", code == 2, f"exit={code}")

code, out = run_cli('--stats')
check("--stats exit=0", code == 0, f"exit={code}")
check("--stats 给场景数/通过/复核进度",
      '场景库统计' in out and '对照通过' in out and '待复核' in out,
      out[:250])
check("--stats 不报未完成的误判率（诚实）",
      '复核未完成' in out and '不报数' in out, out[-160:])
code, out = run_cli('--stats', '--json')
check("--stats --json 可解析且数字自洽", code == 0, f"exit={code}")
try:
    _d = json.loads(out)
    check("--stats --json 字段齐全且 checked+unchecked=scenes",
          all(k in _d for k in ('scenes', 'passed', 'checked', 'unchecked',
                                'per_type'))
          and _d['checked'] + _d['unchecked'] == _d['scenes'],
          str(_d)[:160])
except Exception as e:  # noqa: BLE001
    check("--stats --json 字段齐全且 checked+unchecked=scenes", False,
          f'{e}')

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
print(f"结果: {PASS}/43 通过")
raise SystemExit(0 if PASS == 43 else 1)
