<!-- 感谢提交！请把下面几项填上，方便我们快速判断与合并。 -->

## 改了什么

<!-- 一句话说清这次改动；若是加构件/改路由，说明它在哪一层 -->

## 为什么

<!-- 真实痛点或缺陷现象；没有痛点支撑的"为加而加"建议先开 issue 讨论 -->

## 怎么验证的

- [ ] `python run_tests.py` 全绿（把合计行贴上来）
- [ ] `python demo.py` 通过
- [ ] 若改了对外契约（工具名/参数名）：`python engine/ai/freeze_tool_schema.py` 已重新生成
- [ ] 若新增场景/构件：已含自测 + 正式测试，并已更新文档与 CHANGELOG

```
（粘贴 run_tests.py 的合计行）
```

## 自检（本仓库纪律）

- [ ] 零第三方依赖（纯标准库）
- [ ] 诚实边界：算不动就诚实拦截（`undecided` / `*_pending` / `size_limit`），没有编造数值
- [ ] 没有写进本机路径、身份信息、私有项目名、内部文档编号、密钥（见 CONTRIBUTING「发布面红线」）
- [ ] 门面文档数字与实测一致（`python engine/test_docs_consistency.py` 通过）