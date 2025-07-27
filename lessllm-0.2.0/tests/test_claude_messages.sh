#!/bin/bash

# Test script for Claude Messages API

echo "Testing Claude Messages API with curl..."

# Test non-streaming request
curl -X POST "http://localhost:8000/v1/messages?beta=true" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Claude-CLI/1.0" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "messages": [
      {
        "role": "user",
        "content": "Hello! How are you?"
      }
    ]
  }'

echo -e "\n\nTest completed."