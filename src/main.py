import os
import json
import logging
from datetime import datetime
import yaml
import traceback

from core.news_aggregator import NewsAggregator
from core.script_generator import ScriptGenerator

# 1) Import the VoiceGenerator
from core.voice_generator import VoiceGenerator
from core.deep_dive import main as deep_dive_main

# Configure logging
logging.basicConfig(
    filename='pipeline.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.debug("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing the configuration file: {e}")
        raise

def main():
    """
    Pipeline Flow:
    1. Aggregate multi-source news, store in data/news.
    2. Use DeepSeek to rank & pick top 9 stories, store in data/top_news.
    3. ScriptGenerator -> final narration in data/narration.
    4. VoiceGenerator -> TTS from final script -> data/speech.
    """
    config_path = os.path.join(
        os.path.dirname(__file__),
        '..', 
        'config', 
        'settings.yaml'
    )
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        print("Failed to load configuration. Check logs for details.")
        return

    try:
        logger.info("Starting news aggregation cycle")
        
        # 1) Aggregation
        agg_cfg = config.get('news_aggregation', {})
        aggregator = NewsAggregator(agg_cfg)
        all_news = aggregator.aggregate_news()
        if not all_news:
            logger.warning("No news items after aggregation.")
            print("No news items. Exiting pipeline.")
            return
        
        # 2) Pick top 9 stories
        top_news = aggregator.pick_top_stories(all_news, count=9)
        if not top_news or len(top_news) < 9:
            logger.warning(f"Only {len(top_news)} top stories selected. Expected 9.")
            print(f"Only {len(top_news)} top stories selected. Proceeding with available stories.")
        
        # 3) Script Generation
        script_cfg = config.get('script_generation', {})
        if not script_cfg:
            logger.error("Missing 'script_generation' config.")
            print("Missing script_generation config. Cannot proceed.")
            return
        
        script_gen = ScriptGenerator(script_cfg)
        final_script = script_gen.generate_script(top_news)
        if not final_script:
            logger.error("Script generation failed or returned None.")
            print("Script generation failed. See logs.")
            return

        # Save final script
        narration_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'narration')
        os.makedirs(narration_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_name = f"final_narration_{timestamp}.json"
        final_path = os.path.join(narration_dir, final_name)

        with open(final_path, 'w', encoding='utf-8') as f:
            json.dump(final_script, f, indent=2)

        logger.info(f"Final newscast script saved to {final_path}")
        print(f"Script generation complete. Narration at: {final_path}")
        
        # 4) Voice Generation: Convert final script to speech
        voice_cfg = config.get('voice_generation', {})
        if not voice_cfg:
            logger.warning("No 'voice_generation' config found. Skipping TTS step.")
            return
        
        voice_gen = VoiceGenerator(voice_cfg)
        audio_path = voice_gen.generate_speech(final_script)
        
        if audio_path:
            logger.info(f"Speech generation complete. Audio saved at: {audio_path}")
            print(f"Speech generation complete. Audio at: {audio_path}")
        else:
            logger.warning("Speech generation returned None. Check logs for details.")
        
        # New Section: Automated Deep Dive
        try:
            logger.info("Starting automated deep dive process")
            print("\nStarting notebook automation...")
            deep_dive_main()
            logger.info("Deep dive process completed successfully")
            print("Deep dive automation finished")
        except Exception as e:
            logger.error(f"Deep dive process failed: {str(e)}")
            logger.error(traceback.format_exc())
            print("Deep dive automation failed. Check logs for details.")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        print("Pipeline execution failed. See pipeline.log for details.")

if __name__ == "__main__":
    main()
