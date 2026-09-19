# -*- coding: utf-8 -*-
"""
test_review_marks.py — 正式测试：复核落笔（写回场景表）
用例依据：轨 B 场景库目录化 + 复核纪律（人验证引擎）+ 仓库纪律
         「测试不许改动被跟踪文件」
运行：python engine/scenarios/test_review_marks.py
"""
import hashlib
import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.scenarios.review_marks import (  # noqa: E402
    SCENES_PATH, mark_scene, review_state)

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


def read(path):
    with io.open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scene_block(text, scene_id):
    anchor = "'id': '%s'," % scene_id
    i = text.find(anchor)
    j = text.find('\n    {\n', i)
    return text[i:j if j > 0 else len(text)]


print("复核落笔 · 正式测试")
print("=" * 60)

# 全部写回用例都在临时副本上做（仓库纪律：测试不许动被跟踪文件）
tmpdir = tempfile.mkdtemp(prefix='pe_review_')
tmp = os.path.join(tmpdir, 'scenarios.py')
shutil.copyfile(SCENES_PATH, tmp)

real_before = sha(SCENES_PATH)
before = read(tmp)
st0 = review_state(tmp)

# ── 用例1：落笔「正确」
r = mark_scene('S05', 'ok', note='期望与实际一致', path=tmp)
check("落笔返回 ok 且 changed=True", r['ok'] and r['changed'], str(r))
check("落笔后 checked=True", r['checked'] is True, str(r['checked']))
after = read(tmp)
check("场景表出现 review 记录与『正确』",
      "'review': '正确（" in after and "'checked': True," in after)
check("写回后的场景表仍是合法 Python",
      bool(compile(after, tmp, 'exec')))
check("行尾仍为 LF（无 CR）", '\r' not in after)
check("只动目标场景：S04 / S06 段落逐字节不变",
      scene_block(before, 'S04') == scene_block(after, 'S04')
      and scene_block(before, 'S06') == scene_block(after, 'S06'))

# ── 用例2：复核分布跟着变
st1 = review_state(tmp)
check("分布：待复核 -1、正确 +1",
      st1['pending'] == st0['pending'] - 1 and st1['ok'] == st0['ok'] + 1,
      f"{st0} → {st1}")

# ── 用例3：重复落笔同一结论 → 幂等（不changed）
r2 = mark_scene('S05', 'ok', note='期望与实际一致', path=tmp)
check("同结论重复落笔：changed=False（幂等）",
      r2['ok'] and r2['changed'] is False, str(r2))
check("幂等落笔后文件字节不变", read(tmp) == after)

# ── 用例4：误判 / 边界 / 退回
r3 = mark_scene('S06', 'wrong', note='判成 T2，期望 T8', path=tmp)
t3 = read(tmp)
check("误判-待修：checked 仍为 True 且记录『误判-待修』",
      r3['ok'] and r3['checked'] is True and "'review': '误判-待修（" in t3)
r4 = mark_scene('S07', 'edge', path=tmp)
_block7 = scene_block(read(tmp), 'S07').split("'review': ", 1)[1][:20]
check("边界情况：不带备注时记录里不留多余冒号",
      r4['ok'] and "'review': '边界情况（" in read(tmp) and '：' not in _block7,
      _block7)
r5 = mark_scene('S05', 'pending', path=tmp)
t5 = read(tmp)
check("退回待复核：checked=False 且 review 记录被清掉",
      r5['ok'] and "'checked': False" in scene_block(t5, 'S05')
      and "'review'" not in scene_block(t5, 'S05'))
check("退回后场景表仍是合法 Python", bool(compile(t5, tmp, 'exec')))

# ── 用例5：诚实拦截（一个字节都不许改）
before_bad = sha(tmp)
bad1 = mark_scene('S99', 'ok', path=tmp)
check("未知场景 id → 诚实拦截（列出可用 id）",
      not bad1['ok'] and 'S99' in bad1['error'] and 'S01' in bad1['error'],
      str(bad1))
bad2 = mark_scene('S05', 'maybe', path=tmp)
check("结论取值非法 → 诚实拦截",
      not bad2['ok'] and 'ok / wrong / edge / pending' in bad2['error'],
      str(bad2))
bad3 = mark_scene('all', 'ok', path=tmp)
check("不接受 all（复核要逐个看）",
      not bad3['ok'] and 'all' in bad3['error'], str(bad3))
bad4 = mark_scene('S05', 'ok', note=123, path=tmp)
check("备注非字符串 → 诚实拦截（不硬转）",
      not bad4['ok'] and '必须是字符串' in bad4['error'], str(bad4))
check("四次非法调用的文件字节完全没变", sha(tmp) == before_bad)

# ── 用例6：备注里的引号/反斜杠不破坏字面量
r6 = mark_scene('S08', 'ok', note="含 ' 单引号 与 \\ 反斜杠", path=tmp)
t6 = read(tmp)
check("备注含引号/反斜杠 → 仍能编译且写进去了",
      r6['ok'] and bool(compile(t6, tmp, 'exec'))
      and '反斜杠' in scene_block(t6, 'S08'))

# ── 用例7：仓库里的真场景表没被测试碰过
check("测试未改动被跟踪的场景表（前后 sha256 一致）",
      sha(SCENES_PATH) == real_before)

# ── 用例8：CLI 侧（只测诚实拦截与守卫，不写真文件）
sys.path.insert(0, os.path.join(_REPO, 'engine'))
from engine.cli import main  # noqa: E402

check("CLI：--verdict 不配 --mark → 退出码 2", main(['--verdict', 'wrong']) == 2)
check("CLI：--note 不配 --mark → 退出码 2", main(['--note', '随便写']) == 2)
check("CLI：--mark S99（不存在的场景）→ 退出码 2",
      main(['--mark', 'S99']) == 2)
check("CLI 三次拦截后真场景表仍未变", sha(SCENES_PATH) == real_before)

shutil.rmtree(tmpdir, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/24 通过")
raise SystemExit(0 if PASS == 24 else 1)
