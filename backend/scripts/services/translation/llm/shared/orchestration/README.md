# Translation LLM Orchestration

这一层只负责一件事：
把“单个 block / 单批 items 的翻译请求”编排成稳定、可回退、可诊断的 provider 调用流程。

它不负责：

- provider 专属 HTTP 细节
- OCR payload 抽取
- page payload 回填落盘
- PDF 渲染

## 新人先读

- 想看总入口：
  `retrying_translator.py`
- 想看 plain-text 单条降级主链：
  `fallbacks.py`
- 想看公式 segment 路由：
  `segment_routing.py`
- 想看 direct-typst 特殊路径：
  `direct_typst.py`
- 想看 batch/cache/tail retry：
  `batched_plain.py`

## 当前边界

- `retrying_translator.py`
  shared orchestration 聚合入口。
  负责把 workflow 侧请求接到 plain-text / segment / provider runtime 主链。

- `fallbacks.py`
  plain-text 单条编排 facade。
  负责：
  - 选择 direct-typst / segmented / plain-text 主路径
  - tagged placeholder first 决策
  - 单条 plain-text attempt loop
  - sentence-level fallback 接入
  - 保留兼容 shim，避免外部调用点和测试直接断掉

- `batched_plain.py`
  batched plain-text 编排。
  负责：
  - cache hit / cache drop
  - low-risk batch 决策
  - batch partial accept + retry split
  - transport tail retry pass

- `direct_typst.py`
  direct-typst 主 retry loop。
  负责：
  - direct-typst plain/raw 两条路径的 attempt loop
  - validation failure 后的最终收口
  - sentence fallback / transport degrade 接入

- `direct_typst_long_text.py`
  direct-typst 长文本预切分。
  只负责拆块和 chunk 级拼回，不处理 provider transport。

- `direct_typst_salvage.py`
  direct-typst protocol/json shell salvage。
  只负责从异常文本中提取可接受译文并做 partial accept。

- `heavy_formula.py`
  heavy formula block 预拆分。
  只负责：
  - 是否需要 heavy split
  - 如何按 placeholder 密度拆块
  - chunk 级重试后再拼回

- `plain_text_validation.py`
  plain-text validation 失败后的收口逻辑。
  只负责：
  - protocol shell salvage
  - English residue partial salvage
  - repeated validation failure 最终 degrade 决策

- `sentence_level.py`
  sentence-level fallback。
  只负责句级拆分、逐句请求、部分成功拼回。

- `transport.py`
  transport tail retry / DLQ 公共逻辑。

- `keep_origin.py`
  keep-origin payload 构造器。
  统一所有 degrade payload 的格式。

- `metadata.py`
  translation_diagnostics / formula diagnostics / runtime term restore。

- `common.py`
  文本长度、continuation、CJK、placeholder 数量等纯判定工具。

## 调用链

最常见的调用链是：

`retrying_translator.py`
-> `fallbacks.py`
-> `direct_typst.py` / `segment_routing.py` / plain-text provider runtime
-> `keep_origin.py` / `plain_text_validation.py` / `sentence_level.py`

batch 路径是：

`retrying_translator.py`
-> `batched_plain.py`
-> `fallbacks.py`

## 后续约定

- 新的降级策略，优先放进对应的责任模块，不要再回堆到 `fallbacks.py`
- `fallbacks.py` 保持“薄 facade + 主 loop”定位，不再塞纯工具函数
- provider 专属逻辑不要进入这里，统一留在 `shared/provider_runtime.py` 之后的 provider 实现里
- 如果某个模块再次超过 400-500 行，优先按责任切，不按代码块机械切
