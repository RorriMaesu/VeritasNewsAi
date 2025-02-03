import os
import sys
import yaml
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'src'))

# Now we can import from core
from core.script_generator import ScriptGenerator
from core.voice_generator import VoiceGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_narration():
    """Test script generation and narration"""
    try:
        # Load config
        config_path = project_root / 'config' / 'settings.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Generate script
        generator = ScriptGenerator(config['script_generation'])
        script = generator.generate_script()
        
        if not script:
            logger.error("Script generation failed")
            return
            
        # Print sections for verification
        print("\nGenerated Script Sections:")
        print("-" * 50)
        for section, content in script['content']['sections'].items():
            print(f"\n{section.upper()}:")
            print(content[:100] + "..." if len(content) > 100 else content)
            
        # Generate speech
        voice_gen = VoiceGenerator(config['voice_generation'])
        speech_path = voice_gen.generate_speech(script)
        
        if speech_path:
            print(f"\nSpeech generated: {speech_path}")
        else:
            print("\nSpeech generation failed")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_narration() 