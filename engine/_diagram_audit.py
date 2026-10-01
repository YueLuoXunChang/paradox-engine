# -*- coding: utf-8 -*-
"""
_diagram_audit.py — 逻辑流程图体检：每个模块一张图，且图**不许跟代码脱钩**（常设检查）
=====================================================================================
为什么要它：流程图最容易变成**手画的fiction**——代码改了图不改，或者图里写着"某个判词"，
而那个判词在源码里根本不存在。本检查把三件事变成会失败的断言：

    ① **覆盖**：每个模块都必须有 `docs/diagrams/<模块名>.md`；也不许有多余的孤儿图；
    ② **形状**：至少一段 ```mermaid，每段首行是 `flowchart`/`graph`；节点/连线数不低于下限；
       每张图都要出现 `boundary`（全仓约定：返回值带诚实边界）；
    ③ **不许编造**：图里出现的每个**判词**，必须真的是**这个模块**的判词——
       从源码 AST 抠出本模块的判词集合（`verdict` 字段的字面量 ＋ `_reply(...)`/`_out(...)` 的第一个参数），
       图里出现的判词不许跑到别人的集合里去（**串词最容易出现在复制粘贴写图的时候**）。

产物：`docs/diagrams/README.md` 里的**索引段**（`<!-- INDEX:BEGIN -->` … `<!-- INDEX:END -->`
之间由本脚本重写，其余部分手写）——索引给出逐模块的"图是否存在 · 段落数 · 节点数 · 判词覆盖"。

诚实边界：
    判词只能查**字面量**——用 f-string 拼出来的判词抠不到，本检查会**如实说明**（不假装查全）；
    "覆盖到几个判词"是**索引不是结论**：图写得对不对（分支顺序、剪枝条件）还要人看，
    本检查只能挡住"缺图、形状不对、串词、没提 boundary、带本机路径"这几类硬错。

用法：
    python engine/_diagram_audit.py            # 打印体检结果
    python engine/_diagram_audit.py --write    # 重写索引段
    python engine/_diagram_audit.py --check    # 漂移 + 体检（任一条不过就非零退出）
"""

import ast
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
DIR = os.path.join(_REPO, 'docs', 'diagrams')
INDEX = os.path.join(DIR, 'README.md')
INDEX_BEGIN = '<!-- INDEX:BEGIN（下面这段由 --write 重新生成，别手改） -->'
INDEX_END = '<!-- INDEX:END -->'

MIN_BLOCKS = 1          # 每份至少几段 mermaid
MIN_NODES = 8           # 每份至少几个节点（"详细"的底线）
STANDARD = ('input_pending', 'parse_error', 'size_limit', 'internal_error')

sys.path.insert(0, _REPO)
from engine import _verifier_audit as VA                                     # noqa: E402


def components():
    """复用验证方登记那份的构件清单（扫盘口径同源，别各算各的）。"""
    return VA.components()


def _read(p):
    return io.open(p, encoding='utf-8', errors='replace').read()


def _literals(expr):
    """递归抠一个表达式里的字符串字面量（穿进 IfExp / BoolOp / 拼接 / f-string 的常量段）。

    为什么要递归：本仓的判词常常是表达式形式，例如
    `_reply('equivalent' if same else 'not_equivalent', ...)`——
    只在最外层找字面量会漏掉它，于是"抠不到 ⇒ 当成动态 ⇒ 图里写了反而被误判成串词"。
    """
    out, dynamic = set(), False
    for node in ast.walk(expr):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.add(node.value)
        elif isinstance(node, ast.JoinedStr):
            dynamic = True                      # f-string：只能抠到常量段，报"动态"
    out.discard('verdict')                      # 那是**键名**，不是判词值（walk 会走到嵌套字典的键）
    return out, dynamic


def _verdict_shape(s):
    """判词形状：小写字母开头、只含小写字母/数字/下划线、不超 24 字符。

    用来把"看起来像判词的词"从普通说明文本里挑出来（`utf-8`、`a b` 这类一律不算）。
    """
    if not isinstance(s, str) or not (0 < len(s) <= 24):
        return False
    if not s[0].isalpha() or not s[0].islower():
        return False
    return all(ch.islower() or ch.isdigit() or ch == '_' for ch in s)


# 出口函数名：这些函数第一个参数就是判词（各件命名不完全一样，所以按前缀收）
_EMITTERS = ('_reply', '_out', '_bad', '_result', '_ret', '_emit', '_verdict',
             '_make', '_fail', '_ok')

_LIT_CACHE = {}


def module_literals(path):
    """本模块源码里出现过的所有字符串字面量。

    判"图里的词是不是编的"用：本模块自己都写着 `converge`（操作名）、`demo`（模式名），
    图上写它当然不算编——只有**本模块哪儿都没有**的词才该被列成待核对。
    """
    if path in _LIT_CACHE:
        return _LIT_CACHE[path]
    try:
        tree = ast.parse(_read(path))
    except SyntaxError:
        _LIT_CACHE[path] = set()
        return _LIT_CACHE[path]
    out = {n.value for n in ast.walk(tree)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    _LIT_CACHE[path] = out
    return out


def verdicts_of(module_path):
    """从源码 AST 抠本模块的判词：`{'verdict': 字面量}` ＋ `_reply/_out/_bad(第一个参数)`。

    表达式形式（三元、布尔、拼接）会**递归下钻**；f-string 拼出来的抠不全，
    返回的第二个值标记"有动态拼的痕迹"（本检查如实说明，不假装查全）。
    """
    try:
        tree = ast.parse(_read(module_path))
    except SyntaxError:
        return set(), False
    out, dynamic = set(), False
    for node in ast.walk(tree):
        # 规则一：字典里 `verdict` 键的值（带形状过滤：说明文本里以中文开头的词一律不收）
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == 'verdict':
                    lit, dyn = _literals(v)
                    out |= {x for x in lit if _verdict_shape(x)}
                    dynamic = dynamic or dyn
        # 规则二：老名单出口（_reply/_out/_bad）的第一个参数
        if isinstance(node, ast.Call) and getattr(node.func, 'id', '') in ('_reply', '_out', '_bad'):
            if node.args:
                lit, dyn = _literals(node.args[0])
                out |= {x for x in lit if _verdict_shape(x)}
                dynamic = dynamic or dyn
        # 规则三：私有帮助函数的第一个参数，**且首参本身就是一个判词表达式**
        #（常量 / 三元 / 布尔 / 拼接）。不看嵌套结构——`_ctl_run({'states': …})`
        # 的首参是字典，里面的键名是参数名，不是判词；
        # 门槛 len >= 4 是为了放掉 `_fresh_skolem('c')` 这类单字母前缀。
        if isinstance(node, ast.Call) and node.args \
                and isinstance(node.args[0], (ast.Constant, ast.IfExp,
                                              ast.BoolOp, ast.JoinedStr)):
            fn = getattr(node.func, 'id', '') or ''
            head_lit, _d = _literals(node.args[0])
            if fn in _EMITTERS or (fn.startswith('_')
                                   and any(_verdict_shape(x) and len(x) >= 4
                                           for x in head_lit)):
                out |= {x for x in head_lit
                        if _verdict_shape(x) and (len(x) >= 4
                                                  or fn in _EMITTERS)}
                dynamic = dynamic or _d
        # 规则四：`return 判词, 详情容器`——必须是**两项以上**、且第二项是详情容器
        #（字典 / 列表）。这样 `return ('top',)` / `return ('dia', None, unary())`
        # 这类**数据结构构造**不会被当成判词。
        if isinstance(node, ast.Return) and isinstance(node.value, (ast.Tuple, ast.List)):
            elts = node.value.elts
            if len(elts) >= 2 and isinstance(elts[1], (ast.Dict, ast.List)):
                lit, dyn = _literals(elts[0])
                out |= {x for x in lit if _verdict_shape(x)}
                dynamic = dynamic or dyn
    # 剔掉"类型名"这类根本不是判词的字面量（PORTS 里写着 'verdict': 'str'，别把它当判词）
    out -= {'str', 'int', 'float', 'bool', 'dict', 'list', 'any', 'callable', 'object'}
    return out, dynamic


def mermaid_blocks(text):
    """抠出所有 ```mermaid 代码块（返回块的正文列表）。"""
    return re.findall(r'```mermaid\n(.*?)```', text, re.S)


def block_stats(block):
    """一段图的规模：节点数与连线数（够用的粗算，够挡住"三行就交差"）。"""
    lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith('%%')]
    body = [l for l in lines if l.split()[0] not in ('flowchart', 'graph', 'subgraph', 'end',
                                                     'direction', 'style', 'classDef', 'linkStyle')]
    nodes = set()
    for l in body:
        for m in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*[\[\(\{]', l):
            nodes.add(m.group(1))
    edges = sum(1 for l in body if '-->' in l or '---' in l)
    return len(nodes), edges


def known_identifiers():
    """图上会自然出现的**非判词**词：所有模块 PORTS 里的字段名与取值 ＋ 模块名 ＋ 一小张停用词。

    （把"待核对词"缩小到真正可疑的那几个——第一版判据把 `budget`/`formula` 这类字段名
    也当成"编造判词"，一堆误报；判据自己也得按语料校准。）
    """
    ids = {os.path.basename(c)[:-3] for c in components()}
    for c in components():
        try:
            tree = ast.parse(_read(c))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                    getattr(t, 'id', '') == 'PORTS' for t in node.targets):
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        ids.add(sub.value)
                        for piece in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', sub.value):
                            ids.add(piece)
    ids |= {'boundary', 'verdict', 'mermaid', 'flowchart', 'graph', 'subgraph', 'end', 'style',
            'direction', 'run', 'inputs', 'detail', 'true', 'false', 'none', 'null'}
    return ids


def audit():
    """返回 (rows, problems)。rows 每行一件；problems 装**硬错**（缺图/形状/boundary/本机路径）。"""
    comps = components()
    rows, problems = [], []
    files = {}
    all_verdicts = {}
    for c in comps:
        name = os.path.basename(c)[:-3]
        mine, dyn = verdicts_of(c)
        all_verdicts[name] = mine
        files[name] = (c, mine, dyn)
    # 全仓判词词表 ＋ 非判词标识符表（两者一起才判得出"编造"）
    vocab = set(STANDARD)
    for v in all_verdicts.values():
        vocab |= v
    benign = known_identifiers()

    diagram_files = [f for f in os.listdir(DIR) if f.endswith('.md') and f != 'README.md'] \
        if os.path.isdir(DIR) else []
    for name, (comp, mine, dyn) in sorted(files.items()):
        layer = os.path.basename(os.path.dirname(comp)) or 'engine'
        path = os.path.join(DIR, '%s.md' % name)
        row = {'comp': name, 'layer': layer, 'exists': os.path.exists(path),
               'blocks': 0, 'nodes': 0, 'edges': 0, 'boundary': False,
               'covered': [], 'missing': [], 'foreign': [], 'suspects': [],
               'bad_first': [], 'dynamic': dyn}
        if not row['exists']:
            problems.append('%s：缺图（应写成 docs/diagrams/%s.md）' % (name, name))
            rows.append(row)
            continue
        text = _read(path)
        blocks = mermaid_blocks(text)
        row['blocks'] = len(blocks)
        if not blocks:
            problems.append('%s：没有 ```mermaid 代码块' % name)
        for b in blocks:
            head = next((l.strip() for l in b.splitlines() if l.strip()), '')
            if head != 'flowchart TD':
                row['bad_first'].append(head[:40])
                problems.append('%s：图的布局必须是 `flowchart TD`（统一从上到下），现在是 %r'
                                % (name, head[:40]))
            # 下面四条来自语料侧图集的"避坑清单"，逐条都是真炸过的
            if re.search(r'--\s+[^\-\n]+\s+-->', b):
                problems.append('%s：用了 `-- 标签 -->` 简写（中文标签会炸）→ 改成 `-->|标签|`' % name)
            # 只在**节点标签内容**里查符号（v1 用整段正则，会跨行把 `-->|是|` 里的 > 当成标签内容，
            # 一片假阳性；改成逐行取方括号/花括号里的东西再看）
            bad_sym = []
            for line in b.splitlines():
                for mm in re.finditer(r'[\[\{\(]([^\[\]\{\}\(\)]*)[\]\}\)]', line):
                    inner = re.sub(r'</?br\s*/?>', '', mm.group(1))
                    if re.search(r'[<>≤≥&]', inner):
                        bad_sym.append(inner.strip()[:40])
            if bad_sym:
                problems.append('%s：节点标签里有 < 或 > 或 比较符号（会被当 HTML 标签）→ 写成中文：%s'
                                % (name, bad_sym[:3]))
            if re.search(r'subgraph\s+(?!")', b):
                problems.append('%s：subgraph 名没加引号（含中文会炸）' % name)
            if 'classDef core' not in b:
                problems.append('%s：没按配色约定上色（缺 classDef core）' % name)
        n, e = 0, 0
        for b in blocks:
            bn, be = block_stats(b)
            n += bn
            e += be
        row['nodes'], row['edges'] = n, e
        if row['blocks'] < MIN_BLOCKS:
            problems.append('%s：mermaid 段数不足（%d）' % (name, row['blocks']))
        if n < MIN_NODES:
            problems.append('%s：节点太少（%d < %d）——"详细"不能只有一条直线' % (name, n, MIN_NODES))
        if 'boundary' not in text:
            problems.append('%s：图里没提 boundary（全仓约定：返回值带诚实边界）' % name)
        seen = {w for w in vocab if re.search(r'\b%s\b' % re.escape(w), text)}
        row['covered'] = sorted(seen & mine)
        row['missing'] = sorted(mine - seen)
        # 提到别的构件的判词不算错（流水线里本来就会带上家/下家的结论词），只记下来给人看；
        # 真正可疑的是"既不是本模块判词、也不是字段名/模块名的 snake_case 词"——列成**待核对词**。
        row['foreign'] = sorted(seen - mine - set(STANDARD))
        mod_lits = module_literals(comp)
        suspects = sorted({w for w in re.findall(r'`([a-z][a-z0-9_]{2,})`', text)
                           if w not in vocab and w not in benign
                           and w not in mod_lits})
        row['suspects'] = suspects
        if not row['covered']:
            problems.append('%s：图里一个本模块判词都没写出来' % name)
        if re.search(r'[A-Za-z]:' + re.escape(chr(92)), text) or '落落' in text:
            problems.append('%s：图里出现本机路径或私有引用（发布面红线）' % name)
        rows.append(row)

    orphans = sorted(set(f[:-3] for f in diagram_files) - set(files))
    if orphans:
        problems.append('有多余的孤儿图（没有对应模块）：%s' % orphans)
    return rows, problems


def render_index(rows):
    """只重写索引段（其余手写内容保留）。"""
    n_ok = sum(1 for r in rows if r['exists'])
    covered = sum(len(r['covered']) for r in rows)
    total_v = sum(len(r['covered']) + len(r['missing']) for r in rows)
    L = []
    L.append('共 **%d** 个模块，已有图 **%d** 张；图里点名到的判词 **%d/%d**（字面量口径：'
             '字典 `verdict` 值 ＋ 出口函数首参的常量 / 三元 / 拼接 ＋ `return 判词, 详情字典`。'
             '**数据结构构造标签**（如 `(\'top\',)`）与 f-string 拼出来的都不计，见文末边界）。'
             % (len(rows), n_ok, covered, total_v))
    L.append('')
    L.append('| 模块 | 层 | 图 | 段落 | 节点 | 判词覆盖 | 待核对词 |')
    L.append('|:--|:--|:--|--:|--:|:--|:--|')
    for r in rows:
        link = '[图](%s.md)' % r['comp'] if r['exists'] else '**缺**'
        cov = '%d/%d' % (len(r['covered']), len(r['covered']) + len(r['missing']))
        if r['missing']:
            cov += '（缺 %s）' % '、'.join('`%s`' % m for m in r['missing'][:3])
        sus = '、'.join('`%s`' % s for s in r['suspects'][:3]) or '—'
        L.append('| `%s` | %s | %s | %d | %d | %s | %s |'
                 % (r['comp'], r['layer'], link, r['blocks'], r['nodes'], cov, sus))
    L.append('')
    L.append('> **待核对词**＝图里出现的、既不是本模块判词、也不是字段名/模块名的词——'
             '可能是**编造**，也可能只是画图时用的标识符。它进索引不进硬门禁（当索引读，当结论读就错了）；'
             '硬门禁只管：**每件都有图 · 形状合法 · 节点够多 · 提到 boundary · 无本机路径 · '
             '至少写出一个本模块判词**。')
    return '\n'.join(L)


def write_index(rows, dry=False):
    text = _read(INDEX) if os.path.exists(INDEX) else ''
    block = render_index(rows)
    if INDEX_BEGIN in text and INDEX_END in text:
        head, rest = text.split(INDEX_BEGIN, 1)
        _, tail = rest.split(INDEX_END, 1)
        text = head + INDEX_BEGIN + '\n' + block + '\n' + INDEX_END + tail
    else:
        text = text + '\n' + INDEX_BEGIN + '\n' + block + '\n' + INDEX_END + '\n'
    if not dry:
        io.open(INDEX, 'w', encoding='utf-8', newline='\n').write(text)
    return text


def main(argv):
    rows, problems = audit()
    if '--write' in argv:
        write_index(rows)
        print('已写出索引段：docs/diagrams/README.md（%d 个模块，%d 张图）'
              % (len(rows), sum(1 for r in rows if r['exists'])))
        for p in problems:
            print('  ⚠️ ' + p)
        return 0
    if '--check' in argv:
        want = write_index(rows, dry=True)
        cur = _read(INDEX) if os.path.exists(INDEX) else ''
        if cur != want:
            print('❌ 索引段不是现算的（有人手改，或图变了）——跑 --write')
            return 1
        if problems:
            print('❌ 流程图体检没过（%d 条）：' % len(problems))
            for p in problems:
                print('   ' + p)
            return 1
        print('流程图体检一致（%d 张图 / %d 个模块）' % (sum(1 for r in rows if r['exists']), len(rows)))
        return 0
    print('流程图体检（%d 个模块）' % len(rows))
    miss = [r for r in rows if not r['exists']]
    print('  有图 %d / 缺图 %d' % (len(rows) - len(miss), len(miss)))
    if miss:
        print('  缺图：%s' % '、'.join(r['comp'] for r in miss))
    dyn = [r['comp'] for r in rows if r['dynamic']]
    if dyn:
        print('  ⚠️ 这些模块的判词里有 f-string 动态拼的（本检查抠不到）：%s' % '、'.join(dyn))
    if problems:
        print('  问题 %d 条：' % len(problems))
        for p in problems:
            print('    - ' + p)
    return 0 if not problems else 1


if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印中文/emoji 会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main(sys.argv[1:]))
