Tool Calls enable the model to call external tools to enhance its capabilities.

## Non-thinking Mode
### Sample Code
This example demonstrates the complete Python code for using Tool Calls, using the scenario of getting weather information for the user's current location.

For the specific API format of Tool Calls, please refer to the chat completion documentation.

from openai import OpenAI

def send_messages(messages):
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=messages,
        tools=tools
    )
    return response.choices[0].message

client = OpenAI(
    api_key="<your api key>",
    base_url="https://api.deepseek.com",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of a location, the user should supply a location first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    }
                },
                "required": ["location"]
            },
        }
    },
]

messages = [{"role": "user", "content": "How's the weather in Hangzhou, Zhejiang?"}]
message = send_messages(messages)
print(f"User>\t {messages[0]['content']}")

tool = message.tool_calls[0]
messages.append(message)

messages.append({"role": "tool", "tool_call_id": tool.id, "content": "24℃"})
message = send_messages(messages)
print(f"Model>\t {message.content}")

The execution flow of this example is as follows:

User: Ask about the current weather
Model: Return function get_weather({location: 'Hangzhou'})
User: Call function get_weather({location: 'Hangzhou'}) and pass the result to the model
Model: Return natural language, "The current temperature in Hangzhou is 24°C."
Note: The get_weather function in the code above needs to be provided by the user; the model itself does not execute specific functions.

## Thinking Mode
Starting from DeepSeek-V3.2, the API supports tool calling in thinking mode. See Thinking Mode for details.

## Strict Mode (Beta)
In strict mode, the model will strictly follow the Function's JSON Schema format requirements when outputting Function calls, ensuring that the model's Function output conforms to the user's definition. Strict mode can be used for tool calls in both thinking and non-thinking modes.

To use strict mode, you need to:

Set base_url="https://api.deepseek.com/beta" to enable Beta features
In the passed tools list, all functions must set the strict property to true
The server will validate the JSON Schema of the user's Function. If it does not conform to the specification, or if a JSON Schema type unsupported by the server is encountered, an error message will be returned
Below is an example of a tool definition in strict mode:

{
    "type": "function",
    "function": {
        "name": "get_weather",
        "strict": true,
        "description": "Get weather of a location, the user should supply a location first.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                }
            },
            "required": ["location"],
            "additionalProperties": false
        }
    }
}

## JSON Schema Types Supported in Strict Mode
object
string
number
integer
boolean
array
enum
anyOf

### object Type
The object type defines a deep structure containing key-value pairs, where properties defines the schema for each key (attribute) in the object. All attributes of each object must be set to required, and the additionalProperties attribute in the object must be false.

Example:

{
    "type": "object",
    "properties": {
        "name": { "type": "string" },
        "age": { "type": "integer" }
    },
    "required": ["name", "age"],
    "additionalProperties": false
}

### string Type
Supported parameters:
pattern: Use regular expressions to constrain the format of the string
format: Use predefined common formats for validation, currently supported:
email: Email address
hostname: Hostname
ipv4: IPv4 address
ipv6: IPv6 address
uuid: UUID

Unsupported parameters:
minLength
maxLength

Example:

{
    "type": "object",
    "properties": {
        "user_email": {
            "type": "string",
            "description": "The user's email address",
            "format": "email" 
        },
        "zip_code": {
            "type": "string",
            "description": "Six digit postal code",
            "pattern": "^\\\\d{6}$"
        }
    }
}

### number/integer Type
Supported parameters:
const: Fix the number as a constant
default: Default value for the number
minimum: Minimum value
maximum: Maximum value
exclusiveMinimum: Not less than
exclusiveMaximum: Not greater than
multipleOf: The number output is a multiple of this value

Example:

{
    "type": "object",
    "properties": {
        "score": {
            "type": "integer",
            "description": "A number from 1-5, which represents your rating, the higher, the better",
            "minimum": 1,
            "maximum": 5
        }
    },
    "required": ["score"],
    "additionalProperties": false
}

### array Type
Unsupported parameters:
minItems
maxItems

Example:

{
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "description": "Five keywords of the article, sorted by importance",
            "items": {
                "type": "string",
                "description": "A concise and accurate keyword or phrase."
            }
        }
    },
    "required": ["keywords"],
    "additionalProperties": false
}

### enum
Enum ensures that the output is one of several expected options. For example, in an order status scenario, it can only be one of a limited number of states.

Example:

{
    "type": "object",
    "properties": {
        "order_status": {
            "type": "string",
            "description": "Ordering status",
            "enum": ["pending", "processing", "shipped", "cancelled"]
        }
    }
}

### anyOf
Matches any one of the provided schemas, which can handle fields that may have multiple valid formats. For example, a user's account may be either an email address or a phone number:

{
    "type": "object",
    "properties": {
    "account": {
        "anyOf": [
            { "type": "string", "format": "email", "description": "Can be an email address" },
            { "type": "string", "pattern": "^\\\\d{11}$", "description": "Or an 11-digit phone number" }
        ]
    }
  }
}

### $ref and $def
You can use $def to define modules and then use $ref to reference them to reduce schema duplication and enable modularity. Additionally, $ref can be used independently to define recursive structures.

{
    "type": "object",
    "properties": {
        "report_date": {
            "type": "string",
            "description": "The date when the report was published"
        },
        "authors": {
            "type": "array",
            "description": "The authors of the report",
            "items": {
                "$ref": "#/$def/author"
            }
        }
    },
    "required": ["report_date", "authors"],
    "additionalProperties": false,
    "$def": {
        "authors": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "author's name"
                },
                "institution": {
                    "type": "string",
                    "description": "author's institution"
                },
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "author's email"
                }
            },
            "additionalProperties": false,
            "required": ["name", "institution", "email"]
        }
    }
}

Previous page