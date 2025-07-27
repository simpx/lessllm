#!/bin/bash

# Basic functionality test script

echo "=== LessLLM Basic Functionality Test ==="
echo ""

# Test if server can start (without actually starting it)
echo "1. Testing import and basic initialization..."
python3 -c "
try:
    from lessllm.server import app, init_app
    from lessllm.config import get_config
    from lessllm.providers.claude import ClaudeProvider
    from lessllm.providers.openai import OpenAIProvider
    print('✅ All imports successful')
    
    # Test config loading
    config = get_config()
    print('✅ Config loading successful')
    
    # Test provider initialization
    claude_provider = ClaudeProvider('test-key', None, 'https://test.com')
    print('✅ Claude provider initialization successful')
    
    print('✅ Basic functionality test passed!')
    
except Exception as e:
    print(f'❌ Test failed: {e}')
    exit(1)
"

echo ""
echo "2. Testing Claude Messages API conversion functions..."
python3 -c "
try:
    from lessllm.server import convert_claude_to_openai, convert_openai_to_claude_response
    
    # Test Claude to OpenAI conversion
    claude_request = {
        'model': 'claude-3-5-sonnet-20241022',
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'max_tokens': 100
    }
    
    openai_request = convert_claude_to_openai(claude_request)
    print('✅ Claude to OpenAI conversion successful')
    print(f'   Converted model: {openai_request[\"model\"]}')
    print(f'   Message count: {len(openai_request[\"messages\"])}')
    
    # Test OpenAI to Claude response conversion
    openai_response = {
        'id': 'test-id',
        'model': 'claude-3-5-sonnet-20241022',
        'choices': [{'message': {'content': 'Hello world'}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 20}
    }
    
    claude_response = convert_openai_to_claude_response(openai_response)
    print('✅ OpenAI to Claude response conversion successful')
    print(f'   Response type: {claude_response[\"type\"]}')
    print(f'   Content blocks: {len(claude_response[\"content\"])}')
    
    print('✅ Conversion functions test passed!')
    
except Exception as e:
    print(f'❌ Conversion test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo ""
echo "3. Testing streaming conversion functions..."
python3 -c "
try:
    from lessllm.server import convert_claude_streaming_to_openai, convert_openai_streaming_to_claude
    
    # Test Claude streaming to OpenAI
    claude_chunk = {
        'type': 'content_block_delta',
        'delta': {'type': 'text_delta', 'text': 'Hello'}
    }
    
    openai_chunk = convert_claude_streaming_to_openai(claude_chunk)
    if openai_chunk:
        print('✅ Claude streaming to OpenAI conversion successful')
        print(f'   Delta content: {openai_chunk[\"choices\"][0][\"delta\"][\"content\"]}')
    
    # Test OpenAI streaming to Claude
    openai_streaming_chunk = {
        'choices': [{'delta': {'content': 'World'}}]
    }
    
    claude_streaming_chunk = convert_openai_streaming_to_claude(openai_streaming_chunk)
    print('✅ OpenAI streaming to Claude conversion successful')
    print(f'   Chunk type: {claude_streaming_chunk[\"type\"]}')
    
    print('✅ Streaming conversion functions test passed!')
    
except Exception as e:
    print(f'❌ Streaming conversion test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo ""
echo "=== All basic functionality tests completed ==="