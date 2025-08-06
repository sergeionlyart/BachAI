#!/usr/bin/env python3
"""Test script to understand OpenAI Responses API format"""

import json

# Simplified sample response structure
sample_response = {
    "custom_id": "vision:5YJ3E1EB5KF433798",
    "response": {
        "body": {
            "text": {
                "format": {"type": "text"}
            },
            "output": [
                {
                    "content": [
                        {
                            "text": "Looking at this Tesla Model 3, I can observe several condition and damage indicators... [FULL CAR DESCRIPTION HERE]",
                            "type": "text"
                        }
                    ],
                    "type": "reasoning"
                }
            ]
        }
    }
}

print("=== OpenAI Responses API Structure Analysis ===\n")

print("1. Top level keys:", list(sample_response.keys()))
print("\n2. Response body keys:", list(sample_response['response']['body'].keys()))

# The issue: we're saving 'text' field which contains format info
text_field = sample_response['response']['body']['text']
print("\n3. Text field (WRONG - this is what we're saving):", text_field)

# The correct field: 'output' contains the actual content
output_field = sample_response['response']['body']['output']
print("\n4. Output field structure:")
print("   - Type:", type(output_field))
print("   - Length:", len(output_field))

if output_field and len(output_field) > 0:
    first_output = output_field[0]
    print("\n5. First output item:")
    print("   - Type:", first_output.get('type'))
    print("   - Content type:", type(first_output.get('content')))
    
    content = first_output.get('content', [])
    if content and len(content) > 0:
        first_content = content[0]
        print("\n6. First content item:")
        print("   - Type:", first_content.get('type'))
        print("   - Text length:", len(first_content.get('text', '')))
        print("   - Text preview:", first_content.get('text', '')[:100] + "...")

print("\n=== SOLUTION ===")
print("We need to extract: response['body']['output'][0]['content'][0]['text']")
print("NOT: response['body']['text'] (which only contains format info)")

# Show the correct extraction
correct_text = sample_response['response']['body']['output'][0]['content'][0]['text']
print("\n=== CORRECT EXTRACTION ===")
print("Extracted text:", correct_text[:100] + "...")