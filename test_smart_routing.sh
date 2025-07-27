#!/bin/bash

# Test script for smart routing functionality

echo "=== LessLLM Smart Routing Test ==="
echo ""

BASE_URL="http://localhost:8000"

echo "1. Testing Claude Messages API with Claude model (should use direct passthrough)"
echo "   /v1/messages + claude-3-5-sonnet → Claude Provider (direct)"
echo ""
curl -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Test-Client/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Please respond: Claude Messages API direct passthrough working"
      }
    ]
  }'

echo -e "\n\n2. Testing Claude Messages API with GPT model (should convert to OpenAI)"
echo "   /v1/messages + gpt-4 → OpenAI Provider (convert Claude→OpenAI)"
echo ""
curl -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Test-Client/1.0" \
  -d '{
    "model": "gpt-4",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Please respond: Claude to OpenAI conversion working"
      }
    ]
  }'

echo -e "\n\n3. Testing OpenAI Chat Completions API with GPT model (should use direct passthrough)"
echo "   /v1/chat/completions + gpt-4 → OpenAI Provider (direct)"
echo ""
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Test-Client/1.0" \
  -d '{
    "model": "gpt-4",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user", 
        "content": "Please respond: OpenAI Chat Completions direct passthrough working"
      }
    ]
  }'

echo -e "\n\n4. Testing OpenAI Chat Completions API with Claude model (should convert to Claude)"
echo "   /v1/chat/completions + claude-3-5-sonnet → Claude Provider (convert OpenAI→Claude)"
echo ""
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Test-Client/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Please respond: OpenAI to Claude conversion working"
      }
    ]
  }'

echo -e "\n\n=== Test completed ==="
echo ""
echo "Expected behaviors:"
echo "1. Claude Messages + Claude model = Direct passthrough (Claude format response)"
echo "2. Claude Messages + GPT model = Convert to OpenAI then back to Claude format"
echo "3. OpenAI Chat + GPT model = Direct passthrough (OpenAI format response)" 
echo "4. OpenAI Chat + Claude model = Convert to Claude then back to OpenAI format"