#!/bin/bash

# Test streaming with Aliyun Claude proxy

API_KEY="sk-001061f9c18447ecbed88b9bb6d87871"
BASE_URL="https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy"

echo "Testing Aliyun Claude streaming..."
echo ""

curl -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "User-Agent: LessLLM-Test/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "stream": true,
    "messages": [
      {
        "role": "user",
        "content": "Please count from 1 to 5, one number per line."
      }
    ]
  }' \
  --no-buffer

echo -e "\n\nStreaming test completed."