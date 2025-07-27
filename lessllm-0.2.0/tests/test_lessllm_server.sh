#!/bin/bash

# Test LessLLM server with Claude Messages API

echo "Testing LessLLM server Claude Messages API..."
echo ""

# Test 1: Non-streaming request
echo "=== Test 1: Non-streaming request ==="
curl -X POST "http://localhost:8000/v1/messages" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Claude-CLI/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Hello! Please respond with: LessLLM test successful"
      }
    ]
  }'

echo -e "\n\n=== Test 2: Request with beta parameter (simulating Claude CLI) ==="
curl -X POST "http://localhost:8000/v1/messages?beta=true" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Claude-CLI/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Hello! Please respond with: Beta parameter test successful"
      }
    ]
  }'

echo -e "\n\n=== Test 3: Streaming request ==="
curl -X POST "http://localhost:8000/v1/messages" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Claude-CLI/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 30,
    "stream": true,
    "messages": [
      {
        "role": "user",
        "content": "Count from 1 to 3"
      }
    ]
  }' \
  --no-buffer

echo -e "\n\nAll tests completed."