DeepSeek API uses an API format compatible with OpenAI/Anthropic. By modifying the configuration, you can use the OpenAI/Anthropic SDK to access the DeepSeek API, or use software compatible with the OpenAI/Anthropic API.

PARAM	VALUE
base_url (OpenAI)	https://api.deepseek.com
base_url (Anthropic)	https://api.deepseek.com/anthropic
api_key	apply for an API key
model*	deepseek-v4-flash
deepseek-v4-pro
deepseek-chat (will be deprecated on 2026/07/24)
deepseek-reasoner (will be deprecated on 2026/07/24)
* The two model names deepseek-chat and deepseek-reasoner will be deprecated on 2026/07/24. For compatibility, they correspond to the non-thinking and thinking modes of deepseek-v4-flash respectively.

Calling the Chat API
After creating an API key, you can use the following sample scripts to access DeepSeek models via the OpenAI API format. The examples show non-streaming output. You can set stream to true to use streaming output.

For examples using the Anthropic API format, please refer to the Anthropic API.

curl
python
nodejs
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
  -d '{
        "model": "deepseek-v4-pro",
        "messages": [
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user", "content": "Hello!"}
        ],
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "stream": false
      }'