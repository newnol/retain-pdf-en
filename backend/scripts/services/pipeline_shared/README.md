# Pipeline Shared 说明

`services/pipeline_shared/` 放的是跨阶段共享、但不属于任何单一 provider 的通用协议层。

当前主要承载三类东西：

- `contracts.py`
  provider / translate / render worker 共用的 stdout label 与 summary 文件名。
- `io.py`
  中性的 JSON 落盘 helper。
- `source_json.py`
  主线如何在 raw provider layout 与 normalized document 之间选择正式输入的中性规则。
- `summary.py`
  主线 worker 共用的 pipeline summary 生成与打印逻辑。

设计边界：

- 这里只放阶段级共享协议，不放 MinerU、Paddle 之类 provider 私有语义。
- 这里只放主线都需要的通用能力，不放翻译策略、渲染实现或 OCR 适配细节。
- `services/mineru/` 可以继续保留兼容壳，但新的主线依赖应优先指向这里。

这层的目标不是增加一层抽象，而是把原来挂在 `services/mineru/*` 名字下、实际已经被全流程共用的能力收口到中性模块，方便后续把后端继续演进成“模块化单体”。
