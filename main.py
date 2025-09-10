import platform
import sys
import os
import time
import threading
import tempfile
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QTextEdit, QFrame, QCheckBox, QGraphicsDropShadowEffect,
    QSlider, QSpacerItem, QSizePolicy, QScrollArea, QMessageBox, QProgressDialog
)
from PyQt5.QtGui import QFont, QIcon, QColor, QFontDatabase, QPixmap
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, QThread
import glob
import shutil
import re
import subprocess
from datetime import datetime
from pathlib import Path
from pydub import AudioSegment


# Import Groq client for script generation
from groq import Groq

# Import our audio processor module
from audio_processor import AudioProcessor

# Import required modules from automation script
import random
import shutil
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import pytesseract


class ElegantComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setFont(QFont("Montserrat", 11))
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
    def showPopup(self):
        super().showPopup()
        popup = self.findChild(QFrame)
        if popup:
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(20)
            effect.setColor(QColor(0, 0, 0, 70))
            effect.setOffset(0, 5)
            popup.setGraphicsEffect(effect)


class PremiumButton(QPushButton):
    def __init__(self, text, parent=None, accent=False):
        super().__init__(text, parent)
        self.setFixedHeight(50)
        self.setFont(QFont("Montserrat", 11, QFont.DemiBold))
        
        self.accent = accent
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.setStyleSheet(self._get_style())
        
    def _get_style(self):
        if self.accent:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4568dc, stop:1 #b06ab3);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #5678ec, stop:1 #c07ac3);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3458cc, stop:1 #a05aa3);
                }
            """
        else:
            return """
                QPushButton {
                    background-color: rgba(255, 255, 255, 40);
                    color: #333333;
                    border: 1px solid rgba(0, 0, 0, 10);
                    border-radius: 6px;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 60);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 5);
                }
            """
            
    def enterEvent(self, event):
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.width() + 10)
        self.animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.width() - 10)
        self.animation.start()
        super().leaveEvent(event)
        
    def update_theme(self, is_dark):
        if not self.accent:
            if is_dark:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 10);
                        color: #e0e0e0;
                        border: 1px solid rgba(255, 255, 255, 15);
                        border-radius: 6px;
                        padding: 12px 24px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 15);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 255, 255, 5);
                    }
                """)
            else:
                self.setStyleSheet(self._get_style())


class AutomationWorker(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, script_text):
        super().__init__()
        self.script_text = script_text
        self.downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        self.audio_processor = None
        self.processed_file = None
    
    def run(self):
        try:
            self.update_signal.emit("Starting automation process...")
            
            # Create audio processor
            self.audio_processor = AudioProcessor(input_dir=self.downloads_folder)
            output_dir = self.audio_processor.output_dir
            self.update_signal.emit(f"Audio will be saved to: {output_dir}")
            
            # Try to close any running Chrome processes
            self.close_chrome_processes()
            
            # Replace the existing chrome_options setup with:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--enable-gpu-rasterization")
            chrome_options.add_argument("--force-gpu-mem-available-mb=4096")
            # chrome_options.add_argument("--single-process")  # Add this for resource constraints

            # Add these experimental options to handle latency
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_experimental_option("detach", True)
            
            # Set default download directory
            prefs = {"download.default_directory": self.downloads_folder}
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.update_signal.emit("Starting Chrome browser...")
            
            # Initialize Chrome driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.update_signal.emit("Opening speechma.com...")
            driver.get("https://speechma.com/")
            
            # Wait for the page to load fully
            time.sleep(5)
            
            # Find the search bar for voices
            self.update_signal.emit("Looking for voice search bar...")
            wait = WebDriverWait(driver, 15)
            
            # Look for search elements
            search_elements = driver.find_elements(By.XPATH, "//input[@type='search' or contains(@placeholder, 'search') or contains(@placeholder, 'Search') or contains(@class, 'search')]")
            
            # If no search elements found, try looking for any input field
            if not search_elements:
                search_elements = driver.find_elements(By.TAG_NAME, "input")
            
            # Use the first visible search element
            search_bar = None
            for element in search_elements:
                if element.is_displayed():
                    search_bar = element
                    break
                    
            if search_bar:
                # Search for the "Emily" voice
                self.update_signal.emit("Found search bar. Searching for 'Emily' voice...")
                driver.execute_script("arguments[0].scrollIntoView(true);", search_bar)
                time.sleep(1)
                search_bar.clear()
                search_bar.send_keys("Emily")
                search_bar.send_keys(Keys.RETURN)
                
                # Wait for search results
                self.update_signal.emit("Waiting for search results...")
                time.sleep(3)
                
                # Find elements that contain "Emily" text
                self.update_signal.emit("Looking for Emily voice option...")
                
                # Try various strategies to find and click on the Emily voice
                emily_found = False
                
                # Strategy 1: Find elements containing Emily text
                emily_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Emily')]")
                for element in emily_elements:
                    if element.is_displayed():
                        self.update_signal.emit("Found element with Emily text. Attempting to click...")
                        
                        try:
                            # Try to get various parent elements
                            parent = driver.execute_script("return arguments[0].parentNode;", element)
                            grand_parent = driver.execute_script("return arguments[0].parentNode;", parent)
                            
                            # Try clicking parent elements
                            clickable_elements = [parent, grand_parent]
                            
                            for clickable in clickable_elements:
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView(true);", clickable)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", clickable)
                                    self.update_signal.emit("Clicked on Emily voice!")
                                    emily_found = True
                                    break
                                except Exception:
                                    continue
                                    
                            if emily_found:
                                break
                                
                        except Exception as e:
                            self.update_signal.emit(f"Error clicking on Emily: {e}")
                            continue
                
                # If Emily not found, try alternative strategy
                if not emily_found:
                    self.update_signal.emit("Trying alternative strategy for finding Emily voice...")
                    
                    # Strategy 2: Try to find voice cards/containers
                    card_selectors = [
                        "//div[contains(@class, 'card') and .//text()[contains(., 'Emily')]]",
                        "//div[contains(@class, 'voice') and .//text()[contains(., 'Emily')]]",
                        "//div[contains(@class, 'item') and .//text()[contains(., 'Emily')]]",
                        "//li[.//text()[contains(., 'Emily')]]"
                    ]
                    
                    for selector in card_selectors:
                        cards = driver.find_elements(By.XPATH, selector)
                        if cards:
                            for card in cards:
                                if card.is_displayed():
                                    self.update_signal.emit("Found voice card/container. Clicking...")
                                    driver.execute_script("arguments[0].scrollIntoView(true);", card)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", card)
                                    emily_found = True
                                    break
                            if emily_found:
                                break
                
                # Wait for the voice selection to be applied
                time.sleep(3)
                
                # Find the text input area - look for textarea or contenteditable elements
                self.update_signal.emit("Looking for text input area...")
                input_elements = driver.find_elements(By.XPATH, "//textarea | //div[@contenteditable='true'] | //input[@type='text']")
                
                text_area = None
                for element in input_elements:
                    if element.is_displayed():
                        text_area = element
                        break
                
                if text_area:
                    self.update_signal.emit("Found text input area. Pasting script...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", text_area)
                    time.sleep(1)
                    text_area.clear()
                    text_area.send_keys(self.script_text)
                    self.update_signal.emit("Script has been entered.")
                else:
                    self.update_signal.emit("Couldn't find the text input area. Please paste the script manually.")
                    time.sleep(15)  # Give user time to manually paste

                # Try to handle CAPTCHA
                self.update_signal.emit("Looking for CAPTCHA...")
                try:
                    # Locate the captcha image
                    captcha_img = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "captchaImg"))
                    )

                    # Save screenshot of the CAPTCHA image
                    captcha_img_path = "captcha.png"
                    captcha_img.screenshot(captcha_img_path)

                    # Use OCR to read the text from the image
                    captcha_text = pytesseract.image_to_string(Image.open(captcha_img_path), config='--psm 7').strip()
                    captcha_text = ''.join(filter(str.isdigit, captcha_text))  # Keep only digits

                    self.update_signal.emit(f"OCR detected CAPTCHA: {captcha_text}")

                    if len(captcha_text) == 5:
                        # Enter the CAPTCHA into the input field
                        captcha_input = driver.find_element(By.ID, "captchaInput")
                        captcha_input.clear()
                        captcha_input.send_keys(captcha_text)
                        time.sleep(1)
                        self.update_signal.emit("CAPTCHA entered automatically")
                    else:
                        self.update_signal.emit("CAPTCHA detection failed. You may need to enter it manually.")
                        time.sleep(15)  # Give user time to manually enter CAPTCHA
                except Exception as e:
                    self.update_signal.emit(f"CAPTCHA handling: {e}")
                    self.update_signal.emit("You may need to handle the CAPTCHA manually")
                    time.sleep(15)  # Give user time to manually handle CAPTCHA

                # Click the "Generate Audio" button
                self.update_signal.emit("Looking for the Generate Audio button...")
                try:
                    generate_button = wait.until(EC.element_to_be_clickable((By.ID, "convertButton")))
                    driver.execute_script("arguments[0].scrollIntoView(true);", generate_button)
                    generate_button.click()
                    self.update_signal.emit("Clicked Generate Audio button.")
                except Exception as e:
                    self.update_signal.emit(f"Could not find Generate Audio button: {e}")
                    self.update_signal.emit("Please click the Generate Audio button manually.")
                    time.sleep(10)  # Give user time to click manually

                self.update_signal.emit("Waiting for audio generation and Download button...")
                
                # Start file monitoring 10 seconds BEFORE clicking the download button
                self.update_signal.emit("Starting to monitor for new files in downloads folder...")
                
                # Get the initial list of files in the downloads folder
                initial_files = set(os.listdir(self.downloads_folder))
                
                # Create a file monitoring thread
                file_monitor_thread = threading.Thread(
                    target=self.monitor_downloads_folder,
                    args=(initial_files,)
                )
                file_monitor_thread.daemon = True
                file_monitor_thread.start()
                
                # Wait for the download button to appear
                try:
                    download_button = WebDriverWait(driver, 60).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'download-btn')]"))
                    )

                    # Click the Download button
                    self.update_signal.emit("Clicking the Download button...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", download_button)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", download_button)
                    
                    self.update_signal.emit("Download initiated!")
                except Exception as e:
                    self.update_signal.emit(f"Could not find Download button: {e}")
                    self.update_signal.emit("Please click the Download button manually when ready.")
                    time.sleep(15)  # Give user time to download manually
                
                # Wait for the file monitor thread to complete
                file_monitor_thread.join(60)  # Wait up to 60 seconds
                
                # Close browser
                self.update_signal.emit("Closing browser...")
                driver.quit()
                
                if self.processed_file:
                    self.finished_signal.emit(self.processed_file)
                else:
                    self.update_signal.emit("No audio file was processed. Check the downloads folder manually.")
                    self.finished_signal.emit("")
            else:
                self.update_signal.emit("Couldn't find search bar. Please navigate manually.")
                driver.quit()
                self.error_signal.emit("Failed to find search bar")
                
        except Exception as e:
            self.error_signal.emit(f"Automation error: {e}")
    
    def monitor_downloads_folder(self, initial_files):
        """
        Monitor the downloads folder for new files and process them when found.
        This runs in a separate thread.
        """
        self.processed_file = None
        max_wait = 120  # Maximum wait time in seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Get current files in downloads folder
                current_files = set(os.listdir(self.downloads_folder))
                
                # Check for new files
                new_files = current_files - initial_files
                
                if new_files:
                    self.update_signal.emit(f"New files detected: {', '.join(new_files)}")
                    
                    # Try to process the new files
                    for file_name in new_files:
                        file_path = os.path.join(self.downloads_folder, file_name)
                        
                        # Check if file is still being written to (download not complete)
                        try:
                            size1 = os.path.getsize(file_path)
                            time.sleep(1)  # Wait a bit
                            size2 = os.path.getsize(file_path)
                            
                            # If file size hasn't changed, it's probably complete
                            if size1 == size2:
                                self.update_signal.emit(f"File download complete: {file_name}")
                                try:
                                    # Updated to handle the tuple return value from the AudioProcessor
                                    processed_result = self.audio_processor.process_file(file_path)
                                    
                                    # Check if we got a tuple returned
                                    if isinstance(processed_result, tuple):
                                        wav_path, inference_success = processed_result
                                        self.processed_file = wav_path
                                        if wav_path:
                                            self.update_signal.emit(f"Audio processed successfully: {wav_path}")
                                            if inference_success:
                                                self.update_signal.emit("Inference completed successfully!")
                                            else:
                                                self.update_signal.emit("Note: Inference did not run or was not successful.")
                                            return  # Exit the monitoring loop once a file is processed
                                    else:
                                        # Handle case where it might return the old-style single value
                                        self.processed_file = processed_result
                                        if self.processed_file:
                                            self.update_signal.emit(f"Audio processed successfully: {self.processed_file}")
                                            return  # Exit the monitoring loop once a file is processed
                                except Exception as e:
                                    self.update_signal.emit(f"Error processing audio file {file_name}: {e}")
                        except Exception as e:
                            self.update_signal.emit(f"Error checking file size for {file_name}: {e}")
                            
                # Update initial files to current files to only catch newer files
                initial_files = current_files
                
                # Sleep before checking again
                time.sleep(2)
                
            except Exception as e:
                self.update_signal.emit(f"Error monitoring downloads folder: {e}")
                time.sleep(2)
        
        self.update_signal.emit("File monitoring timed out. No suitable file was found for processing.")
    
    def close_chrome_processes(self):
        """Attempt to close any running Chrome processes"""
        self.update_signal.emit("Closing any existing Chrome processes...")
        try:
            if os.name == 'nt':  # Windows
                subprocess.call('taskkill /f /im chrome.exe', shell=True)
            else:  # Linux/Mac
                subprocess.call('pkill -f chrome', shell=True)
            time.sleep(2)  # Give it time to close
        except Exception as e:
            self.update_signal.emit(f"Note: Couldn't close Chrome processes: {e}")

class ScriptGenerationWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, main_topic, subtopic, tone, length):
        super().__init__()
        self.main_topic = main_topic
        self.subtopic = subtopic
        self.tone = tone
        self.length = length
    
    def run(self):
        try:
            # Use API key from environment variables
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                self.error_signal.emit("GROQ_API_KEY not found in environment variables")
                return
            
            client = Groq(api_key=api_key)
            
            # System prompt to generate a short script (approximately 125-150 words)
            system_prompt = f"""You are a professional script writer for Instagram content creators.
            
    Create a concise, engaging 25-second script (keep the script SHORT)  
    for an Instagram video about the topic: {self.main_topic} - {self.subtopic}.
    
    The script should:
    - Start with a BOLD HOOK.
    - Be appropriate for spoken delivery on Instagram by a female creator
    - Have a clear beginning, middle, and end
    - Use natural conversational language with "bestie talk" style
    - Include pauses, emphasis, and relatable examples
    - Be informative yet engaging for social media audience
    - Include a catchy hook in the first 3 seconds
    - End with a question or call to action to encourage engagement
    - Be in a {self.tone} tone
    - Be {self.length} in detail
    
    DO NOT include any stage directions, timings, or formatting notes.
    Write ONLY the script text that would be spoken aloud on Instagram.
    DO NOT include any headings either, only the script.
            """
            
            # Make API call to Groq
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Write a 35-second Instagram script about: {self.main_topic} - {self.subtopic}"}
                ],
                temperature=0.7,
                max_tokens=300,
                top_p=1,
                stream=False
            )
            
            # Extract the generated script
            script_content = completion.choices[0].message.content
            
            # Add header and hashtags
            formatted_script = f"""{script_content}"""
            
            self.finished_signal.emit(formatted_script)
            
        except Exception as e:
            error_msg = f"Error generating script: {str(e)}"
            self.error_signal.emit(error_msg)
            
            # Create fallback script if API fails
            fallback_script = f"""✨ *INSTAGRAM SCRIPT* ✨

Topic: {self.subtopic} ({self.main_topic})
Style: {self.tone.capitalize()}, {self.length.capitalize()}

[INTRO]
Hey there beautiful souls! Today I want to talk to you about {self.subtopic} in the realm of {self.main_topic}.

[HOOK]
Did you know that mastering this could be the difference between feeling stuck and experiencing true freedom? That's right.

[MAIN CONTENT]
The secret most people miss about {self.subtopic} is that it's not about perfection — it's about consistency and intention.

When I first embraced this practice, I noticed three immediate shifts:
• My mindset became clearer
• My relationships improved
• My daily energy doubled

[CALL TO ACTION]
Drop a '✨' in the comments if you're ready to transform your approach to {self.subtopic} and join our community of mindful creators.

[OUTRO]
Remember, you deserve to experience this level of clarity and purpose. Save this post for when you need a reminder.

 #AgenticAI #ContentCreator #Transformation"""
            
            self.finished_signal.emit(fallback_script)


class InstagramContentGeneratorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agentic AI - Instagram Content Generator")
        self.setGeometry(100, 100, 1280, 900)
        self.setWindowIcon(QIcon("logo.png"))
        self.dark_mode = False
        self.audio_processor = AudioProcessor()
        
        # Configure status updates
        # self.audio_processor.set_status_callback(self.update_status_label)
        
        # Load custom fonts - with fallback if not available
        try:
            QFontDatabase.addApplicationFont("./fonts/Montserrat-Regular.ttf")
            QFontDatabase.addApplicationFont("./fonts/Montserrat-Bold.ttf")
            QFontDatabase.addApplicationFont("./fonts/Montserrat-Medium.ttf")
            QFontDatabase.addApplicationFont("./fonts/PlayfairDisplay-Bold.ttf")
        except Exception:
            print("Font files not found. Using system fonts.")
        
        self.topics = {
            "Soft Life Aesthetic + Wellness Advice": [
                "Daily affirmations", "Motivational rants", "Growth tips",
                "Mindfulness practices", "Self-care rituals"
            ],
            "AI + Life Tips": [
                "Productivity hacks", "Digital minimalism", "AI bestie talk",
                "Future tech trends", "AI-powered creativity"
            ],
            "Emotional Intelligence & Healing": [
                "Overthinking", "Toxic relationships", "Healing practices",
                "Authentic living", "Embracing vulnerability", "Setting boundaries"
            ],
            "Controversial but Classy Opinions": [
                "Unpopular opinion on self-discipline", 
                "Controversial takes on modern productivity",
                "Unpopular opinions about social media",
                "Thought-provoking perspectives on digital culture"
            ],
            "AI + Fashion + Digital Aesthetics": [
                "Digital outfits showcase",
                "AI fashion collaborations",
                "Virtual fashion trends",
                "Digital fashion for social media",
                "AI tools in the fashion industry"
            ],
            "Weekly Series Ideas": [
                "Monday Mindset Check",
                "Talk to Me Tuesday (AI answers DMs)",
                "Thursday Therapy",
                "Sunday Reset Rituals",
                "Wellness Wednesday routines"
            ]
        }
        
        self.script_variations = 0
        self.current_variation = 0
        self.variations = []
        
        # Status logs
        self.automation_logs = []
        
        # Initialize the UI
        self.init_ui()
        self.apply_theme()
        
        # Check for Groq API key
        if not os.environ.get("GROQ_API_KEY"):
            self.show_groq_api_dialog()
        
    def show_groq_api_dialog(self):
        """Show dialog to get Groq API key"""
        from PyQt5.QtWidgets import QInputDialog, QLineEdit
        
        api_key, ok = QInputDialog.getText(
            self, 
            "Groq API Key Required", 
            "Please enter your Groq API key:",
            QLineEdit.Password
        )
        
        if ok and api_key:
            os.environ["GROQ_API_KEY"] = api_key
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create top bar with logo and theme toggle
        top_bar = QWidget()
        top_bar.setFixedHeight(80)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(40, 20, 40, 20)
        
        logo_label = QLabel("AGENTIC AI")
        logo_label.setFont(QFont("Montserrat", 16, QFont.Bold))
        
        self.theme_toggle = QCheckBox()
        self.theme_toggle.setText("🌙")
        self.theme_toggle.setFont(QFont("Montserrat", 14))
        self.theme_toggle.stateChanged.connect(self.toggle_theme)
        
        top_bar_layout.addWidget(logo_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.theme_toggle)
        
        main_layout.addWidget(top_bar)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 20, 40, 40)
        content_layout.setSpacing(30)
        
        # Premium header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 60, 0, 40)
        
        title = QLabel("Automated Reels Generation & Instagram Posting")
        title.setFont(QFont("Playfair Display", 36, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("With one click, Our AI Automates the process starting from script generation to Instagram Posting.")
        subtitle.setFont(QFont("Montserrat", 14))
        subtitle.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        # Apply shadow to the header
        header_effect = QGraphicsDropShadowEffect()
        header_effect.setBlurRadius(30)
        header_effect.setColor(QColor(0, 0, 0, 30))
        header_effect.setOffset(0, 2)
        title.setGraphicsEffect(header_effect)
        
        content_layout.addWidget(header_widget)
        
        # Subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        content_layout.addWidget(divider)
        
        # Controls section
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 20, 0, 20)
        controls_layout.setSpacing(20)
        
        # Content Pillar
        content_label = QLabel("Content Pillar")
        content_label.setFont(QFont("Montserrat", 14, QFont.DemiBold))
        
        self.main_combo = ElegantComboBox()
        self.main_combo.addItems(self.topics.keys())
        self.main_combo.currentIndexChanged.connect(self.update_subtopics)
        
        controls_layout.addWidget(content_label)
        controls_layout.addWidget(self.main_combo)
        
        # Subtopic
        subtopic_label = QLabel("Subtopic")
        subtopic_label.setFont(QFont("Montserrat", 14, QFont.DemiBold))
        
        self.sub_combo = ElegantComboBox()
        controls_layout.addWidget(subtopic_label)
        controls_layout.addWidget(self.sub_combo)
        
        # Sliders for customization
        tone_label = QLabel("Tone")
        tone_label.setFont(QFont("Montserrat", 14, QFont.DemiBold))
        
        tone_container = QWidget()
        tone_layout = QHBoxLayout(tone_container)
        tone_layout.setContentsMargins(0, 0, 0, 0)
        
        casual_label = QLabel("Casual")
        casual_label.setFont(QFont("Montserrat", 10))
        
        self.tone_slider = QSlider(Qt.Horizontal)
        self.tone_slider.setRange(0, 100)
        self.tone_slider.setValue(50)
        self.tone_slider.setFixedHeight(30)
        
        formal_label = QLabel("Formal")
        formal_label.setFont(QFont("Montserrat", 10))
        
        tone_layout.addWidget(casual_label)
        tone_layout.addWidget(self.tone_slider)
        tone_layout.addWidget(formal_label)
        
        controls_layout.addWidget(tone_label)
        controls_layout.addWidget(tone_container)
        
# Detail level
        detail_label = QLabel("Detail Level")
        detail_label.setFont(QFont("Montserrat", 14, QFont.DemiBold))
        
        detail_container = QWidget()
        detail_layout = QHBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        
        brief_label = QLabel("Brief")
        brief_label.setFont(QFont("Montserrat", 10))
        
        self.detail_slider = QSlider(Qt.Horizontal)
        self.detail_slider.setRange(0, 100)
        self.detail_slider.setValue(50)
        self.detail_slider.setFixedHeight(30)
        
        detailed_label = QLabel("Detailed")
        detailed_label.setFont(QFont("Montserrat", 10))
        
        detail_layout.addWidget(brief_label)
        detail_layout.addWidget(self.detail_slider)
        detail_layout.addWidget(detailed_label)
        
        controls_layout.addWidget(detail_label)
        controls_layout.addWidget(detail_container)
        
        # Button group
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 20, 0, 0)
        button_layout.setSpacing(20)
        
        self.generate_button = PremiumButton("Generate Script", accent=True)
        self.generate_button.clicked.connect(self.generate_script)
        self.generate_button.setMinimumWidth(200)
        
        self.regenerate_button = PremiumButton("Regenerate")
        self.regenerate_button.clicked.connect(self.regenerate_script)
        self.regenerate_button.setMinimumWidth(150)
        self.regenerate_button.setEnabled(False)
        
        self.prev_variation_button = PremiumButton("Previous")
        self.prev_variation_button.clicked.connect(self.show_previous_variation)
        self.prev_variation_button.setMinimumWidth(120)
        self.prev_variation_button.setEnabled(False)
        
        self.next_variation_button = PremiumButton("Next")
        self.next_variation_button.clicked.connect(self.show_next_variation)
        self.next_variation_button.setMinimumWidth(120)
        self.next_variation_button.setEnabled(False)
        
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.regenerate_button)
        button_layout.addWidget(self.prev_variation_button)
        button_layout.addWidget(self.next_variation_button)
        button_layout.addStretch()
        
        controls_layout.addWidget(button_container)
        content_layout.addWidget(controls_widget)
        
        # Create script display section
        script_group = QWidget()
        script_layout = QVBoxLayout(script_group)
        script_layout.setContentsMargins(0, 0, 0, 0)
        script_layout.setSpacing(15)
        
        script_header = QLabel("Generated Script")
        script_header.setFont(QFont("Montserrat", 14, QFont.DemiBold))
        
        self.script_text = QTextEdit()
        self.script_text.setMinimumHeight(300)
        self.script_text.setFont(QFont("Montserrat", 12))
        self.script_text.setReadOnly(True)
        self.script_text.setPlaceholderText("Your generated script will appear here...")
        
        script_layout.addWidget(script_header)
        script_layout.addWidget(self.script_text)
        
        # Action buttons
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 10, 0, 0)
        
        self.auto_generate_button = PremiumButton("Auto-Generate Audio", accent=True)
        self.auto_generate_button.clicked.connect(self.start_automation)
        self.auto_generate_button.setMinimumWidth(200)
        self.auto_generate_button.setEnabled(False)
        
        self.copy_button = PremiumButton("Copy Script")  
        self.copy_button.clicked.connect(self.copy_script)
        self.copy_button.setMinimumWidth(150)
        self.copy_button.setEnabled(False)
        
        action_layout.addWidget(self.auto_generate_button)
        action_layout.addWidget(self.copy_button)
        action_layout.addStretch()
        
        script_layout.addWidget(action_container)
        content_layout.addWidget(script_group)
        
        # Status Section
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        status_header = QLabel("Automation Status")
        status_header.setFont(QFont("Montserrat", 14, QFont.DemiBold))
        
        self.status_text = QTextEdit()
        self.status_text.setMinimumHeight(150)
        self.status_text.setMaximumHeight(200)
        self.status_text.setFont(QFont("Montserrat", 11))
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("Automation status will appear here...")
        
        status_layout.addWidget(status_header)
        status_layout.addWidget(self.status_text)
        
        # Add Post Video button
        post_video_container = QWidget()
        post_video_layout = QHBoxLayout(post_video_container)
        post_video_layout.setContentsMargins(0, 10, 0, 0)
        
        self.post_video_button = PremiumButton("Post Video", accent=True)
        self.post_video_button.clicked.connect(self.audio_processor.open_video_in_file_manager)
        self.post_video_button.setMinimumWidth(200)
        self.post_video_button.setEnabled(True)
        
        post_video_layout.addWidget(self.post_video_button)
        post_video_layout.addStretch()
        
        status_layout.addWidget(post_video_container)
        
        content_layout.addWidget(status_group)
        
        # Add spacer at the bottom
        content_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
        
        # Initialize subtopics
        self.update_subtopics()
        
        
    # def open_video_in_file_manager(self):
    #     """Opens the newly generated video in the system's file manager"""
    #     if hasattr(self, 'video_path') and self.video_path:
    #         try:
    #             # Use the appropriate command based on the operating system
    #             if platform.system() == 'Windows':
    #                 os.startfile(os.path.dirname(self.video_path))
    #             elif platform.system() == 'Darwin':  # macOS
    #                 subprocess.call(['open', '-R', self.video_path])
    #             else:  # Linux and other Unix
    #                 subprocess.call(['xdg-open', os.path.dirname(self.video_path)])
                
    #             self.update_status("Opened video in file manager: " + self.video_path)
    #         except Exception as e:
    #             self.update_status(f"Error opening file manager: {str(e)}")
    #     else:
    #         self.update_status("No video file available to open.")
    
    def update_subtopics(self):
        """Update subtopics based on main topic selection"""
        self.sub_combo.clear()
        main_topic = self.main_combo.currentText()
        self.sub_combo.addItems(self.topics[main_topic])
    
    def toggle_theme(self, state):
        """Toggle between light and dark themes"""
        self.dark_mode = bool(state)
        self.apply_theme()
        
    def apply_theme(self):
        """Apply the current theme to the application"""
        if self.dark_mode:
            self.theme_toggle.setText("☀️")
            self.setStyleSheet("""
                QWidget {
                    background-color: #121212;
                    color: #e0e0e0;
                }
                QScrollArea {
                    background-color: #121212;
                }
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    border: 1px solid #333333;
                    border-radius: 6px;
                    padding: 10px;
                }
                QComboBox {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    border: 1px solid #333333;
                    border-radius: 6px;
                    padding: 12px;
                }
                QComboBox::drop-down {
                    border: 0px;
                    width: 30px;
                }
                QComboBox::down-arrow {
                    image: url(./icons/down-arrow-light.png);
                    width: 14px;
                    height: 14px;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #333333;
                    height: 10px;
                    background: #1e1e1e;
                    margin: 0px;
                    border-radius: 5px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4568dc, stop:1 #b06ab3);
                    border: none;
                    width: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
                QSlider::sub-page:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4568dc, stop:1 #b06ab3);
                    border-radius: 5px;
                }
                QCheckBox {
                    spacing: 8px;
                }
                QLabel {
                    color: #e0e0e0;
                }
            """)
        else:
            self.theme_toggle.setText("🌙")
            self.setStyleSheet("""
                QWidget {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QScrollArea {
                    background-color: #f5f5f5;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #dddddd;
                    border-radius: 6px;
                    padding: 10px;
                }
                QComboBox {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #dddddd;
                    border-radius: 6px;
                    padding: 12px;
                }
                QComboBox::drop-down {
                    border: 0px;
                    width: 30px;
                }
                QComboBox::down-arrow {
                    image: url(./icons/down-arrow-dark.png);
                    width: 14px;
                    height: 14px;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #dddddd;
                    height: 10px;
                    background: #ffffff;
                    margin: 0px;
                    border-radius: 5px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4568dc, stop:1 #b06ab3);
                    border: none;
                    width: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
                QSlider::sub-page:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4568dc, stop:1 #b06ab3);
                    border-radius: 5px;
                }
                QCheckBox {
                    spacing: 8px;
                }
            """)
            
        # Update button styles for theme
        for button in [self.regenerate_button, self.prev_variation_button, self.next_variation_button, self.copy_button]:
            button.update_theme(self.dark_mode)
    
    def generate_script(self):
        """Generate script using the selected parameters"""
        self.script_text.setText("Generating script...")
        self.generate_button.setEnabled(False)
        self.regenerate_button.setEnabled(False)
        self.auto_generate_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        
        # Get the selected parameters
        main_topic = self.main_combo.currentText()
        subtopic = self.sub_combo.currentText()
        
        # Determine tone based on slider
        tone_value = self.tone_slider.value()
        if tone_value < 33:
            tone = "casual"
        elif tone_value < 66:
            tone = "balanced"
        else:
            tone = "formal"
            
        # Determine detail level based on slider
        detail_value = self.detail_slider.value()
        if detail_value < 33:
            detail = "brief"
        elif detail_value < 66:
            detail = "moderate"
        else:
            detail = "detailed"
        
        # Create worker thread for script generation
        self.script_worker = ScriptGenerationWorker(main_topic, subtopic, tone, detail)
        self.script_worker.finished_signal.connect(self.on_script_generated)
        self.script_worker.error_signal.connect(self.on_script_error)
        self.script_worker.start()
        
    def on_script_generated(self, script):
        """Handle the generated script"""
        # Reset variations
        self.variations = [script]
        self.current_variation = 0
        self.script_variations = 1
        
        # Update UI
        self.script_text.setText(script)
        self.generate_button.setEnabled(True)
        self.regenerate_button.setEnabled(True)
        self.auto_generate_button.setEnabled(True)
        self.copy_button.setEnabled(True)
        self.prev_variation_button.setEnabled(False)
        self.next_variation_button.setEnabled(False)
        
    def on_script_error(self, error):
        """Handle script generation error"""
        self.script_text.setText(f"Error generating script: {error}")
        self.generate_button.setEnabled(True)
        
    def regenerate_script(self):
        """Regenerate the script for variation"""
        self.script_text.setText("Regenerating script...")
        self.regenerate_button.setEnabled(True)
        
        # Get the selected parameters
        main_topic = self.main_combo.currentText()
        subtopic = self.sub_combo.currentText()
        
        # Determine tone based on slider
        tone_value = self.tone_slider.value()
        if tone_value < 33:
            tone = "casual"
        elif tone_value < 66:
            tone = "balanced"
        else:
            tone = "formal"
            
        # Determine detail level based on slider
        detail_value = self.detail_slider.value()
        if detail_value < 33:
            detail = "brief"
        elif detail_value < 66:
            detail = "moderate"
        else:
            detail = "detailed"
        
        # Create worker thread for script regeneration
        self.script_worker = ScriptGenerationWorker(main_topic, subtopic, tone, detail)
        self.script_worker.finished_signal.connect(self.on_script_regenerated)
        self.script_worker.error_signal.connect(self.on_script_error)
        self.script_worker.start()
        
    def on_script_regenerated(self, script):
        """Handle the regenerated script"""
        # Add to variations
        self.variations.append(script)
        self.script_variations += 1
        self.current_variation = self.script_variations - 1
        
        # Update UI
        self.script_text.setText(script)
        self.regenerate_button.setEnabled(True)
        self.prev_variation_button.setEnabled(self.current_variation > 0)
        self.next_variation_button.setEnabled(self.current_variation < self.script_variations - 1)
        
    def show_previous_variation(self):
        """Show previous script variation"""
        if self.current_variation > 0:
            self.current_variation -= 1
            self.script_text.setText(self.variations[self.current_variation])
            self.prev_variation_button.setEnabled(self.current_variation > 0)
            self.next_variation_button.setEnabled(True)
            
    def show_next_variation(self):
        """Show next script variation"""
        if self.current_variation < self.script_variations - 1:
            self.current_variation += 1
            self.script_text.setText(self.variations[self.current_variation])
            self.next_variation_button.setEnabled(self.current_variation < self.script_variations - 1)
            self.prev_variation_button.setEnabled(True)
            
    def copy_script(self):
        """Copy the current script to clipboard"""
        QApplication.clipboard().setText(self.script_text.toPlainText())
        
        # Temporarily change button text to indicate copy
        original_text = self.copy_button.text()
        self.copy_button.setText("Copied! ✓")
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))
        
    def start_automation(self):
        """Start the automation process"""
        # Clear previous logs
        self.automation_logs = []
        self.status_text.clear()
        self.add_status_log("Preparing automation...")
        
        # Get current script
        script_text = self.script_text.toPlainText()
        
        # Extract just the content part (remove headers and formatting)
        script_lines = script_text.split('\n')
        extracted_script = ""
        content_started = False
        
        for line in script_lines:
            if content_started:
                # Stop at hashtags section
                if line.strip().startswith('#'):
                    break
                extracted_script += line + "\n"
            elif "[INTRO]" in line:
                content_started = True
        
        if not extracted_script.strip():
            # Fallback to use the whole script if extraction failed
            extracted_script = script_text
        
        # Create automation worker
        self.automation_worker = AutomationWorker(extracted_script)
        self.automation_worker.update_signal.connect(self.add_status_log)
        self.automation_worker.finished_signal.connect(self.on_automation_finished)
        self.automation_worker.error_signal.connect(self.on_automation_error)
        
        # Start automation
        self.automation_worker.start()
        self.auto_generate_button.setEnabled(False)
        
    def add_status_log(self, log):
        """Add a log message to the status text"""
        self.automation_logs.append(log)
        self.status_text.setText("\n".join(self.automation_logs))
        # Scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
        
    def on_automation_finished(self, output_file):
        """Handle automation completion"""
        if output_file:
            self.add_status_log(f"✅ Successfully generated audio: {output_file}")
            self.add_status_log("You can now upload this to Instagram!")
        else:
            self.add_status_log("⚠️ Automation completed but no output file was found")
            
        self.auto_generate_button.setEnabled(True)
        
    def on_automation_error(self, error):
        """Handle automation error"""
        self.add_status_log(f"❌ Error: {error}")
        self.auto_generate_button.setEnabled(True)

class AudioProcessor:
    """
    A class to handle processing of downloaded audio files.
    It monitors a directory for new audio files, processes them,
    and converts them to WAV format.
    """
    
    def __init__(self, input_dir=None, output_dir=None, ffmpeg_path=None):
        """
        Initialize the AudioProcessor.
        
        Args:
            input_dir (str): Directory to monitor for new audio files. Defaults to Downloads folder.
            output_dir (str): Directory to save processed files. Defaults to a 'processed_audio' folder.
            ffmpeg_path (str): Path to ffmpeg/ffprobe executable. If None, system PATH will be used.
        """
        # Set default directories if not specified
        if input_dir is None:
            self.input_dir = self._get_downloads_folder()
        else:
            self.input_dir = input_dir
            
        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_audio")
        else:
            self.output_dir = output_dir
            
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set ffmpeg path and configure environment properly
        self.ffmpeg_path = ffmpeg_path
        self._configure_ffmpeg()
        
        # Keep track of already processed files
        self.processed_files = set()
        
        # Default avatar image path for inference
        self.avatar_image = os.path.join(os.getcwd(), "avatar4.jpg")
        
        # Store video path for later use
        self.video_path = None
        
        # Status update callback (can be set to None if not using GUI)
        self.status_callback = None
        
        print(f"AudioProcessor initialized:")
        print(f"  - Monitoring: {self.input_dir}")
        print(f"  - Output dir: {self.output_dir}")
        if self.ffmpeg_path:
            print(f"  - FFmpeg path: {self.ffmpeg_path}")
        print(f"  - FFprobe path: {AudioSegment.ffprobe}")

    def _configure_ffmpeg(self):
        """
        Configure FFmpeg paths properly for both direct subprocess calls and PyDub.
        This method tries multiple approaches to find and set up FFmpeg correctly.
        """
        # Try to find FFmpeg if not explicitly provided
        if not self.ffmpeg_path:
            self.ffmpeg_path = self._find_ffmpeg_in_path()
            
        # If we still don't have a path, try common locations
        if not self.ffmpeg_path:
            self.ffmpeg_path = self._find_ffmpeg_in_common_locations()
            
        # If we found FFmpeg, set up all needed paths
        if self.ffmpeg_path:
            ffmpeg_dir = os.path.dirname(self.ffmpeg_path)
            
            # Add FFmpeg directory to system PATH
            if ffmpeg_dir not in os.environ['PATH']:
                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
            
            # Set explicit paths for PyDub
            AudioSegment.converter = self.ffmpeg_path
            AudioSegment.ffmpeg = self.ffmpeg_path
            
            # Find and set ffprobe path
            if os.name == 'nt':  # Windows
                ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe.exe")
            else:  # Linux/Mac
                ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe")
                
            if os.path.exists(ffprobe_path):
                AudioSegment.ffprobe = ffprobe_path
                print(f"Found FFprobe at: {ffprobe_path}")
            else:
                print(f"Warning: FFprobe not found at expected location: {ffprobe_path}")
                # Try to find ffprobe in PATH
                ffprobe_in_path = self._find_executable("ffprobe")
                if ffprobe_in_path:
                    AudioSegment.ffprobe = ffprobe_in_path
                    print(f"Found FFprobe in PATH: {ffprobe_in_path}")
                    
            # Verify FFmpeg and FFprobe work with PyDub
            self._verify_pydub_config()
        else:
            print("WARNING: FFmpeg not found. Audio conversion will fail.")
            print("\nTo fix this issue:")
            print("1. Download FFmpeg from https://ffmpeg.org/download.html")
            print("2. Either:")
            print("   a) Add FFmpeg to your system PATH, or")
            print("   b) Specify the path when creating the AudioProcessor instance:")
            print('      processor = AudioProcessor(ffmpeg_path="path/to/ffmpeg")')

    def _find_ffmpeg_in_path(self):
        """Find FFmpeg in system PATH."""
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run('where ffmpeg', shell=True, capture_output=True, text=True)
            else:  # Linux/Mac
                result = subprocess.run('which ffmpeg', shell=True, capture_output=True, text=True)
                
            if result.returncode == 0:
                ffmpeg_path = result.stdout.strip()
                print(f"Found FFmpeg in PATH: {ffmpeg_path}")
                return ffmpeg_path
        except Exception as e:
            print(f"Error finding FFmpeg in PATH: {e}")
        return None

    def _find_executable(self, name):
        """Find an executable in system PATH."""
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(f'where {name}', shell=True, capture_output=True, text=True)
            else:  # Linux/Mac
                result = subprocess.run(f'which {name}', shell=True, capture_output=True, text=True)
                
            if result.returncode == 0:
                path = result.stdout.strip()
                return path
        except Exception:
            pass
        return None

    def _find_ffmpeg_in_common_locations(self):
        """Try to find FFmpeg in common installation locations."""
        common_locations = []
        
        if os.name == 'nt':  # Windows
            # Check Program Files locations
            program_files = [
                os.environ.get('ProgramFiles', 'C:\\Program Files'),
                os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'),
                os.environ.get('LOCALAPPDATA', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local'))
            ]
            
            # Add common Windows installation paths
            for pf in program_files:
                common_locations.extend([
                    os.path.join(pf, 'ffmpeg', 'bin', 'ffmpeg.exe'),
                    os.path.join(pf, 'FFmpeg', 'bin', 'ffmpeg.exe')
                ])
                
            # Check in AppData/Local - common for user installations
            local_app_data = os.environ.get('LOCALAPPDATA', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local'))
            common_locations.extend([
                os.path.join(local_app_data, 'Programs', 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(local_app_data, 'Programs', 'FFmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(local_app_data, 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(local_app_data, 'FFmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(local_app_data, 'Programs', 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
            ])
            
            # Check user profile - common for manual installations
            user_profile = os.environ['USERPROFILE']
            common_locations.extend([
                os.path.join(user_profile, 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(user_profile, 'FFmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(user_profile, 'AppData', 'Local', 'Programs', 'ffmpeg-master-latest-win64-gpl-shared', 'bin', 'ffmpeg.exe')
            ])
        else:  # Linux/Mac
            common_locations.extend([
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/opt/local/bin/ffmpeg',
                '/opt/homebrew/bin/ffmpeg',
                os.path.expanduser('~/bin/ffmpeg')
            ])
            
        # Check each location
        for location in common_locations:
            if os.path.exists(location):
                print(f"Found FFmpeg at common location: {location}")
                return location
                
        return None

    def _verify_pydub_config(self):
        """Verify PyDub can find and use FFmpeg by trying a simple conversion."""
        try:
            # Create a simple 1-second silent audio segment
            silence = AudioSegment.silent(duration=100)
            
            # Create a temporary file path
            temp_dir = os.path.join(self.output_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, "test.wav")
            
            # Try to export it
            silence.export(temp_file, format="wav")
            
            # If it exists, PyDub is properly configured
            if os.path.exists(temp_file):
                print("PyDub is properly configured with FFmpeg!")
                os.remove(temp_file)  # Clean up
                return True
        except Exception as e:
            print(f"PyDub configuration test failed: {e}")
            # Don't return yet, we'll try explicit subprocess call
        
        # Try a direct subprocess call as fallback verification
        try:
            test_cmd = [self.ffmpeg_path, "-version"]
            result = subprocess.run(test_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("FFmpeg responds to direct subprocess calls.")
                return True
            else:
                print(f"FFmpeg subprocess test failed: {result.stderr}")
        except Exception as e:
            print(f"FFmpeg subprocess test failed with exception: {e}")
            
        return False
    
    def _get_downloads_folder(self):
        """Get the path to the user's Downloads folder."""
        home = Path.home()
        if os.name == 'nt':  # Windows
            return os.path.join(home, 'Downloads')
        else:  # Linux/Mac
            return os.path.join(home, 'Downloads')
    
    def wait_for_new_audio(self, timeout=300, file_patterns=None, target_pattern=None):
        """
        Wait for new audio files to appear in the input directory.
        
        Args:
            timeout (int): Maximum time to wait in seconds
            file_patterns (list): File patterns to monitor, e.g., ['*.mp3', '*.m4a']
                                 If None, defaults to common audio formats
            target_pattern (str): Regex pattern to match specific file names
        
        Returns:
            str: Path to new audio file, or None if timeout
        """
        if file_patterns is None:
            file_patterns = ['*.mp3', '*.wav', '*.m4a', '*.ogg', '*.flac', '*.aac']
        
        # Default pattern for "speechma_audio_*" files if not specified
        if target_pattern is None:
            target_pattern = r"speechma_audio_.*\.(?:mp3|wav|m4a|ogg|flac|aac)$"
        
        pattern_regex = re.compile(target_pattern)
        
        start_time = time.time()
        print(f"Watching for new audio files in {self.input_dir}...")
        print(f"Looking for files matching pattern: {target_pattern}")

        
        # Get initial list of files to compare against
        initial_files = set()
        for pattern in file_patterns:
            initial_files.update(glob.glob(os.path.join(self.input_dir, pattern)))
        
        # Add already processed files to avoid reprocessing
        initial_files.update(self.processed_files)
        
        # Get current time for comparison
        current_time = datetime.now()
        
        while time.time() - start_time < timeout:
            # Check for new files
            current_files = set()
            matching_files = []
            
            for pattern in file_patterns:
                new_files = glob.glob(os.path.join(self.input_dir, pattern))
                for file in new_files:
                    # Skip already processed files
                    if file in initial_files:
                        continue
                    
                    filename = os.path.basename(file)
                    # Check if file matches our target pattern
                    if pattern_regex.match(filename):
                        matching_files.append(file)
            
            if matching_files:
                # Sort by creation time to find the most recent file
                most_recent_file = max(matching_files, key=os.path.getctime)
                
                # Make sure we don't process a file we've already seen
                if most_recent_file not in self.processed_files:
                    print(f"Found new matching audio file: {most_recent_file}")
                    return most_recent_file
            
            # Wait before checking again
            time.sleep(1)
        
        print("Timeout waiting for new audio file")
        return None

    def convert_to_wav(self, input_file, sample_rate=44100):
        """
        Convert an audio file to WAV format with specified sample rate.
        
        Args:
            input_file (str): Path to input audio file
            sample_rate (int): Sample rate for output WAV
            
        Returns:
            str: Path to output WAV file, or None if conversion failed
        """
        if not os.path.exists(input_file):
            print(f"Error: File not found - {input_file}")
            return None
            
        try:
            # Get file name without extension
            filename = os.path.basename(input_file)
            name_without_ext = os.path.splitext(filename)[0]
            output_file = os.path.join(self.output_dir, f"{name_without_ext}.wav")
            
            print(f"Converting {input_file} to WAV format...")
            
            # Try direct FFmpeg command first as it's more reliable
            if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
                try:
                    # Construct the command - use list form instead of shell=True for better reliability
                    ffmpeg_cmd = [
                        self.ffmpeg_path,
                        "-i", input_file,
                        "-ar", str(sample_rate),
                        "-y",  # Overwrite output files without asking
                        output_file
                    ]
                    
                    print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
                    
                    # Run FFmpeg directly
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"Direct FFmpeg conversion successful: {output_file}")
                        # Mark this file as processed
                        self.processed_files.add(input_file)
                        return output_file
                    else:
                        print(f"Direct FFmpeg conversion failed: {result.stderr}")
                        print("Falling back to pydub...")
                except Exception as e:
                    print(f"Error with direct FFmpeg command: {e}")
                    print("Falling back to pydub...")
            
            # If direct FFmpeg fails or isn't available, use pydub
            print("Loading audio with pydub...")
            audio = AudioSegment.from_file(input_file)
            
            # Set the sample rate if requested
            if sample_rate:
                audio = audio.set_frame_rate(sample_rate)
                
            # Export as WAV
            print(f"Exporting to WAV: {output_file}")
            audio.export(output_file, format="wav")
            
            print(f"Conversion complete: {output_file}")
            
            # Mark this file as processed
            self.processed_files.add(input_file)
            
            return output_file
            
        except Exception as e:
            print(f"Error converting file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_status(self, message):
        """
        Update status message - either using callback or print
        
        Args:
            message (str): Status message to display
        """
        print(message)
        # If a status callback function is set, call it
        if self.status_callback:
            self.status_callback(message)
    
    def run_inference(self, audio_path):
        """
        Run the inference.py script with the processed audio file.
        
        Args:
            audio_path (str): Path to the processed WAV file
            
        Returns:
            bool: True if inference completed successfully, False otherwise
        """
        try:
            print(f"Starting inference with audio: {audio_path}")
            
            # Use sys.executable to ensure we use the same Python interpreter
            import sys
            import os
            python_executable = sys.executable
            
            # Path to the avatar image - make sure it exists!
            avatar_path = self.avatar_image
            if not os.path.exists(avatar_path):
                self.update_status(f"Error: Avatar image not found at {avatar_path}")
                return False
            
            # Build the command as a single string with proper quoting
            cmd_string = f'"{python_executable}" inference.py --driven_audio "{audio_path}" --source_image "{avatar_path}" --result_dir "results" --preprocess full --enhancer gfpgan --pose_style 1 --input_yaw 0 --input_pitch 0 --input_roll 0'
            # cmd_string = f'"{python_executable}" inference.py --driven_audio "{audio_path}" --source_image "{avatar_path}" --result_dir "results" --enhancer gfpgan'

            print(f"Running command: {cmd_string}")
            
            # Create a dict with the current environment variables
            env = os.environ.copy()
            
            # Use Popen to get real-time output
            process = subprocess.Popen(
                cmd_string,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Print output in real-time and capture video path if mentioned
            video_path_regex = re.compile(r"The generated video is named:?\s+(.*\.mp4)")
            print("Command output:")
            while True:
                output_line = process.stdout.readline()
                if output_line == '' and process.poll() is not None:
                    break
                if output_line:
                    print(output_line.strip())
                    # Try to capture video path if it's mentioned in output
                    match = video_path_regex.search(output_line)
                    if match:
                        potential_path = match.group(1).strip()
                        # Check if it's a relative or absolute path
                        if os.path.isabs(potential_path):
                            self.video_path = potential_path
                        else:
                            # Convert to absolute path
                            self.video_path = os.path.abspath(potential_path)
            
            # Get the return code
            return_code = process.poll()
            
            if return_code == 0:
                print("Inference completed successfully!")
                
                # If we haven't already captured the video path from output,
                # try to find it in the results folder
                if not hasattr(self, 'video_path') or not self.video_path or not os.path.exists(self.video_path):
                    # Find the most recently created mp4 file in the results directory
                    results_dir = os.path.join(os.getcwd(), "results")
                    if os.path.exists(results_dir):
                        mp4_files = []
                        # Look for mp4 files in results dir and any subdirectories
                        for root, dirs, files in os.walk(results_dir):
                            for file in files:
                                if file.endswith('.mp4'):
                                    mp4_files.append(os.path.join(root, file))
                        
                        if mp4_files:
                            # Get the most recently created video file
                            self.video_path = max(mp4_files, key=os.path.getctime)
                            self.update_status(f"Video generation complete. Ready to post: {os.path.basename(self.video_path)}")
                        else:
                            self.update_status("Inference successful but no video file found in results folder.")
                    else:
                        self.update_status("Results directory not found.")
                else:
                    self.update_status(f"Video generation complete. Ready to post: {os.path.basename(self.video_path)}")
                
                # Double check that the video path exists
                if hasattr(self, 'video_path') and self.video_path:
                    if os.path.exists(self.video_path):
                        print(f"Confirmed video exists at: {self.video_path}")
                    else:
                        print(f"Warning: Video file not found at path: {self.video_path}")
                
                return True
            else:
                print(f"Inference failed with return code: {return_code}")
                self.update_status("Video generation failed.")
                return False
        except Exception as e:
            print(f"Error during inference: {str(e)}")
            self.update_status(f"Error during video generation: {str(e)}")
            return False    

    def set_avatar_image(self, image_path):
        """
        Set the avatar image path for inference.
        
        Args:
            image_path (str): Path to the avatar image
        """
        if os.path.exists(image_path):
            self.avatar_image = image_path
            print(f"Avatar image set to: {self.avatar_image}")
        else:
            print(f"Warning: Avatar image not found at {image_path}")
    
    def process_file(self, file_path=None, sample_rate=44100, target_pattern=None, run_inference=True):
        """
        Process a file: either the specified file or wait for a new one.
        Then optionally run inference with the processed audio.
        
        Args:
            file_path (str): Optional path to file. If None, wait for a new file.
            sample_rate (int): Sample rate for output WAV
            target_pattern (str): Regex pattern to match specific file names
            run_inference (bool): Whether to automatically run inference after processing
            
        Returns:
            tuple: (wav_path, inference_success) where wav_path is the path to processed WAV file,
                   and inference_success is a boolean indicating if inference was successful
        """
        # If no file specified, wait for a new one to appear
        if file_path is None:
            file_path = self.wait_for_new_audio(target_pattern=target_pattern)
            
        if file_path is None:
            return None, False
            
        # Convert the file to WAV
        wav_path = self.convert_to_wav(file_path, sample_rate)
        
        if wav_path is None:
            return None, False
            
        # Run inference if requested
        inference_success = False
        if run_inference and wav_path:
            inference_success = self.run_inference(wav_path)
            
        return wav_path, inference_success
        
    def open_video_in_file_manager(self):
        """Uploads the newly generated video to Instagram using Chrome automation with enhanced error handling and waiting for proper page loading"""
        # Debug prints to help troubleshoot
        print(f"Debug: video_path attribute exists: {hasattr(self, 'video_path')}")
        if hasattr(self, 'video_path'):
            print(f"Debug: video_path value: {self.video_path}")
            print(f"Debug: video file exists: {os.path.exists(self.video_path) if self.video_path else 'No path set'}")
        
        # First verify we have a valid video path
        if not (hasattr(self, 'video_path') and self.video_path and os.path.exists(self.video_path)):
            self.update_status("No video file available to upload.")
            # Try to look in results directory for recent mp4 files as a fallback
            results_dir = os.path.join(os.getcwd(), "results")
            if os.path.exists(results_dir):
                mp4_files = [os.path.join(results_dir, f) for f in os.listdir(results_dir) 
                            if f.endswith('.mp4')]
                
                if mp4_files:
                    # Get the most recently created video file
                    self.video_path = max(mp4_files, key=os.path.getctime)
                    self.update_status(f"Found video file as fallback: {os.path.basename(self.video_path)}")
                else:
                    self.update_status("No MP4 files found in results directory.")
                    return
            else:
                self.update_status("Results directory not found.")
                return
        
        # Now that we have a valid video path, let's upload to Instagram
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
            from webdriver_manager.chrome import ChromeDriverManager
            import time
            
            self.update_status("Starting Instagram upload process...")
            
            # Instagram credentials
            username = "Write your username here"
            password = "Write your password here"
            
            # Setup Chrome with optimized options
            options = webdriver.ChromeOptions()
            # Performance and stability options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--enable-gpu-rasterization")
            options.add_argument("--force-gpu-mem-available-mb=4096")
            
            # Add experimental options to handle latency and automation detection
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_experimental_option("detach", True)
            
            # Start Chrome browser with automatic webdriver management
            self.update_status("Initializing Chrome browser...")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.maximize_window()
            
            # Custom wait function that handles common exceptions
            def wait_for_element(driver, locator, timeout=20, condition=EC.visibility_of_element_located):
                try:
                    element = WebDriverWait(driver, timeout).until(
                        condition(locator)
                    )
                    return element
                except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
                    self.update_status(f"Error finding element {locator}: {str(e)}")
                    return None
            
            # Navigate to Instagram
            self.update_status("Opening Instagram...")
            driver.get("https://www.instagram.com/")
            
            # Wait for the login page to load
            wait = WebDriverWait(driver, 30)
            
            try:
                # Wait for the login fields to be visible
                self.update_status("Waiting for login page to load...")
                username_field = wait_for_element(driver, (By.CSS_SELECTOR, "input[name='username']"))
                if not username_field:
                    raise Exception("Username field not found")
                    
                password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
                
                # Enter credentials
                self.update_status("Entering login credentials...")
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
                
                # Click login button
                login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()
                
                # Wait for and handle the "Save Login Info" dialog if it appears
                self.update_status("Checking for 'Save Login Info' dialog...")
                try:
                    # First try the exact element structure provided
                    not_now_selector = (By.XPATH, "//div[@role='button' and contains(@class, 'x1i10hfl') and contains(text(), 'Not now')]")
                    
                    # List of potential "Not Now" button selectors
                    not_now_selectors = [
                        not_now_selector,
                        (By.XPATH, "//div[@role='button' and contains(text(), 'Not now')]"),
                        (By.XPATH, "//div[@role='button' and contains(text(), 'Not Now')]"),
                        (By.XPATH, "//button[contains(text(), 'Not now')]"),
                        (By.XPATH, "//button[contains(text(), 'Not Now')]"),
                        (By.XPATH, "//div[contains(@class, 'x1i10hfl') and @role='button' and contains(., 'Not now')]"),
                        (By.XPATH, "//div[contains(@class, 'x1i10hfl') and @role='button' and contains(., 'Not Now')]"),
                        (By.XPATH, "//div[contains(@class, 'x1i10hfl') and @tabindex='0' and @role='button']"),
                    ]
                    
                    for selector in not_now_selectors:
                        not_now_button = wait_for_element(driver, selector, timeout=3)
                        if not_now_button:
                            self.update_status(f"'Save Login Info' dialog detected, clicking 'Not Now' button...")
                            try:
                                # First try direct click
                                not_now_button.click()
                                self.update_status("Successfully clicked 'Not Now' button with direct click")
                                break
                            except Exception as e:
                                self.update_status(f"Direct click on 'Not Now' failed, trying JavaScript click: {str(e)}")
                                try:
                                    # Try JavaScript click
                                    driver.execute_script("arguments[0].click();", not_now_button)
                                    self.update_status("Successfully clicked 'Not Now' button with JavaScript click")
                                    break
                                except Exception as e2:
                                    self.update_status(f"JavaScript click on 'Not Now' failed, trying ActionChains: {str(e2)}")
                                    try:
                                        # Try ActionChains
                                        from selenium.webdriver.common.action_chains import ActionChains
                                        actions = ActionChains(driver)
                                        actions.move_to_element(not_now_button).click().perform()
                                        self.update_status("Successfully clicked 'Not Now' button with ActionChains")
                                        break
                                    except Exception as e3:
                                        self.update_status(f"ActionChains click on 'Not Now' failed: {str(e3)}")
                                        continue
                    
                    # Give the UI time to update after clicking the button
                    time.sleep(2)
                    
                except Exception as e:
                    self.update_status(f"Note: 'Save Login Info' dialog handling completed: {str(e)}")
                
                # Check for "Turn on Notifications" dialog and dismiss if present
                try:
                    notifications_dialog = wait_for_element(
                        driver, 
                        (By.XPATH, "//button[contains(text(), 'Not Now')]"), 
                        timeout=5
                    )
                    
                    if notifications_dialog:
                        self.update_status("'Turn on Notifications' dialog detected, clicking 'Not Now'...")
                        notifications_dialog.click()
                        time.sleep(1)  # Short pause after clicking
                except Exception as e:
                    self.update_status(f"Note: Notifications dialog not found or already handled: {str(e)}")
                
                # Verify we are on the home page by checking for multiple homepage elements
                self.update_status("Verifying successful login and home page load...")
                
                # Define a list of possible home page indicators
                home_indicators = [
                    (By.CSS_SELECTOR, "svg[aria-label='Home']"),
                    (By.CSS_SELECTOR, "svg[aria-label='Create']"),
                    (By.CSS_SELECTOR, "svg[aria-label='Search']"),
                    (By.CSS_SELECTOR, "svg[aria-label='Explore']"),
                    # Header elements
                    (By.CSS_SELECTOR, "nav[role='navigation']"),
                    # Feed elements
                    (By.CSS_SELECTOR, "main[role='main']"),
                    # Profile elements  
                    (By.CSS_SELECTOR, "span[aria-label='Profile']")
                ]
                
                # Check for at least two indicators to confirm we're on the home page
                indicators_found = 0
                for indicator in home_indicators:
                    try:
                        element = wait_for_element(driver, indicator, timeout=5)
                        if element:
                            indicators_found += 1
                            if indicators_found >= 2:
                                break
                    except:
                        continue
                
                if indicators_found < 2:
                    raise Exception("Failed to verify home page load - insufficient indicators found")
                
                self.update_status("Instagram home page successfully loaded!")
                
                # Wait for the create button to be fully interactive
                self.update_status("Looking for create button...")
                create_button = None
                
                # Try multiple selectors for the create button
                create_button_selectors = [
                    (By.CSS_SELECTOR, "svg[aria-label='Create']"),
                    (By.XPATH, "//div[@role='button' and contains(@aria-label, 'Create')]"),
                    (By.XPATH, "//a[contains(@href, '/create/')]"),
                    (By.CSS_SELECTOR, "[aria-label='New post']"),
                    (By.XPATH, "//div[contains(@aria-label, 'New post')]"),
                    (By.XPATH, "//div[contains(@aria-label, 'New')]"),
                    (By.XPATH, "//span[contains(text(), 'Create')]"),
                    (By.XPATH, "//a[@role='link' and contains(@href, '/create')]"),
                    (By.XPATH, "//div[@role='button']//*[local-name()='svg' and @aria-label='Create']"),
                    (By.XPATH, "//div[@role='button']//*[local-name()='svg' and @aria-label='New post']")
                ]
                
                for selector in create_button_selectors:
                    try:
                        element = wait_for_element(driver, selector, timeout=5)
                        if element:
                            create_button = element
                            self.update_status(f"Found create button using selector: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if not create_button:
                    # Final attempt: look for the parent container of the create button
                    try:
                        # Get all clickable elements
                        clickable_elements = driver.find_elements(By.CSS_SELECTOR, "[role='button']")
                        for element in clickable_elements:
                            try:
                                # Check if this might be the create button by looking at its aria-label
                                aria_label = element.get_attribute("aria-label")
                                if aria_label and ("create" in aria_label.lower() or "new" in aria_label.lower() or "post" in aria_label.lower()):
                                    create_button = element
                                    self.update_status(f"Found create button by aria-label: {aria_label}")
                                    break
                            except:
                                pass
                    except Exception as e:
                        pass
                
                if not create_button:
                    raise Exception("Create button not found after trying multiple methods")
                
                # Give the page a moment to stabilize before clicking
                time.sleep(2)
                
                # Click on create button
                self.update_status("Clicking create button...")
                try:
                    # First try direct click
                    create_button.click()
                except Exception as e:
                    self.update_status(f"Direct click failed, trying alternative clicking methods: {str(e)}")
                    try:
                        # Try JavaScript click as fallback
                        driver.execute_script("arguments[0].click();", create_button)
                    except Exception as e2:
                        self.update_status(f"JavaScript click failed, trying ActionChains: {str(e2)}")
                        # Try ActionChains as second fallback
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(create_button).click().perform()
                
                # Wait for the create post dialog to appear
                self.update_status("Waiting for upload dialog...")
                select_from_computer = wait_for_element(
                    driver, 
                    (By.XPATH, "//button[contains(text(), 'Select from computer')]"),
                    timeout=30
                )
                
                if not select_from_computer:
                    # Try alternative selector
                    select_from_computer = wait_for_element(
                        driver,
                        (By.XPATH, "//div[contains(text(), 'Select from computer')]"),
                        timeout=10
                    )
                    
                if not select_from_computer:
                    raise Exception("'Select from computer' button not found")
                
                # Click on "Select from computer"
                self.update_status("Selecting video from computer...")
                driver.execute_script("arguments[0].click();", select_from_computer)
                
                # Wait for file input to be ready
                time.sleep(2)
                
                try:
                    # Locate the file input element (it's usually hidden)
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    
                    if not file_inputs:
                        raise Exception("File input element not found")
                    
                    # Try each file input until one works
                    file_input_success = False
                    for file_input in file_inputs:
                        try:
                            # Send the file path directly to the input element
                            file_input.send_keys(self.video_path)
                            file_input_success = True
                            break
                        except Exception as e:
                            self.update_status(f"Trying another file input: {str(e)}")
                            continue
                    
                    if not file_input_success:
                        raise Exception("Failed to send file path to any file input element")
                    
                    self.update_status("Uploading video...")
                    
                    # Wait for upload to complete and next button to be enabled (with generous timeout for large videos)
                    self.update_status("Waiting for video to upload and process...")
                    next_button = wait_for_element(
                        driver, 
                        (By.XPATH, "//button[contains(text(), 'Next')]"),
                        timeout=30,  # 3 minutes timeout for large video upload
                        condition=EC.element_to_be_clickable
                    )
                    
                    if not next_button:
                        raise Exception("Next button not found or not clickable after upload")
                    
                    # Click next to proceed to filters page
                    self.update_status("Upload complete. Moving to filters page...")
                    driver.execute_script("arguments[0].click();", next_button)
                    
                    # Wait for filters/editing page and click next again
                    next_button = wait_for_element(
                        driver, 
                        (By.XPATH, "//button[contains(text(), 'Next')]"),
                        timeout=30,
                        condition=EC.element_to_be_clickable
                    )
                    
                    if not next_button:
                        raise Exception("Next button not found on filters page")
                    
                    self.update_status("Moving to caption page...")
                    driver.execute_script("arguments[0].click();", next_button)
                    
                    # Wait for caption page and click share
                    self.update_status("Adding caption and finalizing post...")
                    share_button = wait_for_element(
                        driver, 
                        (By.XPATH, "//button[contains(text(), 'Share')]"),
                        timeout=30,
                        condition=EC.element_to_be_clickable
                    )
                    
                    if not share_button:
                        # Try alternative share button text
                        share_button = wait_for_element(
                            driver,
                            (By.XPATH, "//button[contains(text(), 'Post')]"),
                            timeout=10
                        )
                    
                    if not share_button:
                        raise Exception("Share button not found")
                    
                    # Optional: Add a caption here if desired
                    try:
                        caption_area = driver.find_element(By.CSS_SELECTOR, "textarea[aria-label='Write a caption...']")
                        caption_area.send_keys("Check out my latest video! #automated #upload")
                    except Exception as e:
                        self.update_status(f"Note: Couldn't add caption: {str(e)}")
                    
                    # Finally, share the post
                    self.update_status("Sharing post...")
                    driver.execute_script("arguments[0].click();", share_button)
                    
                    # Wait for confirmation that post was shared
                    confirmation = wait_for_element(
                        driver,
                        (By.XPATH, "//*[contains(text(), 'Your post has been shared')]"),
                        timeout=60
                    )
                    
                    if confirmation:
                        self.update_status("✅ Video successfully posted to Instagram!")
                    else:
                        # Check for alternative confirmation indicators
                        time.sleep(10)  # Give time for the post to complete
                        
                        # If we're back at the home page, likely successful
                        home_button = wait_for_element(driver, (By.CSS_SELECTOR, "svg[aria-label='Home']"), timeout=5)
                        if home_button:
                            self.update_status("✅ Video posted to Instagram! (Inferred from return to home page)")
                        else:
                            self.update_status("⚠️ Upload may have completed, but confirmation not detected")
                    
                except Exception as e:
                    self.update_status(f"Error during file upload: {str(e)}")
            
            except TimeoutException as e:
                self.update_status(f"Timeout waiting for Instagram elements: {str(e)}")
            except Exception as e:
                self.update_status(f"Error during Instagram automation: {str(e)}")
            
            # Keep the browser open for review
            self.update_status("Keeping browser open for 1 minute for review...")
            time.sleep(60)
            
            # Close the browser
            driver.quit()
            self.update_status("Browser closed. Instagram upload process completed.")
            
        except ImportError:
            self.update_status("Error: Selenium is required for Instagram automation. Please install it with 'pip install selenium webdriver-manager'.")
        except Exception as e:
            self.update_status(f"Error starting Instagram automation: {str(e)}")
            
    def set_status_callback(self, callback_function):
        """
        Set a callback function for status updates
        
        Args:
            callback_function: Function that accepts a single string parameter
        """
        self.status_callback = callback_function

if __name__ == "__main__":
    # Create the application
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the window
    window = InstagramContentGeneratorApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())
