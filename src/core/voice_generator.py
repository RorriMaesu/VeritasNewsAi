import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings
from dotenv import load_dotenv
import re

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # Ensure debug logs are captured

class VoiceGenerator:
    """
    VoiceGenerator uses ElevenLabs to convert final narration scripts into speech files.

    Updated to:
      1. Reference 'sections' from final script JSON.
      2. Accommodate up to 9 main stories plus hook, headlines, and outro.
      3. Use new file naming format from config.
      4. Remove any internal meta-commentary (e.g., content within <think> tags) and special characters 
         that TTS should not speak (such as *, _, #, ^, `, { }, and stray angle brackets).
    """

    def __init__(self, config: Dict):
        self.config = config
        self.api_key = os.getenv("ELEVENLABS_KEY")
        if not self.api_key:
            logger.error("ELEVENLABS_KEY not found in environment")
            raise ValueError("Missing ELEVENLABS_KEY")
        
        self.client = ElevenLabs(api_key=self.api_key)

        # Prepare output directory
        output_dir = self.config.get('output_dir', './data/speech')
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        
        # Gather other config parameters
        self.voice_id = self.config.get('voice_id', '')
        self.model_id = self.config.get('model_id', 'eleven_multilingual_v2')
        self.stability = self.config.get('stability', 0.7)
        self.similarity_boost = self.config.get('similarity_boost', 0.7)
        self.filename_format = self.config.get('filename_format', '%Y%m%d_%H%M%S_speech.mp3')

    def generate_speech(self, script_data: Dict) -> Optional[str]:
        """
        Generate speech from final narration script and return the output path.
        
        Expects 'sections' within script_data.
        Will read sections in the following order:
          [HOOK], [HEADLINES], up to 9 MAIN_STORYs, then [OUTRO].
        """
        # 1) Validate script structure
        if 'sections' not in script_data:
            logger.error("Script data missing 'sections' key.")
            return None
        
        sections = script_data['sections']
        if not isinstance(sections, dict):
            logger.error("'sections' is not a dictionary. Invalid script format.")
            return None
        
        # 2) Assemble full script in desired order
        narration_order = (
            ['hook', 'headlines'] +
            [f'main_story_{i}' for i in range(1, 10)] +
            ['outro']
        )
        raw_script_list = []
        for section_key in narration_order:
            if section_key in sections and sections[section_key].strip():
                raw_script_list.append(sections[section_key].strip())
        
        full_script = "\n\n".join(raw_script_list)
        if not full_script.strip():
            logger.error("No valid content to speak after assembling sections.")
            return None
        
        # 3) Clean script text for TTS: remove <think> tags, unwanted punctuation, and special characters.
        cleaned_script = self._clean_script(full_script)
        if not cleaned_script:
            logger.error("No valid narration content found after cleaning.")
            return None

        # 4) Generate filename from config's filename_format
        filename = datetime.now().strftime(self.filename_format)
        output_path = os.path.join(self.output_dir, filename)
        
        # 5) Call ElevenLabs TTS
        try:
            logger.info("Attempting ElevenLabs speech generation...")
            audio_stream = self.client.generate(
                text=cleaned_script,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=self.stability,
                        similarity_boost=self.similarity_boost,
                        style=0.0,  # Additional parameter if needed
                        use_speaker_boost=True
                    )
                ),
                model=self.model_id
            )
            
            with open(output_path, "wb") as f:
                for chunk in audio_stream:
                    f.write(chunk)
            
            logger.info(f"ElevenLabs speech generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"ElevenLabs generation failed: {e}")
            logger.info("Attempting fallback TTS (gTTS)...")
            return self._generate_fallback_tts(cleaned_script, output_path)

    def _generate_fallback_tts(self, text: str, output_path: str) -> Optional[str]:
        """Fallback TTS using gTTS if ElevenLabs fails."""
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            logger.info(f"Fallback TTS generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Fallback TTS failed: {e}")
            return None

    def _clean_script(self, script: str) -> str:
        """Enhanced cleaning to remove all asterisk-enclosed content"""
        try:
            # Remove <think> tags first
            script = re.sub(r'<think>.*?</think>', '', script, flags=re.DOTALL | re.IGNORECASE)
            
            # New: Remove any content between asterisks (1+ asterisks on both sides)
            script = re.sub(r'\*{1,}(?!\s*$).*?\*{1,}', '', script, flags=re.DOTALL)
            
            # New: Remove lines starting/ending with asterisks (catch malformed patterns)
            script = re.sub(r'^\*+.*', '', script, flags=re.MULTILINE)
            script = re.sub(r'.*\*+$', '', script, flags=re.MULTILINE)
            
            # Existing cleanup patterns
            script = re.sub(r'\[[^\]]*\]', '', script)
            script = re.sub(r'\([^)]*\)', '', script)
            script = re.sub(r'[^a-zA-Z0-9\s.,!?\'’]', '', script)
            
            # Normalize and return
            script = re.sub(r'\s+', ' ', script).strip()
            
            # Split into sentences and ensure proper sentence termination
            sentences = re.split(r'(?<=[.!?]) +', script)
            cleaned_sentences = []
            for sent in sentences:
                sent = sent.strip()
                if sent:
                    sent = sent[0].upper() + sent[1:]
                    if not sent.endswith((".", "!", "?")):
                        sent += "."
                    cleaned_sentences.append(sent)
            
            return ' '.join(cleaned_sentences)
            
        except Exception as e:
            logger.error(f"Script cleaning failed: {e}")
            return ""

if __name__ == "__main__":
    # Example usage:
    # Load a final script JSON file (here, using an example script dictionary)
    example_script = {
        "metadata": {
            "brand_name": "Veritas Lens AI",
            "generated_at": datetime.now().isoformat(),
            "llms_used": ["DeepSeek-r1", "Gemini Flash"],
            "refinement_iterations": 3
        },
        "sections": {
            "hook": "<think>This internal reasoning should not be read.</think>Good evening, everyone.",
            "headlines": "Today's headlines include major developments in international trade.",
            "main_story_1": "Our top story: the stock market saw unprecedented gains.",
            "main_story_2": "In local news, city officials announce new public safety measures.",
            "main_story_3": "Sports update: the local team clinched the championship title.",
            "outro": "Thank you for watching. Stay tuned for more updates."
        }
    }

    config = {
        "output_dir": "./data/speech",
        "voice_id": "example_voice_id",
        "model_id": "eleven_multilingual_v2",
        "stability": 0.7,
        "similarity_boost": 0.7,
        "filename_format": "%Y%m%d_%H%M%S_speech.mp3"
    }

    vg = VoiceGenerator(config)
    audio_file = vg.generate_speech(example_script)
    if audio_file:
        print(f"Audio generated at: {audio_file}")
