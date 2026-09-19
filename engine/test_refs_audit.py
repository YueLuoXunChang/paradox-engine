# -*- coding: utf-8 -*-
"""
test_refs_audit.py — 正式测试：私有档案引用清点（只列不改）
用例依据：发布面红线「指向私有档案的章节引用」需要清点，但清或留是作者口径
运行：python engine/test_refs_audit.py
"""
import hashlib
import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

from engine._refs_audit import audit, report_text, scan_file, text_files  # noqa: E402

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


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


print("私有档案引用清点 · 正式测试")
print("=" * 60)

d = tempfile.mkdtemp(prefix='pe_refs_')
try:
    # ── 判据：三种形态
    f1 = os.path.join(d, 'a.py')
    with io.open(f1, 'w', encoding='utf-8', newline='\n') as fh:
        # 拼接构造：文件里不出现「档案名 + 章节号」的完整字面量
        fh.write('# ' + '详规' + '：第 3 层冷门详规 ' + '§' + '三（非单调）\n')
    h1 = scan_file(f1)
    check("识别「私有档案名 + 章节号」",
          len(h1) == 1 and h1[0][2] == '私有档案名+章节号', str(h1))

    f2 = os.path.join(d, 'b.md')
    with io.open(f2, 'w', encoding='utf-8', newline='\n') as fh:
        # 样例拼接构造：本文件里不出现完整的内部文档编号字面量
        # （发布面判据会抓「两位数字打头 + _ + .md」这种写法）
        fh.write('参考 ' + '4' + '5_长期架构蓝图.md' + ' 与 '
                 + '1' + '2_路径与符号速查.md' + '\n')
    h2 = scan_file(f2)
    check("识别「编号型指针（NN_xxx.md）」",
          len(h2) == 2 and all(x[2] == '编号型指针' for x in h2), str(h2))

    f3 = os.path.join(d, 'c.md')
    with io.open(f3, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('本仓章节见 docs/ROADMAP.md §6.4 与 README §二\n')
    check("本仓内章节引用不误报（读者打得开）", scan_file(f3) == [],
          str(scan_file(f3)))

    f4 = os.path.join(d, 'd.py')
    with io.open(f4, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# 冷门按' + '详规' + '§一~§五全部接入完成\n')
    h4 = scan_file(f4)
    check("同一行同一段上下文只记一处（不重复计数）", len(h4) == 1, str(h4))

    f5 = os.path.join(d, 'e.py')
    with io.open(f5, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# ' + '公式卡' + ' §2.1 与 ' + '总架构' + ' §3.2 都算私有引用\n')
    check("多种私有档案名都认（公式卡 / 总架构）",
          len(scan_file(f5)) == 1, str(scan_file(f5)))

    # ── 全仓清点
    r = audit()
    # 2026-09-19：全仓私有引用已清完（章节号清成「来源：体系内部详规」），
    # 所以这里断言 **0**——再长回来会在这条现形
    check("全仓私有档案引用为 0（已清完，未清干净会现形）",
          r['total'] == 0 and r['files_hit'] == 0,
          '%d 处 / %d 文件: %s' % (r['total'], r['files_hit'],
                                   sorted(r['files'])[:4]))
    check("total = 各文件命中数之和",
          r['total'] == sum(len(v) for v in r['files'].values()))
    check("工具与判据自检文件不计入（它们必须写出这些名字）",
          all(x not in r['files'] for x in
              ('engine/_refs_audit.py', 'engine/test_public_face.py',
               'engine/test_refs_audit.py')), str(sorted(r['files'])[:3]))
    check("覆盖面与发布面判据同量级（≥80 文本文件）",
          len(text_files()) >= 80, str(len(text_files())))

    txt = report_text()
    # 清完之后清单是空的（0 处）——分组与行号只在有命中时才出现，
    # 所以这里改成校验「工具自己能对临时文件给出分组与行号」（上面已验）
    # 加上「空清单也说清口径」：
    check("空清单也给出分类与口径说明（不只剩一行标题）",
          '共 0 处' in txt and '只记一处' in txt and '偏保守' in txt,
          txt.split('\n')[2][:80])
    check("清单写明只列不改、清或留由作者定",
          '只列不改' in txt and '清或留由作者定' in txt)
    check("清单提醒别提交进公开仓", '别提交进公开仓' in txt)
    check("清单说明本仓章节引用不算", '本仓内章节引用' in txt)

    # 分类小计：有命中时按类给数；清完后为 0——两种情况都要给出「共 N 处，涉及 M 个文件」
    check("清单给出总数与涉及文件数（有命中时另带分类小计）",
          '处，涉及' in txt and '个文件' in txt, txt.split('\n')[2][:90])
    check("清单写明计数口径（同段上下文只记一处，数字偏保守）",
          '只记一处' in txt and '偏保守' in txt)

    # ── 只读
    sample = [os.path.join(_REPO, 'README.md'),
              os.path.join(_REPO, 'engine', 'cold', 'agm_revision.py')]
    before = {p: sha(p) for p in sample}
    audit()
    report_text()
    check("跑完不改任何文件（抽样 sha256 一致）",
          all(sha(p) == before[p] for p in sample))
finally:
    shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
