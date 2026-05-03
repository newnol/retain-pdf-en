In many scenarios, users need the model to output strictly in JSON format to structure the output for easier parsing by downstream logic.

DeepSeek provides the JSON Output feature to ensure the model outputs valid JSON strings.

## Notes
Set the response_format parameter to {'type': 'json_object'}.
The system or user prompt passed by the user must contain the word "json" and provide an example of the desired JSON format to guide the model to output valid JSON.
The max_tokens parameter should be set appropriately to prevent the JSON string from being truncated midway.
When using the JSON Output feature, the API may occasionally return empty content. We are actively optimizing this issue, and you can try modifying the prompt to mitigate this problem.

## Sample Code
Here is the complete Python code demonstrating the JSON Output feature:

import json
from openai import OpenAI

client = OpenAI(
    api_key="<your api key>",
    base_url="https://api.deepseek.com",
)

system_prompt = """
The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. 

EXAMPLE INPUT: 
Which is the highest mountain in the world? Mount Everest.

EXAMPLE JSON OUTPUT:
{
    "question": "Which is the highest mountain in the world?",
    "answer": "Mount Everest"
}
"""

user_prompt = "Which is the longest river in the world? The Nile River."

messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}]

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=messages,
    response_format={
        'type': 'json_object'
    }
)

print(json.loads(response.choices[0].message.content))


The model will output:

{
    "question": "Which is the longest river in the world?",
    "answer": "The Nile River"
}