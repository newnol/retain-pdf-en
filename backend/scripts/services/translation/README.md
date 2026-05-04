# Translation 说明

这一层只做一件事：把 OCR payload 变成可落盘、可回填、可渲染的翻译结果。

这里不负责 PDF 读取和写回，也不负责 MinerU 解包。

## 阶段边界

Translation 阶段的正式输入和输出固定为：

- 输入：
  `document.v1.json`、翻译策略参数、翻译输出目录
- 输出：
  逐页 translation payload、翻译摘要、翻译诊断

明确不负责的事情：

- 不直接消费 provider raw JSON、zip 或 unpacked 目录
- 不负责源 PDF 的页面写回、排版覆盖和最终 PDF 交付
- 不负责 OCR provider 上传、轮询、下载和 normalize 产物生成

当前稳定交接点：

- 上游 OCR 阶段应先把 provider 结果收敛成 `document.v1.json`
- 下游渲染阶段应只消费这里落盘的翻译产物，不应再回头理解 OCR provider 私有字段

当前默认翻译产物协议：

- `translation-manifest.json`
记录页索引到翻译 payload 文件的稳定映射，供渲染阶段优先读取
  还会附带轻量元数据，例如 glossary 摘要、诊断摘要，以及 `invocation` 字段
  当前正式路径统一标记为 `stage_spec`
- 逐页 translation payload
  当前仍按每页一个 JSON 落盘，manifest 负责声明这些文件该如何被渲染阶段发现
- 阶段 spec
  `translate-only` 入口已支持 `job_root/specs/translate.spec.json`（`translate.stage.v1`）
- 调试产物
  - `artifacts/translation_diagnostics.json`
  - `artifacts/translation_debug_index.json`

## Translation Payload 口径

逐页 translation payload 现在分成两层：

1. 顶层 contract 字段
2. `metadata` 调试/桥接字段

顶层 contract 字段包括：

- `block_kind`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy_translate`
- `asset_id`
- `reading_order`
- `raw_block_type`
- `normalized_sub_type`

当前约定：

- translation 的分类、style hint、policy、payload 回填和 diagnostics 主链优先只读这些顶层 contract 字段
- `metadata` 可以继续保留，但职责只限于 debug、provider trace 和桥接 `continuation_hint/provider warning`
- 新逻辑不要再把 `metadata.layout_role`、`metadata.semantic_role`、`metadata.structure_role` 当正式语义入口
- 如果后续 block 语义变更，优先只改 `document.v1 -> TextItem -> payload` 这条 contract 投影，不要让下游模块各自再翻 `metadata`

兼容约定：

- 新任务目录应生成 `translation-manifest.json`
- 翻译产物协议固定为 `translation-manifest.json` + 每页 payload，渲染阶段不再兼容旧的逐页 JSON 直扫模式
- 默认加载口径已经是 strict contract；缺少上述顶层字段的 payload 会直接报错
- Rust 主工作流调用的 `translate-only` worker 现在要求 `--spec`
- `scripts/entrypoints/translate_book.py` 现在也是 spec-only 包装入口
- API 凭证不再要求写入 stage spec；spec 中使用 `credential_ref`，由运行时环境注入真实 key

## 调试闭环

现在有一套最小可复现链路，专门用来定位“某个 item 为什么没翻 / 降级 / 保留原文”：

1. 先看调试产物
   - `translation_diagnostics.json` 看全局统计
   - `translation_debug_index.json` 看 item 级索引
2. 再看单 item
   - `backend/scripts/devtools/replay_translation_item.py`
3. 需要批量回归时再接 promptfoo
   - `backend/scripts/devtools/promptfoo/`
   - 先用 `scan_drift.py` 找 saved vs replay 漂移项，再用 `capture_case.py` 固化成 case artifact

Rust API 对应暴露了：

- `GET /api/v1/jobs/{job_id}/translation/diagnostics`
- `GET /api/v1/jobs/{job_id}/translation/items`
- `GET /api/v1/jobs/{job_id}/translation/items/{item_id}`
- `POST /api/v1/jobs/{job_id}/translation/items/{item_id}/replay`

## 子目录

- `ocr/`
  OCR JSON 读取和数据抽取。主线优先读取 `normalized_document_v1`，raw provider JSON 只在入口处先经过 adapter、defaults 和 schema 校验，再进入这里。
- `orchestration/`
  布局区、continuation、translation unit 元数据。
- `classification/`
  `precise` 模式下的可疑块分类。
- `continuation/`
  段落连续性判断、candidate pair 导出和审阅。
- `diagnostics/`
  结构化翻译诊断模型，承接 placeholder 异常、窗口降级和 keep-origin 降级事件。
- `policy/`
  翻译策略配置和显式契约消费。默认主链不再靠本地规则二次猜 OCR 语义。
- `llm/`
  模型请求、缓存、重试、placeholder 守护、分段路由和控制上下文。
  新人先读 `llm/README.md`，里面单独说明了 provider 层、shared 层、编排层、兼容 shim 和关键调用链。
- `payload/`
  payload 协议、公式占位、翻译 JSON 读写。
- `terms/`
  术语表归一化、提示词注入和术语命中统计。
- `workflow/`
  单页翻译流程入口。

## 主要流程

1. `ocr/` 读取统一中间层 `document.v1.json` 并抽取页面块
2. 如果入口给的是 provider 原始 JSON，则先由 `document_schema/adapters.py` 转成 `document.v1`
3. `workflow/translation_workflow.py` 生成每页翻译模板并加载 payload
4. `orchestration` 补齐布局区和编排元数据
5. `continuation` 先消费上游 `continuation_hint`，再用规则兜底，把连续段落合并成统一 translation unit
6. `policy` 根据模式决定跳过哪些块
7. `llm` 按 batch 调模型翻译、缓存和重试，并统一处理 placeholder/segment/fallback 控制
8. `payload` 把翻译结果回填到 page payload，并保存最终 JSON

补充约定：

- translation 主线不应该直接理解某个 OCR provider 的 raw JSON 结构
- translation 主线当前的默认落盘结果是“逐页 translation payload + translation-manifest.json”；这层负责产物内容和映射协议，不负责最终 PDF 文件名和渲染模式
- `document.v1` 里凡是已经带 `skip_translation` tag 的块，必须在 `ocr/json_extractor.py` 抽取阶段就被挡掉，不能再漏进翻译候选
- `abstract` 这类正文扩展语义可以继续进入翻译；`reference_entry`、`formula_number` 这类 provider 已明确标记跳过的块不应进入 payload
- 抽取阶段优先读取显式 `content.kind / layout_role / semantic_role / structure_role / policy.translate`；默认主链不再从 `derived.role / sub_type / raw_type / tags` 反推正文
- 抽取阶段会把 block 上的 `continuation_hint` 展开成 payload 里的 `ocr_continuation_*` 字段
- continuation 当前采用 provider-first 策略：优先消费同页 `intra_page` provider hint；跨页 `cross_page` hint 只在“相邻页 + 顺序明确 + layout_zone 命中页尾/页首阅读边界 + 文本长度足够”时受控消费，其余情况继续保留但不直接驱动拼接
- 如果只想排查 OCR 规范化是否有问题，优先看 `document.v1.report.json`
- Python 侧读取 report 摘要时，优先走 `document_schema/reporting.py`

默认正文白名单现在固定为：

- `content.kind == "text"`
- 且 `policy.translate == true`

这意味着：

- 正文是否进入翻译链，应该在 normalize / adapter 阶段决定
- translation 默认主链不再重新猜 `footer/header/page_number/table/image/code/reference_content`
- `ref_text`、`mixed_literal`、`metadata_fragment` 这类旧本地 skip / rewrite 规则已经退出默认主链

## 术语表 v1

当前术语表链路分成两层输入：

- 命名术语表资源：由 Rust API 先落库，再通过 `glossary_id` 引用
- 任务内 inline 术语：直接随任务一起传入 `glossary_entries`

进入 Python 之前，Rust 侧会先完成：

- 术语条目归一化
- 去重
- 命名术语表与 inline 术语的合并
- 相同 `source` 的覆盖统计

Translation 阶段当前只做两件事：

- 把合并后的术语表注入到 LLM 控制上下文，作为翻译偏好提示
- 在翻译结束后统计术语命中情况，并写入 `translation-manifest.json`、诊断文件和 pipeline summary

明确不做的事情：

- 不做翻译后强制替换
- 不保证每个术语一定命中
- 不直接解析 Excel 文件

## 模式说明

- `fast`
  不启用分类器。
- `sci`
  面向论文和技术文档，还会做领域推断。
- `precise`
  启用 LLM 分类器，只对可疑 OCR 块做额外判断。

## Policy Config 兼容说明

`policy/config.py` 里的 `build_translation_policy_config()` 目前还保留了几个旧字段，但它们已经不属于默认主链语义：

- `enable_narrow_body_noise_skip`
- `enable_metadata_fragment_skip`
- `metadata_fragment_max_page_idx`
- `enable_reference_zone_skip`
- `enable_reference_tail_skip`

当前约定是：

- 默认主链不会消费这些字段去重建旧 skip 逻辑
- 它们当前只作为 deprecated compatibility surface 保留，主要避免老测试/老调用方立刻报错
- 新代码不要再基于这些字段设计行为

注意：

- 这属于内部 Python translation policy contract，不是外部 HTTP API 契约
- 真实的“是否翻译”主决策仍应来自 `document.v1` 的显式 block policy

## 协作规矩

如果翻译模块单独分人维护，这里只负责“把 `document.v1.json` 变成稳定翻译产物”。

- 允许在这里改策略、并发、术语表、LLM 调度、payload 落盘和翻译诊断
- 不要在这里直接处理 provider raw OCR 结构，也不要把源 PDF 渲染逻辑塞回来
- 当前正式输出协议是“逐页 translation payload + `translation-manifest.json`”；渲染层应只消费这套协议
- 如果修改 payload 结构、manifest 字段语义或默认文件发现方式，必须同步更新 `runtime/pipeline`、`rendering`、README 和测试
- 术语表当前是翻译提示约束，不是渲染层规则，也不是 OCR 层规则；不要把术语逻辑扩散到其他模块
