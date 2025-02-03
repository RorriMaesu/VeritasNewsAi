import time
import subprocess
import logging
import psutil
import traceback
import os
import pyautogui  # For image recognition and clicking
from pywinauto import Application
from pywinauto.keyboard import send_keys
import pyperclip  # Clipboard handling
import json
import re

# Configure logging to include debug level and traceback information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

#########################
# Browser-specific functions
#########################

def close_existing_edge():
    """Close any existing Microsoft Edge instances to prevent conflicts."""
    logging.debug("Closing existing Microsoft Edge processes.")
    for process in psutil.process_iter(attrs=['pid', 'name']):
        try:
            name = process.info['name']
            if name and "msedge.exe" in name.lower():
                logging.info(f"Terminating Edge process with PID: {process.info['pid']}")
                subprocess.run(["taskkill", "/F", "/PID", str(process.info['pid'])], shell=True)
        except Exception as e:
            logging.error("Error iterating processes: " + str(e))
            logging.error(traceback.format_exc())
    time.sleep(2)

def open_edge():
    """Launch Edge and wait for it to fully load before connecting."""
    logging.debug("Launching Microsoft Edge.")
    try:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        subprocess.Popen([edge_path])
        time.sleep(0.1)
        app = None
        for attempt in range(10):
            try:
                logging.debug(f"Attempt {attempt+1}: Connecting to Edge window.")
                app = Application(backend="uia").connect(title_re=".*Edge", timeout=2)
                break
            except Exception as e:
                logging.warning(f"Attempt {attempt+1} failed: {e}")
                time.sleep(0.5)
        if not app:
            raise Exception("Could not connect to Microsoft Edge after several attempts.")
        return app
    except Exception as e:
        logging.error("Error launching Edge: " + str(e))
        logging.error(traceback.format_exc())
        return None

def close_existing_chrome():
    """Close any existing Google Chrome instances to prevent conflicts."""
    logging.debug("Closing existing Google Chrome processes.")
    for process in psutil.process_iter(attrs=['pid', 'name']):
        try:
            name = process.info['name']
            if name and "chrome.exe" in name.lower():
                logging.info(f"Terminating Chrome process with PID: {process.info['pid']}")
                subprocess.run(["taskkill", "/F", "/PID", str(process.info['pid'])], shell=True)
        except Exception as e:
            logging.error("Error iterating processes: " + str(e))
            logging.error(traceback.format_exc())
    time.sleep(2)

def open_chrome():
    """Launch Google Chrome and wait for it to fully load before connecting."""
    logging.debug("Launching Google Chrome.")
    try:
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            raise FileNotFoundError("Google Chrome executable not found.")
        subprocess.Popen([chrome_path])
        time.sleep(0.1)
        app = None
        for attempt in range(10):
            try:
                logging.debug(f"Attempt {attempt+1}: Connecting to Chrome window.")
                app = Application(backend="uia").connect(title_re=".*Chrome", timeout=2)
                break
            except Exception as e:
                logging.warning(f"Attempt {attempt+1} failed: {e}")
                time.sleep(0.5)
        if not app:
            raise Exception("Could not connect to Google Chrome after several attempts.")
        return app
    except Exception as e:
        logging.error("Error launching Chrome: " + str(e))
        logging.error(traceback.format_exc())
        return None

#########################
# Common functions used in both branches
#########################

def navigate_to_notebook(app, url):
    """Navigate to a specific Notebook URL."""
    logging.debug(f"Navigating to: {url}")
    try:
        window = app.top_window()
        window.set_focus()
        time.sleep(0.5)
        send_keys("%d", pause=0)  # Alt+D to focus the address bar
        send_keys(f"{url}{{ENTER}}", pause=0)
        time.sleep(1)
        logging.info(f"Successfully navigated to {url}")
        return True
    except Exception as e:
        logging.error(f"Failed to navigate to notebook: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def click_create_new_button():
    """Click the 'Create new' button using pyautogui image recognition."""
    logging.debug("Attempting to click 'Create new' button via image recognition")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "create_new_image.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Create new button image missing at {image_path}")

        timeout = 15
        confidence = 0.7
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=True)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate 'Create new' button image")
        logging.info(f"Found 'Create new' button at {button_location}")
        pyautogui.moveTo(button_location, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Create new button click failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def click_copy_text_button():
    """Click the 'Copy text' button using pyautogui image recognition."""
    logging.debug("Attempting to click 'Copy text' button via image recognition")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "copy_text_image.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Copy text button image missing at {image_path}")

        timeout = 15
        confidence = 0.9
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=True)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate 'Copy text' button image")
        logging.info(f"Found 'Copy text' button at {button_location}")
        pyautogui.moveTo(button_location, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Copy text button click failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def click_text_here_asterisk():
    """Click the 'text_here_*' target area using image recognition."""
    logging.debug("Attempting to click 'text_here_*' area via image recognition")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "text_here_asterisk.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Text target image missing at {image_path}")

        timeout = 15
        confidence = 0.7
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=True)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate 'text_here_*' target image")
        logging.info(f"Found text target area at {button_location}")
        pyautogui.moveTo(button_location, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Text target click failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def get_latest_narration_file():
    """Finds the most recent narration file in the data/narration directory."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        narration_dir = os.path.join(project_root, "data", "narration")
        files = [f for f in os.listdir(narration_dir) if f.startswith("final_narration") and f.endswith(".json")]
        if not files:
            raise FileNotFoundError("No narration files found")
        files.sort(key=lambda x: os.path.getmtime(os.path.join(narration_dir, x)), reverse=True)
        return os.path.join(narration_dir, files[0])
    except Exception as e:
        logging.error(f"Error finding narration file: {str(e)}")
        logging.error(traceback.format_exc())
        return None

def paste_narration_text():
    """Pastes the narration content into the focused text field."""
    try:
        file_path = get_latest_narration_file()
        if not file_path:
            raise FileNotFoundError("No valid narration file found")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        text_to_paste = json.dumps(content['sections'], indent=2)
        text_to_paste = re.sub(r'[^\x00-\x7F]+', '', text_to_paste)
        pyperclip.copy(text_to_paste)
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        if not pyperclip.paste().startswith(text_to_paste[:100]):
            logging.warning("Clipboard paste failed, using direct typing")
            send_keys(text_to_paste, pause=0)
        return True
    except Exception as e:
        logging.error(f"Paste failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def click_insert_prompt_button():
    """Click the insert prompt button using pyautogui image recognition."""
    logging.debug("Attempting to click insert prompt button via image recognition")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "insert_prompt_image.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Insert prompt image missing at {image_path}")
        timeout = 15
        confidence = 0.9
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=True)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate insert prompt button image")
        logging.info(f"Found insert prompt button at {button_location}")
        pyautogui.moveTo(button_location, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(2)
        return True
    except Exception as e:
        logging.error(f"Insert prompt button click failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def wait_for_play_button():
    """Wait until the play button becomes visible."""
    logging.debug("Starting play button wait")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        play_image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "play_button.png")
        if not os.path.exists(play_image_path):
            raise FileNotFoundError(f"Play button image missing at {play_image_path}")
        timeout = 300  # 5 minutes
        confidence = 0.6
        start_time = time.time()
        logging.info("Waiting for play button to appear...")
        while time.time() - start_time < timeout:
            play_location = pyautogui.locateCenterOnScreen(play_image_path, confidence=confidence, grayscale=True)
            if play_location:
                logging.info("Play button detected - processing complete")
                return True
            time.sleep(10)
        logging.error("Play button not found within 5 minutes")
        return False
    except Exception as e:
        logging.error(f"Play button wait failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def click_three_dots_menu(check_only=False):
    """Click the three dots menu using image recognition with indefinite waiting."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(os.path.dirname(current_dir), "data", "pyautogui_image_files", "three_dots_image.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Three dots image missing at {image_path}")
        confidence = 0.7
        grayscale = True
        attempt_count = 0
        logging.info("Starting three dots detection (indefinite mode)")
        while True:
            try:
                attempt_count += 1
                button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=grayscale)
                if button_location:
                    logging.info(f"Found three dots at {button_location} (attempt {attempt_count})")
                    if check_only:
                        return True
                    pyautogui.moveTo(button_location.x, button_location.y, duration=0.8)
                    time.sleep(0.3)
                    pyautogui.click()
                    time.sleep(1)
                    return True
                wait_time = min(attempt_count * 0.3, 5)
                time.sleep(wait_time)
            except Exception as e:
                logging.warning(f"Detection attempt {attempt_count} failed: {str(e)}")
                time.sleep(2)
    except Exception as e:
        logging.error(f"Three dots menu fatal error: {str(e)}")
        logging.error(traceback.format_exc())
        return False

def click_download_button():
    """
    Wait one second after the three dots are clicked, then search for the download image
    and click its center.
    """
    logging.debug("Attempting to click 'Download' button via image recognition")
    try:
        absolute_path = r"M:\ReactProjects\AutoNews\auto-news-channel\src\data\pyautogui_image_files\download_image.png"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        relative_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "download_image.png")
        potential_paths = [absolute_path, relative_path]
        image_path = None
        for path in potential_paths:
            logging.debug(f"Checking for download image at: {path}")
            if os.path.exists(path):
                image_path = path
                logging.info(f"Found download image at: {path}")
                break
        if not image_path:
            raise FileNotFoundError(f"Download image not found. Checked paths: {potential_paths}")
        time.sleep(1)
        timeout = 15
        confidence = 0.8
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=True)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate the 'Download' button image on screen")
        logging.info(f"Found download button at {button_location}")
        pyautogui.moveTo(button_location, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Download button click failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

#########################
# Chrome-specific download configuration function
#########################

def configure_chrome_download_settings(app):
    """
    For the Chrome branch, this function:
      1. Waits 2 seconds after launch.
      2. Navigates to 'chrome://settings/downloads'.
      3. Waits 1 second for the settings page to load.
      4. Searches for and clicks the 'Change Download Location' image using multiple confidence thresholds.
      5. Waits 2 seconds for the file dialog to appear.
      6. Uses send_keys to press Alt+D, types the new folder path, and presses Enter.
      7. Waits 0.5 seconds, then searches for and clicks the 'select_folder.png' image.
    """
    try:
        time.sleep(2)  # Allow Chrome to open
        chrome_window = app.top_window()
        chrome_window.set_focus()
        time.sleep(0.5)
        send_keys("%d", pause=0)  # Alt+D to focus the address bar
        send_keys("chrome://settings/downloads{ENTER}", pause=0)
        logging.info("Navigated to chrome://settings/downloads")
        time.sleep(1)
        
        # Search for "Change Download Location" button
        change_image_path = r"M:\ReactProjects\AutoNews\auto-news-channel\src\data\pyautogui_image_files\change_download_location_image.png"
        if not os.path.exists(change_image_path):
            raise FileNotFoundError(f"Change location image not found at: {change_image_path}")
        
        thresholds = [0.9, 0.85, 0.8, 0.75, 0.7, 0.65]  # Extended to lower threshold 0.65
        button_location = None
        start_time = time.time()
        timeout = 10
        while time.time() - start_time < timeout and button_location is None:
            for conf in thresholds:
                try:
                    button_location = pyautogui.locateCenterOnScreen(change_image_path, confidence=conf, grayscale=True)
                except pyautogui.ImageNotFoundException:
                    button_location = None
                if button_location:
                    logging.info(f"Found 'Change Download Location' button at {button_location} with confidence {conf}")
                    break
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate the 'Change Download Location' button image.")
        pyautogui.moveTo(button_location, duration=0.3)
        pyautogui.click()
        
        time.sleep(2)  # Wait for file dialog
        
        # Focus the dialog's address bar and type the new folder path
        send_keys("%d", pause=0)  # Alt+D
        folder_path = r"M:\ReactProjects\AutoNews\auto-news-channel\data\narration\deepdive"
        send_keys(folder_path + "{ENTER}", pause=0)
        logging.info(f"Typed folder path: {folder_path}")
        
        time.sleep(0.5)
        select_image_path = r"M:\ReactProjects\AutoNews\auto-news-channel\src\data\pyautogui_image_files\select_folder.png"
        if not os.path.exists(select_image_path):
            raise FileNotFoundError(f"Select folder image not found at: {select_image_path}")
        start_time = time.time()
        select_button_location = None
        while time.time() - start_time < timeout and select_button_location is None:
            try:
                select_button_location = pyautogui.locateCenterOnScreen(select_image_path, confidence=0.8, grayscale=True)
            except pyautogui.ImageNotFoundException:
                select_button_location = None
            if select_button_location:
                break
            time.sleep(0.3)
        if not select_button_location:
            raise Exception("Could not locate the 'Select Folder' image.")
        logging.info(f"Found 'Select Folder' button at {select_button_location}")
        pyautogui.moveTo(select_button_location, duration=0.3)
        pyautogui.click()
        time.sleep(1)
        
        logging.info("Chrome download settings configured successfully.")
        return True
    except Exception as e:
        logging.error("Chrome download configuration failed: " + str(e))
        logging.error(traceback.format_exc())
        return False

#########################
# Edge-specific download configuration functions
#########################

def navigate_to_download_settings(app):
    """Navigate to the Downloads settings in Edge."""
    logging.debug("Navigating to Edge download settings.")
    try:
        edge_window = app.top_window()
        edge_window.set_focus()
        logging.debug("Focusing address bar using Alt+D.")
        send_keys("%d", pause=0)
        time.sleep(0.1)
        send_keys("edge://settings/downloads{ENTER}", pause=0)
        time.sleep(1)
        return edge_window
    except Exception as e:
        logging.error("Error navigating to settings: " + str(e))
        logging.error(traceback.format_exc())
        return None

def click_change_button():
    """
    Locate and click the 'Change location' button in the Downloads settings using pyautogui.
    """
    logging.debug("Attempting to click the 'Change location' button using pyautogui image recognition.")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "change_download_location_image.png")
        logging.debug(f"Looking for change location button at: {image_path}")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file missing at: {image_path}")
        timeout = 10
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate the 'Change location' button image on screen.")
        logging.info(f"Found 'Change location' button image at {button_location}.")
        pyautogui.moveTo(button_location)
        pyautogui.click(button_location)
        time.sleep(1)
        logging.info("Change dialog activated successfully using pyautogui.")
        return True
    except Exception as e:
        logging.error("Button interaction failed using pyautogui: " + str(e))
        logging.error(traceback.format_exc())
        return False

def set_download_path():
    """Set the download path in the file dialog using relative path construction."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.abspath(os.path.join(current_dir, '../../data/narration/deepdive'))
        os.makedirs(target_path, exist_ok=True)
        logging.debug(f"Attempting to set path to: {target_path}")
        send_keys('%d', pause=0)  # Alt+D
        send_keys(target_path.replace('/', '\\') + "{ENTER}", pause=0)
        time.sleep(0.1)
        send_keys("{ENTER}", pause=0)
        time.sleep(0.3)
        return True
    except Exception as e:
        logging.error("Path entry failed: " + str(e))
        logging.error(traceback.format_exc())
        return False

def click_generate_podcast_button():
    """Click the 'Generate Podcast' button using pyautogui image recognition."""
    logging.debug("Attempting to click 'Generate Podcast' button via image recognition")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_path = os.path.join(parent_dir, "data", "pyautogui_image_files", "generate_podcast_image.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Generate podcast image missing at {image_path}")
        timeout = 20
        confidence = 0.8
        start_time = time.time()
        button_location = None
        while time.time() - start_time < timeout:
            button_location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence, grayscale=True)
            if button_location:
                break
            time.sleep(0.3)
        if not button_location:
            raise Exception("Could not locate 'Generate Podcast' button image")
        logging.info(f"Found generate podcast button at {button_location}")
        pyautogui.moveTo(button_location, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Generate podcast button click failed: {str(e)}")
        logging.error(traceback.format_exc())
        return False

#########################
# Main Process
#########################

def main():
    logging.debug("Starting the automated browser process.")
    print("Select Browser:")
    print("1: Microsoft Edge")
    print("2: Google Chrome")
    browser_choice = input("Enter 1 or 2: ").strip()

    app = None

    if browser_choice == "1":
        logging.info("User selected Microsoft Edge.")
        close_existing_edge()
        app = open_edge()
        if app:
            edge_window = navigate_to_download_settings(app)
            if edge_window:
                if click_change_button():
                    path_result = set_download_path()
                    logging.info(f"Download path set result: {path_result}")
                else:
                    logging.error("Failed to activate change dialog for download settings.")
            else:
                logging.error("Failed to obtain the Edge window after navigation.")
        else:
            logging.error("Microsoft Edge did not start properly.")
    elif browser_choice == "2":
        logging.info("User selected Google Chrome.")
        close_existing_chrome()
        app = open_chrome()
        if not app:
            logging.error("Google Chrome did not start properly.")
            return
        # Configure Chrome download settings before continuing
        if not configure_chrome_download_settings(app):
            logging.error("Failed to configure Chrome download settings.")
            return
    else:
        logging.error("Invalid selection. Exiting.")
        return

    if app:
        notebook_url = "https://notebooklm.google.com/"
        if navigate_to_notebook(app, notebook_url):
            time.sleep(3)
            click_create_new_button()
            time.sleep(1.5)
            click_copy_text_button()
            time.sleep(1)
            click_text_here_asterisk()
            time.sleep(2)
            paste_narration_text()
            time.sleep(1)
            click_insert_prompt_button()
            time.sleep(2)
            click_generate_podcast_button()
            time.sleep(3)
            if wait_for_play_button():
                time.sleep(10)
                app.top_window().set_focus()
                time.sleep(1)
                if click_three_dots_menu():
                    logging.info("Successfully opened context menu")
                    if click_download_button():
                        logging.info("Download button clicked successfully")
                    else:
                        logging.error("Failed to click download button")
                else:
                    logging.error("Failed to open context menu")
        else:
            logging.error("Failed to navigate to the Notebook URL.")

if __name__ == '__main__':
    main()
