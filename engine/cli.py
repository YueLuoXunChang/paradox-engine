# -*- coding: utf-8 -*-
"""
cli.py — paradox-engine 命令行入口（AI 挂载层 · 阶段 6 扩展）
================================================================
用法：
    python -m engine.cli --text "产品既要快又要稳"          # 中文诊断报告
    python -m engine.cli --text "..." --json                 # 结构化 JSON
    python -m engine.cli --file 输入.txt                     # 从文件读文本
    python -m engine.cli --demo                              # 十五步演示
    paradox-engine --text "..."                              # 安装后 console 命令

做什么：
    把总控五步流水线接到命令行——传一段问题文本，输出中文诊断报告
    （或 JSON），给人看 / 给脚本用 / 给 AI 管道用。

诚实边界：
    - 需要结构化线索才能真跑构件的场景，缺线索会诚实报"缺结构化输入"
      （与 controller 一致，不伪造）；
    - 只诊断不决策：报告结尾带边界声明。
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load_controller():
    try:
        from engine.control.controller import run as controller
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'control'))
        from controller import run as controller
    return controller


def build_parser():
    p = argparse.ArgumentParser(
        prog='paradox-engine',
        description='悖论/矛盾检测引擎：给一段文本 → 判类→复杂度→切路→'
                    '执行→判输出（只诊断不决策）',
        epilog='概念原创：月落寻常 · AI 协作实现 · MPL-2.0')
    p.add_argument('--text', type=str, default=None, help='问题文本')
    p.add_argument('--file', type=str, default=None,
                   help='从文件读取问题文本')
    p.add_argument('--json', action='store_true',
                   help='输出结构化 JSON（默认给人看的中文报告）')
    p.add_argument('--demo', action='store_true',
                   help='跑十五步演示 demo.py')
    p.add_argument('--tools', action='store_true',
                   help='列出全部可用工具（function-calling schema）')
    p.add_argument('--structured', type=str, default=None,
                   help='结构化线索 JSON（如 {"A":"要快","B":"要稳"}，'
                        '给 T2 用）')
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.demo:
        demo_path = os.path.join(_REPO, 'demo.py')
        os.system(f'python "{demo_path}"')
        return 0

    if args.tools:
        try:
            from engine.ai.tools import tools
        except ImportError:
            sys.path.insert(0, os.path.join(_REPO, 'engine', 'ai'))
            from tools import tools
        tl = tools()
        print(f'可用工具 {len(tl)} 件：')
        for t in tl:
            fn = t['function']
            print(f'  · {fn["name"]}：{fn["description"]}')
        return 0

    # 取文本
    text = args.text
    if args.file:
        try:
            with open(args.file, encoding='utf-8') as fh:
                text = fh.read().strip()
        except OSError as e:
            print(f'读文件失败：{e}')
            return 2
    if not text:
        print('需给文本：--text "..." 或 --file 输入.txt'
              '（或 --demo / --tools）')
        return 2

    # 结构化线索
    structured = None
    if args.structured:
        try:
            structured = json.loads(args.structured)
        except json.JSONDecodeError as e:
            print(f'--structured JSON 解析失败：{e}')
            return 2

    controller = _load_controller()
    r = controller({'text': text, 'structured': structured or {}})

    if args.json:
        # 结构化输出：classification + execution + output_check + report
        print(json.dumps({
            'main_type': r['classification']['main_type'],
            'main_name': r['classification']['main_name'],
            'level': r['classification']['level'],
            'route_id': r['classification']['route']['route_id'],
            'confidence': r['classification']['confidence'],
            'verdict': r['verdict'],
            'output_check': r['output_check'],
            'execution': [
                {'component': e['component'], 'status': e['status'],
                 'note': e.get('note')}
                for e in r['execution']
            ],
            'report': r['report'],
        }, ensure_ascii=False, indent=2))
    else:
        print(r['report'])

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
