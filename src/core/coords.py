#!/usr/bin/env python3
"""
Smart Click Coordinate Detector with advanced features
Usage: python click_coords.py [--help] [--mode MODE] [--hotkey]
"""

import sys
import pyautogui
import argparse
from pynput import mouse, keyboard
from datetime import datetime
import pyperclip
from collections import deque
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import threading
import os
import time

class SmartCoordTracker:
    def __init__(self, args):
        self.args = args
        if not hasattr(args, 'exit_after'):
            self.args.exit_after = False
        if not hasattr(args, 'timestamp'):
            self.args.timestamp = False
        if not hasattr(args, 'overlay'):
            self.args.overlay = True
        self.history = deque(maxlen=10)  # Track last 10 clicks
        self.listener = None
        self.kb_listener = None
        self.hotkey_active = False
        self.persistent_targets = []
        self.detection_active = False  # Add shutdown flag
        
        # Set up output formats
        self.formats = {
            'simple': lambda x, y: f"X: {x:<4}  Y: {y}",
            'hex': lambda x, y: f"0x{x:04X}:0x{y:04X}",
            'css': lambda x, y: f"{x}px {y}px",
            'tuple': lambda x, y: f"({x}, {y})"
        }
        
        # Process manual targets provided via command-line
        if args.target:
            for target in args.target:
                try:
                    x, y = map(int, target.split(','))
                    self.persistent_targets.append((x, y))
                except Exception as e:
                    print(f"Invalid target format '{target}'. Use X,Y format.")
                    
        if args.image:
            self.detection_image = args.image
            self.detection_active = True
            threading.Thread(target=self.detect_image_loop, daemon=True).start()
        else:
            self.detection_image = None
        
    def get_rgb(self, x, y):
        """Get pixel color at coordinates"""
        try:
            # Taking a full screenshot might be heavy but works for most cases.
            return pyautogui.screenshot().getpixel((x, y))
        except Exception:
            return (0, 0, 0)

    def show_help(self):
        """Display help information"""
        print("\nSmart Click Modes:")
        print("  C: Toggle coordinate display format")
        print("  R: Toggle RGB color display")
        print("  S: Save current position to history")
        print("  H: Show this help")
        print("  Q: Quit\n")

    def on_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        try:
            if pressed and not self.hotkey_active:
                self.process_coords(x, y)
                return not self.args.exit_after
        except Exception as e:
            print(f"⚠️ Click handling error: {str(e)}")
            return True  # Keep listener alive
        return True  # Default return

    def on_hotkey(self):
        """Handle hotkey press for current mouse position"""
        x, y = pyautogui.position()
        self.hotkey_active = True
        self.process_coords(x, y)
        self.hotkey_active = False

    def create_overlay_window(self, x, y, persistent=False, label=None, color='red'):
        """
        Modified overlay creator with customizable labels and colors
        """
        def run_overlay():
            win = tk.Tk()
            win.attributes('-alpha', 0.7)
            win.attributes('-topmost', True)
            win.overrideredirect(True)
            win.attributes('-transparentcolor', 'white')
            win.geometry(f"100x100+{x-50}+{y-50}")
            
            canvas = tk.Canvas(win, bg='white', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # Customizable elements
            canvas.create_oval(10, 10, 90, 90, outline=color, width=2)
            canvas.create_line(50, 20, 50, 80, fill=color, width=2)
            canvas.create_line(20, 50, 80, 50, fill=color, width=2)
            
            display_text = label if label else f"{x},{y}"
            canvas.create_text(50, 95, text=display_text,
                              fill=color, anchor=tk.N, font=('Arial', 8))
            
            if not persistent:
                win.after(2000, win.destroy)
            win.mainloop()
        
        threading.Thread(target=run_overlay, daemon=True).start()

    def detect_image_loop(self):
        """Continuously detect specified image and mark its location"""
        while self.detection_active:
            try:
                location = pyautogui.locateCenterOnScreen(self.detection_image, confidence=0.8)
                if location:
                    self.create_overlay_window(
                        location.x, 
                        location.y,
                        persistent=True,
                        color='#00FF00',  # Bright green
                        label='THREE DOTS'
                    )
            except Exception as e:
                print(f"Image detection error: {e}")
            time.sleep(1)

    def process_coords(self, x, y):
        """Process and display coordinates with optional features"""
        x, y = int(x), int(y)
        output = []
        
        # Format coordinates based on selected mode
        output.append(self.formats[self.args.mode](x, y))
        
        # Append RGB information if requested
        if self.args.rgb:
            r, g, b = self.get_rgb(x, y)
            output.append(f"RGB: ({r:03}, {g:03}, {b:03})")
            
        # Append timestamp if requested
        if self.args.timestamp:
            output.append(f"TS: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
        # Build final output string
        final_output = " | ".join(output)
        
        # Copy output to clipboard if enabled
        if self.args.clip:
            pyperclip.copy(final_output)
            
        # Print result unless in quiet mode
        if not self.args.quiet:
            print(final_output)
            
        # Store in history
        self.history.append((x, y))
        
        # Display overlay if enabled
        if self.args.overlay:
            # Use --persist flag to decide whether the overlay is persistent
            self.create_overlay_window(x, y, persistent=self.args.persist)

    def detect_three_dots(self):
        """Background thread to continuously detect the three dots image,
           move the mouse to its center, and click once found."""
        try:
            # Set the image_path directly to the provided location
            image_path = r"M:\ReactProjects\AutoNews\auto-news-channel\src\data\pyautogui_image_files\three_dots_image.png"
            
            print(f"🔍 Three dots detection active using image: {image_path}")
            self.detection_active = True
            
            # Loop continuously as long as detection is active
            while self.detection_active:
                try:
                    # Check frequently with a short delay to avoid high CPU usage
                    for _ in range(10):  # 10 iterations * 0.1s = 1 second total
                        if not self.detection_active:
                            return
                        time.sleep(0.1)
                    
                    # Search for the image on screen
                    location = pyautogui.locateCenterOnScreen(image_path, confidence=0.7)
                    if location and self.detection_active:
                        # Provide visual feedback using overlay (optional)
                        self.create_overlay_window(
                            location.x,
                            location.y,
                            persistent=True,
                            color='#00FF00',
                            label='THREE DOTS'
                        )
                        
                        # Move the mouse to the detected location and click
                        print(f"✅ Three dots found at ({location.x}, {location.y}). Moving and clicking...")
                        pyautogui.moveTo(location.x, location.y, duration=0.5)
                        pyautogui.click()
                        
                        # Optional: add a cooldown to prevent multiple rapid clicks.
                        time.sleep(3)
                        
                except Exception as e:
                    if self.detection_active:  # Only log errors if detection is still enabled
                        print(f"Three dots scan error: {str(e)}")
        
        except Exception as e:
            print(f"Three dots detection failed: {str(e)}")
        finally:
            self.detection_active = False

    def test_three_dots_location(self):
        """Test sequence to find and mark three dots image location"""
        try:
            print("🔍 Starting three dots image search (60s max)...")
            image_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "pyautogui_image_files",
                "three_dots_image.png"
            )
            
            start_time = time.time()
            found = False
            
            while time.time() - start_time < 60:
                location = pyautogui.locateCenterOnScreen(image_path, confidence=0.7)
                if location:
                    x, y = location
                    print(f"✅ Found three dots at {x},{y}")
                    
                    # Visual feedback
                    pyautogui.moveTo(x, y, duration=0.5)
                    pyautogui.click()
                    
                    # Save coordinates
                    self.history.append((x, y))
                    
                    # Create persistent overlay
                    self.create_overlay_window(
                        x, y,
                        persistent=True,
                        color='#FF00FF',  # Purple marker
                        label="TEST CLICK"
                    )
                    found = True
                    break
                    
                time.sleep(1)
                
            if not found:
                print("❌ Three dots not found within 60 seconds")
                return False
                
            return True
            
        except Exception as e:
            print(f"🔥 Test failed: {str(e)}")
            return False

    def start(self):
        """Start tracking session with three dots detection"""
        try:
            print("🌟 Smart Coordinate Tracker Activated")
            
            # Run three dots test first if requested
            if self.args.test_three_dots:
                self.test_three_dots_location()
            
            # Show persistent targets
            for x, y in self.persistent_targets:
                self.create_overlay_window(x, y, persistent=True)
                print(f"🎯 Persistent target at ({x}, {y})")
            
            # Start the three dots detection thread if no image flag was provided
            if not self.args.image:
                threading.Thread(target=self.detect_three_dots, daemon=True).start()
            
            # Keyboard listener
            self.kb_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+p': self.on_hotkey,
                '<ctrl>+<alt>+q': self.stop,
                'c': self.toggle_mode,
                'r': lambda: setattr(self.args, 'rgb', not self.args.rgb),
                'h': self.show_help
            })
            self.kb_listener.daemon = True
            self.kb_listener.start()
            
            # Mouse listener
            with mouse.Listener(on_click=self.on_click) as self.listener:
                self.listener.join()
            
        except KeyboardInterrupt:
            self.stop()

    def toggle_mode(self):
        """Cycle through display formats"""
        modes = list(self.formats.keys())
        current_idx = modes.index(self.args.mode)
        new_mode = modes[(current_idx + 1) % len(modes)]
        self.args.mode = new_mode
        if not self.args.quiet:
            print(f"Switched to {new_mode} mode")

    def stop(self, *args):
        """Stop all listeners and exit the program"""
        try:
            print("\n🛑 Shutting down...")
            self.detection_active = False  # Signal thread to stop
            
            # Extended wait for thread cleanup
            time.sleep(1.0)  # Increased from 0.5s
            
            # Stop listeners first
            if self.listener:
                self.listener.stop()
            if self.kb_listener:
                self.kb_listener.stop()
            
            # Print final positions
            print("📌 Final positions:")
            for idx, (x, y) in enumerate(self.history, 1):
                print(f"{idx:2}: {self.formats[self.args.mode](x, y)}")
            
            # Force exit
            os._exit(0)
            
        except Exception as e:
            print(f"❌ Emergency shutdown: {str(e)}")
            os._exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="📌 Smart Click Coordinates - Visual Position Detector",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""\
Common Use Cases:
  Basic click tracking:   python click_coords.py
  Set persistent target:  python click_coords.py -T 749,665
  Web design alignment:   python click_coords.py -T 100,200 -T 300,400 --css
  Color sampling:         python click_coords.py --rgb --clip
  Programming use:        python click_coords.py --hex --quiet

Interactive Controls:
  Left Click         - Capture coordinates
  Ctrl+Alt+P         - Get current mouse position
  C                  - Cycle display formats
  R                  - Toggle RGB color display
  S                  - Save current position to history
  Ctrl+Alt+Q         - Quit program
"""
    )
    parser.add_argument("-m", "--mode", choices=["simple", "hex", "css", "tuple"],
                        default="simple", help="Display format (default: simple)")
    parser.add_argument("-T", "--target", action="append",
                        help="Set persistent target at X,Y coordinates (can use multiple)")
    parser.add_argument("-P", "--persist", action="store_true",
                        help="Keep overlays until exit (default: temporary)")
    parser.add_argument("-r", "--rgb", action="store_true",
                        help="Show RGB color at position")
    parser.add_argument("-c", "--clip", action="store_true",
                        help="Auto-copy output to clipboard")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Minimal console output")
    parser.add_argument("-o", "--overlay", action="store_true",
                        help="Show visual click overlays", default=True)
    parser.add_argument("--timestamp", action="store_true",
                        help="Include timestamp in the output")
    parser.add_argument("-e", "--exit-after", action="store_true",
                        help="Exit after first click")
    parser.add_argument("-i", "--image", help="Path to image file to continuously detect and mark")
    parser.add_argument("--test-three-dots", action="store_true",
                        help="Run three dots image detection test")

    try:
        args = parser.parse_args()
        tracker = SmartCoordTracker(args)
        tracker.start()
        
    except KeyboardInterrupt:
        print("\n🚫 Operation cancelled")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if "pynput" in str(e):
            print("💡 Install requirements: pip install pynput pyautogui pyperclip Pillow")
