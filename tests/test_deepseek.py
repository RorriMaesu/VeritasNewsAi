import logging
import yaml
from core.script_generator import ScriptGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_deepseek():
    # Test configuration
    config = {
        'brand_name': 'Test Brand',
        'llm_choice': 'local_deepseek',
        'temperature': 0.7,
        'debug_mode': True
    }
    
    try:
        # Initialize generator
        logger.info("Initializing ScriptGenerator with DeepSeek...")
        generator = ScriptGenerator(config)
        
        # Test prompts
        test_prompts = [
            "Write a short news headline about technology. Keep it under 50 words and make it engaging.",
            "Write a brief introduction for a news story about climate change. Keep it under 100 words.",
            "Generate a conclusion for a news report about space exploration. Keep it under 75 words.",
            "Generate a script section containing markdown and JSON, but needing clean speech output"
        ]
        
        responses = []
        for i, prompt in enumerate(test_prompts, 1):
            logger.info(f"\nTesting prompt {i}...")
            response = generator._generate_content(prompt)
            
            print(f"\nPrompt {i} response:")
            print("="*50)
            print(response)
            print("="*50)
            responses.append(response)
        
        # Add structured output test case
        test_prompts.append({
            "hook": "Create engaging opening",
            "headlines": "List top 3 stories",
            "main_story_1": "Detail first news story",
            "outro": "Create closing remarks"
        })
        
        # Add validation for structured output
        for response in responses:
            if isinstance(response, dict):
                assert 'metadata' not in response, "JSON metadata not filtered"
                assert all(isinstance(v, str) for v in response.values()), "Non-string values in output"
            else:
                assert '**' not in response, "Markdown not cleaned"
                assert '{' not in response, "JSON remnants found"
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_deepseek()
    print("\nTest result:", "Success" if success else "Failed") 