#!/bin/bash

# Test script for Aliyun Claude proxy configuration

API_KEY="sk-001061f9c18447ecbed88b9bb6d87871"
BASE_URL="https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy"

echo "Testing Aliyun Claude proxy configuration..."
echo "Base URL: $BASE_URL"
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Test 1: Basic Claude Messages API request
echo "=== Test 1: Basic Claude Messages API ==="
curl -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "User-Agent: LessLLM-Test/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Hello, please respond with just: Test successful"
      }
    ]
  }' \
  --verbose \
  --connect-timeout 10 \
  --max-time 30

echo -e "\n\n=== Test 2: Check if endpoint requires x-api-key instead ==="
curl -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -H "User-Agent: LessLLM-Test/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Hello, please respond with just: Test successful"
      }
    ]
  }' \
  --verbose \
  --connect-timeout 10 \
  --max-time 30

echo -e "\n\n=== Test 3: Try without /v1 prefix ==="
curl -X POST "${BASE_URL}/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "User-Agent: LessLLM-Test/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [
      {
        "role": "user",
        "content": "Hello, please respond with just: Test successful"
      }
    ]
  }' \
  --verbose \
  --connect-timeout 10 \
  --max-time 30

echo -e "\n\nTest completed."