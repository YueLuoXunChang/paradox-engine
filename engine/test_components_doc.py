# -*- coding: utf-8 -*-
"""
test_components_doc.py — 正式测试：构件参考自动生成（docs/components.md）
用例依据：索引/参考不能靠人肉维护（查索引时曾发现 README 树漏登记 9 个模块）
运行：python engine/test_components_doc.py
"""
import io
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

from engine import _components_doc as cd  # noqa: E402

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


print("构件参考 · 正式测试")
print("=" * 60)

text = cd.render()
check("生成器能产出内容", text.startswith('# 构件参考') and len(text) > 3000,
      str(len(text)))
check("参考文件已落盘", os.path.exists(cd.DOC))
have = io.open(cd.DOC, encoding='utf-8').read() if os.path.exists(cd.DOC) else ''
check("落盘的参考与代码一致（漂移检查；改了代码忘了重生成会失败）",
      have == text,
      '文件 %d 字 vs 生成 %d 字' % (len(have), len(text)))

# 与生成器同一个来源（磁盘）：新增模块还没提交时 git ls-files 看不到，
# 用两份来源比会假报差异（这坑当场出现过）
_scan = cd.scan()
_mods = [it['path'] for v in _scan.values() for it in v]
n_doc = len([l for l in text.split('\n') if l.startswith('### `engine/')])
check("构件数 = 扫描到的非下划线非测试模块数",
      n_doc == len(_mods), '%d vs %d' % (n_doc, len(_mods)))
check("每个构件都有「做什么」（没有空说明）",
      '（无说明）' not in text and '无 docstring' not in text)
check("端口声明覆盖率 ≥30 个构件（其余诚实标未声明）",
      text.count('- 输入端口：') >= 30, str(text.count('- 输入端口：')))
check("参考里不含私有档案章节号（沿用发布面口径）",
      cd.__name__ and not any(
          n in text for n in ('详规 §', '总架构 §', '公式源 §')))

d = tempfile.mkdtemp(prefix='pe_cdoc_')
try:
    fake = os.path.join(d, 'components.md')
    io.open(fake, 'w', encoding='utf-8', newline='\n').write('手改过的参考\n')
    real_doc, cd.DOC = cd.DOC, fake
    orig_argv = sys.argv
    sys.argv = ['x', '--check']
    try:
        buf = io.StringIO()
        code = cd.main(['--check'])
    finally:
        cd.DOC = real_doc
        sys.argv = orig_argv
    check("--check 对手改过的参考报不一致（返回 1）", code == 1, str(code))
    check("--check 对一致的文件返回 0", cd.main(['--check']) == 0)
finally:
    import shutil
    shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/9 通过")
raise SystemExit(0 if PASS == 9 else 1)
