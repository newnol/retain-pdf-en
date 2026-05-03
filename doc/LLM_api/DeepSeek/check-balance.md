Check Balance
GET
https://api.deepseek.com/user/balance
Check account balance

Responses
200
OK, returns user balance details

application/json
Schema
Example (from schema)
Example
Schema

is_available
boolean
Whether the current account has balance available for API calls

balance_infos

object[]


Query Command

curl -L -X GET 'https://api.deepseek.com/user/balance' \
-H 'Accept: application/json' \
-H 'Authorization: Bearer sk-8d9400da2f484b54b95343959122722b'


Response structure:
```
{
  "is_available": true,
  "balance_infos": [
    {
      "currency": "CNY",
      "total_balance": "110.00",
      "granted_balance": "10.00",
      "topped_up_balance": "100.00"
    }
  ]
}
```