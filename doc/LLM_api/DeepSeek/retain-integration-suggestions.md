# Retain Integration Suggestions

Based on the current `doc/LLM_api/DeepSeek` directory documentation and the latest official model specifications, the most directly useful capabilities for the current project are as follows.

## 1. Default Model

- The default model should be switched to `deepseek-v4-flash`
- `deepseek-chat` / `deepseek-reasoner` are still compatible, but the official documentation has marked them for future deprecation and should no longer be used as new defaults

## 2. Most Directly Useful Capabilities for the Current Project

- `JSON Output`
  Suitable for our current translation classification, failure diagnosis, and structured return scenarios
- `1M context`
  Beneficial for long documents, long context rules, and glossary scenarios
- `Context Cache / KV Cache`
  High value for cost optimization in batch translation of repeated system prompts, long rules, and long glossaries
- `Tool Calls`
  Not currently required for the main workflow, but has potential value for failure diagnosis, rule selection, and external glossary queries
- `Error Codes`
  401 / 402 / 422 / 429 / 500 / 503 are worth mapping into our existing failure classification and retry strategies

## 3. Most Recommended Priorities for the Backend

- Unify the default model to `deepseek-v4-flash`
- Maintain the `response_format={"type":"json_object"}` structured return capability
- Continue strengthening retry and backoff strategies for DeepSeek 429 / 503
- Evaluate connecting long system prompts, rule texts, and glossaries to context cache
- Stop writing `deepseek-chat` into new examples, defaults, and debugging tools

## 4. Related Documentation

- [Models & Pricing](./models-and-pricing.md)
- [JSON_output](./JSON_output.md)
- [Tool Calls](./tool-calls.md)
- [Error Codes](./error-codes.md)
- [Token Usage Calculation](./token-usage-calculation.md)