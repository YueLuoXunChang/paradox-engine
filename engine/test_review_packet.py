# -*- coding: utf-8 -*-
"""
test_review_packet.py — 正式测试：场景复核包（给作者批阅待复核队列用）
======================================================================
为什么有它：
    待复核队列（现 24 个）是作者侧的事，引擎只能把**依据**摆整齐、不能替人下结论。
    复核包就是那件事：逐场景给材料原文 / 期望 vs 实际 / 命中信号 / 真跑构件 /
    场景说明 / 可粘贴落笔命令 + 留白。本文件把它的几条硬约束钉住：
    ① 默认只收**待复核**的场景（点名某个场景时照给）；
    ② **一个字节都不改场景表**（sha256 守着）；
    ③ 每个场景段必须齐活（原文、期望/实际、落笔命令、留白）；
    ④ 落盘默认**不覆盖**（与其它导出同一个口径）；
    ⑤ 不许出现"已替你判定"的说法（只摆依据）。
运行：python engine/test_review_packet.py
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

from engine.scenarios.scenarios import SCENES  # noqa: E402

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


def _cli(*args):
    p = subprocess.run([sys.executable, '-m', 'engine.cli'] + list(args),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=_REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print("场景复核包 · 正式测试")
print("=" * 60)

_sha_before = _sha(_SCENES)
_pending = [s['id'] for s in SCENES if not s.get('checked')]
_checked = [s['id'] for s in SCENES if s.get('checked')]

# ── 一、默认口径：只看待复核
code, out = _cli('--review', '--packet')
check("--review --packet 正常退出（exit=0）", code == 0, f'rc={code}')
_heads = re.findall(r'^## (\S+) · ', out, re.M)
check("默认只收待复核场景（默认不含已复核的）",
      set(_heads) == set(_pending) and not (set(_heads) & set(_checked)),
      f'包内 {len(_heads)} 个；已复核混进：{sorted(set(_heads) & set(_checked))}')
check("报头写明场景数与口径（只看还没落笔的）",
      f'共 {len(_pending)} 个场景' in out and '只看还没落笔的' in out,
      out.split('\n')[2][:80])

# ── 二、每个场景段齐活（原文 / 期望实际 / 命中信号 / 真跑 / 落笔命令 / 留白）
_blocks = out.split('\n---\n')[1:]
check("场景段数与待复核数一致", len(_blocks) == len(_pending),
      f'{len(_blocks)} vs {len(_pending)}')
_miss = []
for b in _blocks:
    sid = re.search(r'^## (\S+) · ', b, re.M)
    if not sid:
        _miss.append('（找不到场景号）')
        continue
    need = [f"paradox-engine --mark {sid.group(1)} --verdict ____",
            '**材料原文**', '```text', '期望：', '实际：', '判类命中：',
            '真跑构件：', '场景说明：', '**你的结论**']
    for n in need:
        if n not in b:
            _miss.append((sid.group(1), n))
check("每段都齐活（原文/期望实际/命中/真跑/说明/落笔命令/留白）",
      not _miss, str(_miss[:4]))
_texts = [s['text'] for s in SCENES if not s.get('checked')]
check("材料原文是完整给的（不截断——复核要看原文）",
      all((t[:20] in out) for t in _texts), '有场景原文没进包')

# ── 三、点名单个场景：照给（哪怕已复核过）
if _checked:
    code, out1 = _cli('--review', '--packet', '--scene', _checked[0])
    check("点名某个已复核场景 → 照给，并在报头写清是「指定场景」",
          code == 0 and f'指定场景 {_checked[0]}' in out1
          and f'## {_checked[0]} ·' in out1, out1.split('\n')[2][:80])

# ── 四、落盘：能写、默认不覆盖、确认可覆盖
_d = tempfile.mkdtemp(prefix='pe_packet_')
_pf = os.path.join(_d, '复核包.md')
code, out2 = _cli('--review', '--packet', '--packet-out', _pf)
check("--packet-out 真的落盘（Markdown 文件）",
      code == 0 and os.path.exists(_pf), f'rc={code} {out2[-120:]}')
check("落盘内容与打印口径一致（含全部待复核场景）",
      os.path.exists(_pf)
      and len(re.findall(r'^## ', io.open(_pf, encoding='utf-8').read(),
                         re.M)) == len(_pending))
_sz = os.path.getsize(_pf)
code, out3 = _cli('--review', '--packet', '--packet-out', _pf)
check("目标已存在 → 默认不覆盖（exit=2 且文件没动）",
      code == 2 and '默认不覆盖' in out3 and os.path.getsize(_pf) == _sz,
      f'rc={code}')
code, out4 = _cli('--review', '--packet', '--packet-out', _pf,
                  '--export-overwrite')
check("加 --export-overwrite → 允许覆盖（exit=0）", code == 0, f'rc={code}')

# ── 五、守卫与口径
code, out5 = _cli('--review', '--packet', '--scene', 'S99')
check("不存在的场景 → exit=2 并给可用清单",
      code == 2 and '不存在' in out5 and 'S01' in out5, f'rc={code}')
check("包里写明「结论是你的判断」与落笔格式（不替你写结论）",
      '结论是你的判断' in out and '--verdict ok|wrong|edge' in out)
check("包里没有「引擎已判定」这类越界说法",
      all(k not in out for k in ('引擎已判定', '已替作者', '已代签')))

# ── 六、只读纪律：全程不动场景表
check("复核包全程不改场景表（sha256 前后一致）", _sha(_SCENES) == _sha_before)
check("复核包里已复核场景的复核记录照实显示（有就写、没有就不写）",
      all(('已复核' in b) for b, s in zip(_blocks, SCENES)
          if s.get('checked')) or all(s['id'] not in _heads for s in SCENES
                                      if s.get('checked')))

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
