import pyautogui
import time
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_three_dots_detection():
    """Test three dots menu detection with adjustable parameters."""
    try:
        # Get image path using same resolution as main code
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(
            parent_dir,
            "data",
            "pyautogui_image_files",
            "three_dots_image.png"
        )
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image missing at {image_path}")

        # Configurable test parameters
        confidence = 0.9  # Lower threshold
        grayscale = True  # Match main code's grayscale
        region = None  # Search full screen
        attempts = 5
        delay_between_attempts = 2  # seconds

        # Alternative region calculation
        screen_width, screen_height = pyautogui.size()
        custom_region = (
            int(screen_width * 0.8),  # Right 20%
            0,
            int(screen_width * 0.2),  # 20% width
            screen_height
        )

        logging.info(f"Starting three dots detection test with:")
        logging.info(f"Image: {image_path}")
        logging.info(f"Confidence: {confidence}")
        logging.info(f"Custom Region: {custom_region}")
        logging.info(f"Resolved image path: {os.path.abspath(image_path)}")

        for attempt in range(1, attempts+1):
            logging.info(f"Attempt {attempt}/{attempts}")
            
            # Visual feedback for search area
            pyautogui.alert("Check screen for region highlight")
            pyautogui.moveTo(custom_region[0], custom_region[1])
            pyautogui.dragTo(
                custom_region[0] + custom_region[2],
                custom_region[1] + custom_region[3],
                duration=1,
                button='left'
            )
            
            location = pyautogui.locateCenterOnScreen(
                image_path,
                confidence=confidence,
                grayscale=grayscale,
                region=region
            )
            
            if location:
                logging.success(f"Found at {location} with confidence >= {confidence}")
                pyautogui.moveTo(location)
                return True
                
            logging.warning("Not found in this attempt")
            time.sleep(delay_between_attempts)

        logging.error("All attempts failed")
        return False

    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        return False

if __name__ == '__main__':
    time.sleep(5)  # Added initial delay
    test_three_dots_detection()

# Capture current screen area for debugging
test_region = (custom_region[0], custom_region[1], 300, 200)  # Capture part of search area
pyautogui.screenshot("debug_screenshot.png", region=test_region)