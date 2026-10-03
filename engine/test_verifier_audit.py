# -*- coding: utf-8 -*-
"""test_verifier_audit.py — 验证方登记的正式测试（漂移 + 自洽 + 登记表 + 口径）

这份检查守的是**闸三"工具不可自证"**：产物**没有独立检验方时处于"未验状态"**。
所以本表要回答的不是"测试多不多"，而是"**有没有人（或另一套实现）独立验过**"。

四条守则：
  ① **漂移**：落盘产物必须等于现算（构件/测试一变就红，防表格过期）；
  ② **自洽**：五态互斥且完备（每件恰好一态）；证据列不许空；态词必须在词表里；
  ③ **登记表**（核心）：**"只有性质/接口测试"与"无测试引用"的件必须逐个登记**——
     新增一件只自证的构件，就得在这张表里加一个名字（签字），不许悄悄混过去；
  ④ **口径**：产物里必须写着"初筛不是终判"，且外部验证方的登记与文件**不许脱钩**
     （命中词必须在对应测试文件里真的出现）。

另外在本文件里**独立再算一遍**两件事（不借审计器的结论）：`untested` 的件确实没有任何
测试文件 **import** 它（AST 重扫）；跨构件互验的件确实被另一个构件**import** 过。
"""

import ast
import io
import re
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

from engine import _verifier_audit as VA                                    # noqa: E402

try:  # 控制台自愈：Windows GBK 控制台打印 emoji 会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

PASS = 0
TOTAL = 0


def check(label, cond, detail=''):
    global PASS, TOTAL
    TOTAL += 1
    if cond:
        PASS += 1
        print(f'  ✅ {label}')
    else:
        print(f'  ❌ {label}  {detail}')


# ── 登记表：**没有独立验证方**的件，逐个签字（新增一件就得改这里）
# 2026-10-02 更新（三次都在这天）：
#   ① `test_classical_crosscheck.py`（三条判定路随机对拍 + 自写 oracle）落地后，
#      `nd_propositional`、`resolution` 升到"独立复算"档 → 23 件变 21 件；
#   ② `test_fol_crosscheck.py`（三个 oracle 分别夹 monadic_fol / first_order /
#      equality_tableau）落地后，这三件也升档 → 21 件变 18 件；
#   ③ `test_modal_family_crosscheck.py`（模态求值 / 有限路径 LTL / CTL 定点三个独立求值器）
#      落地后，`ltl`、`modal` 升档（`model_check` 原本已在"独立复算"）→ **18 件变 16 件**。
KNOWN_NO_INDEPENDENT = {
    'ai_scenarios', 'converge_check',                     # 无测试引用
    'boundary_paradox', 'freeze_tool_schema',
    'lambda_calculus',
    'observer_bypass', 'paradox_annotate', 'paradox_measure', 'recursion_theorem',
    'repl', 'selfref_fixpoint', 'stlc', 'tools', 'truth_revision',
    'turing_machine', 'wall_pipeline',                    # 只有用例集/性质断言
}
# 点名了**外部验证方**的件（登记在审计器里，命中词必须出现在对应测试文件中）
KNOWN_EXTERNAL = {'criticality', 'growth_guard', 'bisimulation'}

rows, problems = VA.audit()
by_state = {}
for r in rows:
    by_state.setdefault(r['state'], []).append(r['comp'])
no_indep = sorted(set(by_state.get('property_only', [])) | set(by_state.get('untested', [])))

print('一、漂移与产物口径')
artifact = os.path.join(_REPO, 'docs', 'verifier_audit.md')
check('产物存在', os.path.exists(artifact), artifact)
text = io.open(artifact, encoding='utf-8').read() if os.path.exists(artifact) else ''
check('产物 == 现算（漂移检查）', text == VA.render(rows),
      '不一致：跑 python engine/_verifier_audit.py --write')
check('产物写着"自动生成、别手改"',
      '自动生成' in text and '别手改' in text)
check('口径警告在产物里：未验状态 + 初筛不是终判',
      '未验状态' in text and ('不是终判' in text or '**不是终判**' in text))
_drive = re.compile('[A-Za-z]:' + re.escape(chr(92)))   # 盘符路径：动态拼，别在源文件里写字面量
check('产物不含本机路径 / 私有记账引用（发布面红线）',
      _drive.search(text) is None and '落落' not in text and '账本 §' not in text)

print('二、自洽（五态互斥完备）')
states = set(VA.STATE_ORDER)
check('态词都在词表里', all(r['state'] in states for r in rows), sorted(set(r['state'] for r in rows)))
check('每件构件恰好一个态（五态互斥）',
      sum(len(v) for v in by_state.values()) == len(rows) == len(set(r['comp'] for r in rows)))
check('件数与扫盘构件数一致',
      len(rows) == len(VA.components()), (len(rows), len(VA.components())))
check('每行证据列非空', all(r['evidence'].strip() for r in rows))
check('每个态在产物统计段里都有一行', all(VA.STATE_CN[s] in text for s in VA.STATE_ORDER))
check('统计数字对得上（外部 3 件 / 跨构件 13 件）',
      len(by_state.get('external', [])) == 3 and len(by_state.get('cross', [])) == 13,
      {k: len(v) for k, v in by_state.items()})

print('三、登记表：只自证 / 没测的必须签字')
check('只自证/没测的清单 == 登记表（双向；多登记少登记都报）',
      set(no_indep) == KNOWN_NO_INDEPENDENT,
      '只在实测不在表：%s；只在表不在实测：%s'
      % (sorted(set(no_indep) - KNOWN_NO_INDEPENDENT),
         sorted(KNOWN_NO_INDEPENDENT - set(no_indep))))
check('登记表里的名字都是真构件（没有过期条目）',
      KNOWN_NO_INDEPENDENT <= {r['comp'] for r in rows},
      sorted(KNOWN_NO_INDEPENDENT - {r['comp'] for r in rows}))
check('这份"只自证/没测"名单在产物第三节里逐个列出来了',
      all(('`%s`' % c) in text.split('## 三')[1] for c in KNOWN_NO_INDEPENDENT))
check('"只有性质/接口测试"的证据会点明"不构成独立验证方"',
      '不构成独立验证方' in text)

print('四、外部验证方登记不许与文件脱钩')
check('审计器报"登记与文件脱钩"的清单为空', not problems, problems)
check('点名的外部件确实是 external 态', KNOWN_EXTERNAL <= set(by_state.get('external', [])),
      sorted(KNOWN_EXTERNAL - set(by_state.get('external', []))))
_ext_ok = []
for comp in sorted(KNOWN_EXTERNAL):
    token = VA.EXTERNAL[comp][0]
    own = os.path.join(_HERE, 'mechanisms', 'test_%s.py' % comp)
    own2 = os.path.join(_HERE, 'cold', 'test_%s.py' % comp)
    p = own if os.path.exists(own) else own2
    _ext_ok.append(os.path.exists(p) and token in io.open(p, encoding='utf-8').read())
check('外部件在测试文件里真的点名了验证方（命中词独立再查一遍）', all(_ext_ok), _ext_ok)

print('五、本文件独立再算一遍（不借审计器的结论）')


def ast_imports(path):
    try:
        tree = ast.parse(io.open(path, encoding='utf-8').read())
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                names.add(al.name.split('.')[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split('.')[-1])
            for al in node.names:
                names.add(al.name.split('.')[-1])
    return names


tests = VA.test_files()
all_imports = {os.path.basename(t): ast_imports(t) for t in tests}
names_imported = set().union(*all_imports.values()) if all_imports else set()
untested = by_state.get('untested', [])
check('untested 的件确实没有任何测试文件 import 它（AST 重扫）',
      all(c not in names_imported for c in untested), untested)
cross_names = by_state.get('cross', [])
# 找测试文件：**按文件名全仓找**（别硬猜目录——control/ 与 engine 根下也有构件，
# 第一版我按 mechanisms/cold/classical 猜，把 7 件误报成"没 import 别的构件"）
test_by_stem_all = {}
for t_ in tests:
    test_by_stem_all.setdefault(os.path.basename(t_)[5:-3], []).append(t_)
comps = {os.path.basename(x)[:-3] for x in VA.components()}
_reimported = []
for c in cross_names:
    imps = set()
    for t_ in test_by_stem_all.get(c, []):
        imps |= ast_imports(t_)
    if not (imps & (comps - {c})):
        _reimported.append(c)
check('跨构件互验的件确实 import 了另一个构件（抽查全量重算）', not _reimported, _reimported)
check('自带自测列与文件事实相符（抽查 2 件）',
      all(('__main__' in io.open(r['path'] if os.path.isabs(r['path'])
                                 else os.path.join(_REPO, r['path']), encoding='utf-8').read())
          == r['selftest'] for r in rows[:2]))

print('六、词表与判据本身别退化')
check('关键词表没被砍到不成样子（≥20 条）', len(VA.ORACLE_MARKS) >= 20, len(VA.ORACLE_MARKS))
check('校准过的写法还在表里（另写/另算/真值表/已知答案/参考实现）',
      all(m in VA.ORACLE_MARKS for m in ('另写', '另算', '真值表', '已知答案', '参考实现')))
check('太泛的写法**不许**进表（模型/反例/见证 这些常是构件自己的输出）',
      not any(m in VA.ORACLE_MARKS for m in ('模型', '反例', '见证', '对照')))
check('外部登记带命中词（防表格与文件脱钩的机制在）',
      all(isinstance(v, tuple) and len(v) == 2 and v[0] for v in VA.EXTERNAL.values()))

print('=' * 70)
print(f'结果: {PASS}/25 通过')
raise SystemExit(0 if PASS == 25 else 1)
