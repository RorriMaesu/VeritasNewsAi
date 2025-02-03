import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import re

import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import ollama
from ollama import Client

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # Ensure debug logs are captured

class ScriptGenerator:
    """
    Generates and refines a professional news script with DeepSeek and Gemini Flash.
    Ensures proper formatting, neutral tone, and TTS compatibility.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.brand_name = config.get('brand_name', 'Veritas Lens AI')
        self.max_refine_iterations = config.get('max_refine_iterations', 3)
        self.deepseek_model = config.get('deepseek_model', 'deepseek-r1')

        # Directories for storing scripts
        base_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        self.temp_refine_dir = os.path.join(base_dir, 'data', 'temp_refine')
        self.narration_dir = os.path.join(base_dir, 'data', 'narration')
        os.makedirs(self.temp_refine_dir, exist_ok=True)
        os.makedirs(self.narration_dir, exist_ok=True)

        # Initialize DeepSeek LLM client
        self.deepseek_client = Client()

        # Initialize Gemini Flash LLM client
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY", "")
        if not self.gemini_api_key:
            logger.warning("GOOGLE_API_KEY not found. Gemini Flash critiques may fail.")
            self.gemini_model = None
        else:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("Gemini Flash model configured successfully.")
            except Exception as e:
                logger.error(f"Failed to configure Gemini Flash model: {e}")
                self.gemini_model = None

    def generate_script(self, top_stories: List[Dict]) -> Optional[Dict]:
        """
        Main function to generate the final narration script based on the provided top stories.
        """
        if not top_stories:
            logger.error("No top stories provided.")
            return None

        try:
            # 1) Build initial script with DeepSeek
            initial_script = self._build_initial_script(top_stories)
            logger.info("Initial script generated using DeepSeek.")

            # 2) Parse bracketed sections
            sections = self._parse_bracketed_sections(initial_script)
            if not sections:
                logger.error("Failed to parse bracketed sections from DeepSeek output.")
                return None
            logger.info("Parsed bracketed sections from initial script.")

            # 3) Refine each section with iterative approach
            refined_sections = {}
            for section_key, section_text in sections.items():
                new_text = self._iterative_refine_section(section_key, section_text)
                refined_sections[section_key] = new_text
                logger.info(f"Section '{section_key}' refined successfully.")

            # 4) Cleanup for TTS
            cleaned_sections = {}
            for key, text in refined_sections.items():
                cleaned_text = self._final_tts_filter(text)
                cleaned_sections[key] = cleaned_text

            # 5) Assemble final narration object
            final_narration = {
                "metadata": {
                    "brand_name": self.brand_name,
                    "generated_at": datetime.now().isoformat(),
                    "llms_used": ["DeepSeek-r1", "Gemini Flash"],
                    "refinement_iterations": self.max_refine_iterations
                },
                "sections": cleaned_sections
            }

            # 6) Save final script to JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            narration_filename = f"final_narration_{timestamp}.json"
            narration_path = os.path.join(self.narration_dir, narration_filename)

            with open(narration_path, 'w', encoding='utf-8') as f:
                json.dump(final_narration, f, indent=2)

            logger.info(f"Final narration script saved to {narration_path}")
            return final_narration

        except Exception as e:
            logger.exception(f"An error occurred during script generation: {e}")
            return None

    def _build_initial_script(self, stories: List[Dict]) -> str:
        """
        Generates the initial bracketed script using DeepSeek.
        """
        prompt = self._build_deepseek_prompt(stories)
        return self._call_deepseek(prompt)

    def _build_deepseek_prompt(self, stories: List[Dict]) -> str:
        """Structured prompt with output constraints"""
        story_details = "\n".join([f"- {s.get('title')}: {s.get('description')}" 
                                for s in stories])
        return f"""
You are a professional news scriptwriter. Generate a TV news broadcast script.

**STRICT RULES:**
1. Use ONLY these sections: [HOOK], [HEADLINES], [MAIN_STORY_1], [MAIN_STORY_2], [MAIN_STORY_3], [OUTRO]
2. Output ONLY the spoken narration text
3. NEVER include:
   - AI reasoning/thinking (no <think>/</think>)
   - Visual directions (e.g., "show map")
   - Production notes
   - Revision comments
4. Use concise, spoken English with proper punctuation
5. Maintain neutral tone with clear subject-verb-object structure

**TOP STORIES:**
{story_details}

**EXAMPLE FORMAT:**
[HOOK]
Breaking news tonight: [Concise attention-grabbing lead]

[HEADLINES]
- First headline summary
- Second headline summary
- Third headline summary

[MAIN_STORY_1]
Detailed report with key facts...

[OUTRO]
That's all for tonight. For updates visit...

Generate the news script:"""

    def _parse_bracketed_sections(self, raw_text: str) -> Dict[str, str]:
        """
        Extracts sections from the generated script by detecting bracketed headers.
        Removes any extraneous meta commentary including <think> tags.
        """
        # Enhanced removal of chain-of-thought markers with different casing
        raw_text = re.sub(
            r'(?i)\[?\/?think.*?\]?',  # Handles [Think], [THINK], [/think] etc
            '', 
            raw_text, 
            flags=re.DOTALL
        )
        
        sections = {}
        current_section = None
        buffer = []

        for line in raw_text.splitlines():
            line = line.strip()
            match = re.match(r'^\[(.*?)\]$', line)
            if match:
                if current_section and buffer:
                    sections[current_section] = " ".join(buffer).strip()
                current_section = match.group(1).lower().replace(" ", "_")
                buffer = []
            elif current_section:
                buffer.append(line)
        if current_section and buffer:
            sections[current_section] = " ".join(buffer).strip()

        return sections

    def _iterative_refine_section(self, section_key: str, section_text: str) -> str:
        """
        Iteratively refines a script section using Gemini for critique
        and DeepSeek for revisions based on that critique.
        """
        refined = section_text
        for iteration in range(self.max_refine_iterations):
            if not refined.strip():
                break

            # 1) Generate critique with Gemini
            critique = self._call_gemini(
                f"**Critique this news script section**:\n{refined}\n\n"
                "Focus on viewer engagement, clarity, neutrality. Provide short bullet points of improvement."
            )
            if not critique.strip():
                logger.warning(f"Empty critique for section '{section_key}' (iteration {iteration+1}).")
                break

            # 2) Generate revision with DeepSeek
            revision_prompt = (
                f"**Revise this news script section**:\n{refined}\n\n"
                f"**Apply these critique points**:\n{critique}\n\n"
                "Limit changes to clarity, engagement, neutrality. Do not add extraneous text or commentary."
            )
            revised = self._call_deepseek(revision_prompt)
            if not revised.strip():
                logger.debug(f"DeepSeek revision empty. Keeping previous version for '{section_key}'.")
                break

            # 3) Compare old vs new for improvement
            if self._is_improved(refined, revised):
                refined = revised
                logger.debug(f"Section '{section_key}' improved in iteration {iteration+1}.")
            else:
                logger.debug(f"No improvement for section '{section_key}' at iteration {iteration+1}. Stopping.")
                break

            # 4) Save iteration
            self._save_iteration(section_key, iteration, refined)

        return refined

    def _call_deepseek(self, prompt: str) -> str:
        """
        Calls DeepSeek to generate or revise the script.
        """
        try:
            response = self.deepseek_client.generate(
                model=self.deepseek_model, 
                prompt=prompt, 
                stream=False
            )
            # Add immediate response cleaning
            raw_response = response.get('response', "")
            return re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            return ""

    def _call_gemini(self, prompt: str) -> str:
        """
        Calls Gemini Flash model to critique or assist with short instructions.
        """
        if not self.gemini_model:
            logger.warning("Gemini model not configured. Returning empty critique.")
            return ""
        try:
            response = self.gemini_model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            else:
                return ""
        except Exception as e:
            logger.error(f"Gemini Flash call failed: {e}")
            return ""

    def _is_improved(self, old_text: str, new_text: str) -> bool:
        """
        Checks if new_text is a meaningful improvement over old_text.
        """
        old_c = old_text.strip().lower()
        new_c = new_text.strip().lower()
        return (old_c != new_c) and (len(new_text.strip()) > 0)

    def _final_tts_filter(self, structured_output: dict) -> str:
        """Hybrid cleaning approach using Gemini Flash + regex"""
        # First LLM-based cleaning
        cleaning_prompt = """Extract ONLY spoken text from this JSON structure.
        Remove ALL technical fields/metadata. Combine into continuous prose.
        
        Input: {structured_output}
        Output:"""
        
        try:
            gemini_clean = self._generate_content(
                cleaning_prompt.format(structured_output=structured_output),
                llm_choice='gemini_flash',
                temperature=0.1
            )
        except Exception as e:
            logger.error(f"Gemini cleaning failed: {e}")
            gemini_clean = str(structured_output)
        
        # Final regex safety net
        return self._clean_script(gemini_clean)

    def _clean_script(self, script: str) -> str:
        """Lightweight regex-based final cleanup"""
        # Remove JSON artifacts
        script = re.sub(r'["{}]|\b(?:metadata|sections)\b', '', script)
        
        # Remove residual special characters
        script = re.sub(r'[*_#]', '', script)
        
        # Normalize whitespace
        return re.sub(r'\s+', ' ', script).strip()

    def _save_iteration(self, section_key: str, iteration: int, content: str):
        """
        Saves iteration text for debugging and transparency.
        """
        section_dir = os.path.join(self.temp_refine_dir, f"section_{section_key}")
        os.makedirs(section_dir, exist_ok=True)
        filename = f"iteration_{iteration+1}.txt"
        path = os.path.join(section_dir, filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"Saved iteration {iteration+1} for section '{section_key}' at {path}.")
        except Exception as e:
            logger.error(f"Failed saving iteration for section '{section_key}': {e}")

    def generate_full_script(self, prompts: dict) -> str:
        raw_output = self._generate_structured_content(prompts)
        return self._final_tts_filter(raw_output)

    def _generate_content(self, prompt: str, llm_choice: str = None, **kwargs) -> str:
        llm_choice = llm_choice or self.config.get('llm_choice', 'local_deepseek')
        
        if 'gemini' in llm_choice.lower():
            return self._gemini_client.generate(prompt, **kwargs)
        else:
            return self._deepseek_client.generate(prompt, **kwargs)

    def _generate_structured_content(self, prompts: dict) -> dict:
        """
        Generates content with enforced JSON structure using DeepSeek R1
        """
        structure_prompt = f"""Generate news script as JSON with EXACTLY these keys:
        {json.dumps(list(prompts.keys()))}
        
        Rules:
        1. Output ONLY spoken narration text
        2. Use clean punctuation
        3. No markdown/formatting
        4. No meta-commentary
        
        Context: {prompts}
        """
        
        try:
            raw_output = self._generate_content(
                structure_prompt,
                llm_choice='local_deepseek',
                temperature=0.3
            )
            return json.loads(raw_output)
        except json.JSONDecodeError:
            logger.warning("Failed parsing structured output, attempting recovery...")
            return self._recover_structured_content(raw_output)

    def _gemini_tts_cleanup(self, raw_text: str) -> str:
        """Final cleanup using Gemini Flash 2.0 to remove non-broadcast content"""
        cleanup_prompt = """STRICT INSTRUCTIONS FOR NEWS SCRIPT CLEANUP:
1. REMOVE ALL revision notes, section headers, and meta-commentary
2. DELETE these exact phrases and similar:
   - "Revised News Script Section:"
   - "Here's a revised version of..."
   - "Incorporating the critique points..."
   - "This version enhances..."
3. PRESERVE ONLY the final spoken narration
4. OUTPUT clean, continuous prose with proper punctuation

INPUT TEXT TO CLEAN:
{input}

CLEAN OUTPUT:"""
        
        try:
            response = self._generate_content(
                cleanup_prompt.format(input=raw_text),
                llm_choice='gemini_flash',
                temperature=0.1,  # Keep highly deterministic
                max_tokens=4000
            )
            return self._final_sanitization(response)
        
        except Exception as e:
            logger.error(f"Gemini TTS cleanup failed: {e}")
            return self._fallback_cleanup(raw_text)

    def _final_sanitization(self, text: str) -> str:
        """Last-chance regex cleanup"""
        # Remove residual metadata markers
        text = re.sub(r'(?i)\b(revised\s+version|script\s+section):?', '', text)
        # Remove any remaining bracketed comments
        text = re.sub(r'\[[^\]]*\]', '', text)
        # Collapse whitespace
        return re.sub(r'\s+', ' ', text).strip()

    def generate_tts_ready_script(self, raw_json: dict) -> str:
        """Full processing pipeline"""
        try:
            # Extract JSON content
            combined_text = ' '.join(raw_json['sections'].values())
            # Gemini cleanup
            return self._gemini_tts_cleanup(combined_text)
        except KeyError:
            logger.error("Invalid JSON structure, performing raw cleanup")
            return self._final_sanitization(str(raw_json))


if __name__ == "__main__":
    """
    Example usage:
    Pass in top_stories as a list of dictionaries, each containing a 'title' and 'description'.
    The script generator will return a final JSON structure with generated narration.
    """
    # Example input
    example_stories = [
        {"title": "Citizenship by Birthright? By Bloodline?", 
         "description": "Recent migration trends are putting traditional definitions under the microscope."},
        {"title": "Elon Musk's Startup Tactics in Europe", 
         "description": "How emerging tech strategies could shake up political landscapes across the EU."},
        {"title": "Conflict in Gaza", 
         "description": "Ongoing tension and a personal story of one survivor's final days."}
    ]

    config = {
        "brand_name": "Veritas Lens AI",
        "max_refine_iterations": 3,
        "deepseek_model": "deepseek-r1"
    }

    generator = ScriptGenerator(config)
    final_script = generator.generate_script(example_stories)

    if final_script:
        print(json.dumps(final_script, indent=2))
