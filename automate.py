import os
import time
import random
import shutil
import subprocess
import tempfile
import sys
import threading
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
from groq import Groq

# Import our custom audio processor module
from audio_processor import AudioProcessor

def display_menu(options):
    """Display a menu of options and get user selection."""
    print("\nSelect an option:")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    while True:
        try:
            choice = int(input("\nEnter your choice (number): "))
            if 1 <= choice <= len(options):
                return choice
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")

def get_content_topics():
    """Return the content topics and their subtopics."""
    return {
        "Soft Life Aesthetic + Wellness Advice": [
            "Daily affirmations with lip-sync + subtitles",
            "AI-generated motivational rants about self-love",
            "Motivational rants about boundaries",
            "Motivational rants about growth",
            "You are not too sensitive. You're just finally listening to yourself."
        ],
        "AI + Life Tips (Make Tech Emotional)": [
            "I'm your AI bestie here to remind you...",
            "Short clips explaining AI concepts in relatable language",
            "Productivity hacks",
            "Mental clarity tips",
            "Digital minimalism"
        ],
        "Emotional Intelligence & Healing": [
            "Overthinking",
            "Toxic relationships",
            "Setting boundaries",
            "Here's what no one tells you about healing",
            "Gentle healing practices"
        ],
        "Controversial but Classy Opinions (Micro-Thoughts)": [
            "Unpopular opinion, but being hard on yourself isn't discipline, it's trauma.",
            "Controversial takes on modern productivity",
            "Unpopular opinions about social media",
            "Thought-provoking perspectives on digital culture",
            "Challenging conventional wisdom"
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

def generate_script(main_topic, subtopic):
    """Generate a script about the given topic using Groq API."""
    # Use API key from environment variables
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not found in environment variables.")
        api_key = input("Please enter your Groq API key: ")
        os.environ["GROQ_API_KEY"] = api_key
    
    client = Groq(api_key=api_key)
    
    # System prompt to generate a short script
    system_prompt = f"""You are a professional script writer for Instagram content creators.
    
    Create a concise, engaging 45-second script (approximately 125-150 words) 
    for an Instagram video about the topic: {main_topic} - {subtopic}.
    
    The script should:
    - Start with a BOLD HOOK.
    - Be appropriate for spoken delivery on Instagram by a female creator
    - Have a clear beginning, middle, and end
    - Use natural conversational language with "bestie talk" style
    - Include pauses, emphasis, and relatable examples
    - Be informative yet engaging for social media audience
    - Include a catchy hook in the first 3 seconds
    - End with a question or call to action to encourage engagement
    
    DO NOT include any stage directions, timings, or formatting notes.
    Write ONLY the script text that would be spoken aloud on Instagram.
    DO NOT include any headings either, only the script.
    """
    
    try:
        # Make API call to Groq
        print(f"Generating script for: {main_topic} - {subtopic}...")
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a 45-second Instagram script about: {main_topic} - {subtopic}"}
            ],
            temperature=0.7,
            max_tokens=300,  # Limit to keep it around 45 seconds of speech
            top_p=1,
            stream=False
        )
        
        # Extract the generated script
        script_content = completion.choices[0].message.content
        return script_content
    except Exception as e:
        print(f"Error generating script with Groq API: {e}")
        fallback_script = f"Hey there! Today I want to talk to you about {subtopic} in the realm of {main_topic}. " \
                         f"This is such an important topic that can really transform your perspective. " \
                         f"Let me share a few thoughts on this. First, remember that your journey is unique. " \
                         f"Second, small steps lead to big changes. And finally, you have everything you need within you already. " \
                         f"What's one step you're taking today to embrace this? Let me know in the comments below!"
        print("Using fallback script instead.")
        return fallback_script

def close_chrome_processes():
    """Attempt to close any running Chrome processes"""
    print("Closing any existing Chrome processes...")
    try:
        if os.name == 'nt':  # Windows
            subprocess.call('taskkill /f /im chrome.exe', shell=True)
        else:  # Linux/Mac
            subprocess.call('pkill -f chrome', shell=True)
        time.sleep(2)  # Give it time to close
    except Exception as e:
        print(f"Note: Couldn't close Chrome processes: {e}")
        print("You may want to close Chrome manually before running this script.")

def start_audio_monitor(downloads_folder):
    """
    Start a background thread to monitor for downloaded files and process them
    
    Args:
        downloads_folder (str): Path to the downloads folder to monitor
        
    Returns:
        tuple: (threading.Thread, AudioProcessor) - The monitoring thread and processor instance
    """
    # Create audio processor instance
    processor = AudioProcessor(input_dir=downloads_folder)
    
    # Define the monitoring function
    def monitor_audio_files():
        print("Starting audio file monitoring thread...")
        while True:
            try:
                # Wait for and process new audio files
                wav_file = processor.process_file()
                
                if wav_file:
                    print(f"✓ Successfully processed audio to WAV: {wav_file}")
                    # Additional processing could be added here
                else:
                    # Sleep before retrying - this prevents CPU overuse
                    time.sleep(5)
                    
            except Exception as e:
                print(f"Error in audio monitoring thread: {e}")
                time.sleep(5)  # Sleep before retrying on error
    
    # Create and start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_audio_files, daemon=True)
    monitor_thread.start()
    
    return monitor_thread, processor

def main():
    # Get available content topics
    topics_dict = get_content_topics()
    topics_list = list(topics_dict.keys())

    # Display topic menu and get user's choice
    print("\n=== Instagram Script Generator and Text-to-Speech Automation ===\n")
    print("First, let's choose a topic for your Instagram content:")
    selected_topic_index = display_menu(topics_list) - 1
    selected_topic = topics_list[selected_topic_index]
    
    # Display subtopic menu and get user's choice
    print(f"\nNow, choose a subtopic for '{selected_topic}':")
    subtopics = topics_dict[selected_topic]
    selected_subtopic_index = display_menu(subtopics) - 1
    selected_subtopic = subtopics[selected_subtopic_index]
    
    # Generate script using Groq API
    user_script = generate_script(selected_topic, selected_subtopic)
    
    print("\n=== Generated Script ===")
    print(user_script)
    print("========================\n")
    
    # Ask user if they want to proceed with this script
    proceed = input("\nDo you want to proceed with this script? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Exiting program.")
        return
    
    # Detect downloads folder
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    print(f"Using downloads folder: {downloads_folder}")
    
    # Start audio monitoring in a background thread
    monitor_thread, audio_processor = start_audio_monitor(downloads_folder)
    print(f"Audio monitor started. Files will be converted to WAV format in: {audio_processor.output_dir}")
    
    # Try to close any running Chrome processes
    close_chrome_processes()
    
    # Set up Chrome options
    chrome_options = Options()
    
    # Essential options to prevent crashes
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    
    # Set default download directory to the detected downloads folder
    prefs = {"download.default_directory": downloads_folder}
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Option 1: Try running Chrome without a user data directory first
    # This will use a fresh, temporary profile
    print("Trying to start Chrome with default settings...")
    
    driver = None
    
    try:
        # Initialize Chrome driver with the webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Successfully started Chrome!")
        
        # Navigate to the website
        print("Opening https://speechma.com/...")
        driver.get("https://speechma.com/")
        
        # Wait for the page to load fully
        print("Waiting for page to load...")
        time.sleep(5)
        
        # Find the search bar for voices
        print("Looking for voice search bar...")
        wait = WebDriverWait(driver, 15)
        
        # First try: look for typical search elements
        try:
            # Look for search elements using different techniques
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
                print("Found search bar. Searching for 'Emily' voice...")
                driver.execute_script("arguments[0].scrollIntoView(true);", search_bar)
                time.sleep(1)
                search_bar.clear()
                search_bar.send_keys("Emily")
                search_bar.send_keys(Keys.RETURN)
                
                # Wait for search results
                print("Waiting for search results...")
                time.sleep(3)
                
                # Find elements that contain "Emily" text and then get their parent elements
                print("Looking for Emily voice option...")
                
                # Try various strategies to find the clickable element
                try:
                    # Strategy 1: Find the element containing Emily and get its parent or ancestor
                    emily_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Emily')]")
                    for element in emily_elements:
                        if element.is_displayed():
                            print("Found element with Emily text. Getting parent...")
                            
                            # Method 1: Try getting direct parent
                            try:
                                parent = driver.execute_script("return arguments[0].parentNode;", element)
                                
                                # Try going up further if needed
                                grand_parent = driver.execute_script("return arguments[0].parentNode;", parent)
                                great_grand_parent = driver.execute_script("return arguments[0].parentNode;", grand_parent)
                                
                                # Try clickable parents in order
                                clickable_elements = [
                                    parent,
                                    grand_parent, 
                                    great_grand_parent,
                                    driver.execute_script("return arguments[0].parentNode;", great_grand_parent)
                                ]
                                
                                # Try clicking each parent until one works
                                for clickable in clickable_elements:
                                    try:
                                        print("Trying to click a parent element...")
                                        driver.execute_script("arguments[0].scrollIntoView(true);", clickable)
                                        time.sleep(1)
                                        
                                        # Check if there's any popup or overlay first
                                        try:
                                            overlay = driver.find_element(By.ID, "api-notification")
                                            if overlay.is_displayed():
                                                print("Found overlay. Attempting to close it first...")
                                                driver.execute_script("arguments[0].style.display='none';", overlay)
                                                time.sleep(1)
                                        except:
                                            pass
                                        
                                        # Try JavaScript click which bypasses overlay issues
                                        driver.execute_script("arguments[0].click();", clickable)
                                        print("Clicked using JavaScript!")
                                        break
                                    except Exception as click_error:
                                        print(f"Click attempt failed: {click_error}")
                                        continue
                                
                                break
                                
                            except Exception as parent_error:
                                print(f"Error getting parent: {parent_error}")
                                continue
                    
                    # If that didn't work, try strategy 2: XPath for clickable containers
                    if "emily_option" not in locals():
                        print("Trying alternate strategy for finding Emily voice...")
                        
                        # Strategy 2: Find clickable elements like cards or containers that contain Emily text
                        card_selectors = [
                            "//div[contains(@class, 'card') and .//text()[contains(., 'Emily')]]",
                            "//div[contains(@class, 'voice') and .//text()[contains(., 'Emily')]]",
                            "//div[contains(@class, 'item') and .//text()[contains(., 'Emily')]]",
                            "//li[.//text()[contains(., 'Emily')]]",
                            "//div[.//div[contains(text(), 'Emily')]]"
                        ]
                        
                        for selector in card_selectors:
                            try:
                                cards = driver.find_elements(By.XPATH, selector)
                                if cards:
                                    for card in cards:
                                        if card.is_displayed():
                                            print(f"Found voice card/container. Trying to click...")
                                            driver.execute_script("arguments[0].scrollIntoView(true);", card)
                                            time.sleep(1)
                                            driver.execute_script("arguments[0].click();", card)
                                            print("Clicked on voice container!")
                                            break
                                    break
                            except Exception as card_error:
                                print(f"Card selector error: {card_error}")
                                continue
                                
                except Exception as emily_error:
                    print(f"Error finding Emily voice: {emily_error}")
                    print("Please select the Emily voice manually.")
                
                # Wait for the voice selection to be applied
                time.sleep(3)
                
                # Find the text input area - look for textarea or contenteditable elements
                print("Looking for text input area...")
                input_elements = driver.find_elements(By.XPATH, "//textarea | //div[@contenteditable='true'] | //input[@type='text']")
                
                text_area = None
                for element in input_elements:
                    if element.is_displayed():
                        text_area = element
                        break
                
                if text_area:
                    print("Found text input area. Pasting your script...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", text_area)
                    time.sleep(1)
                    text_area.clear()
                    text_area.send_keys(user_script)
                    print("Script has been entered. You can now continue manually.")
                else:
                    print("Couldn't find the text input area. Please paste your script manually.")

                print("Reading CAPTCHA using OCR...")
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

                    print(f"OCR detected CAPTCHA: {captcha_text}")

                    if len(captcha_text) != 5:
                        print("Detected CAPTCHA is not 5 digits. Please enter the CAPTCHA code manually.")
                        captcha_text = input("Enter the 5-digit CAPTCHA code you see: ")

                    # Enter the CAPTCHA into the input field
                    captcha_input = driver.find_element(By.ID, "captchaInput")
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_text)
                    time.sleep(1)
                except Exception as e:
                    print("CAPTCHA OCR failed:", e)
                    print("Please enter the CAPTCHA code manually.")

                # Click the "Generate Audio" button
                print("Looking for the Generate Audio button...")
                try:
                    generate_button = wait.until(EC.element_to_be_clickable((By.ID, "convertButton")))
                    driver.execute_script("arguments[0].scrollIntoView(true);", generate_button)
                    generate_button.click()
                    print("Clicked Generate Audio button.")
                except Exception as e:
                    print(f"Could not find Generate Audio button: {e}")
                    print("Please click the Generate Audio button manually.")

                print("Waiting for audio generation and Download button to appear...")
                print("(The audio file will be automatically processed once downloaded)")
                
                # Wait for the download button to appear in the audio controls
                try:
                    download_button = WebDriverWait(driver, 60).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'download-btn')]"))
                    )

                    # Scroll into view and click the Download button
                    print("Clicking the Download button...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", download_button)
                    time.sleep(2)  # Slight delay for smoother behavior
                    driver.execute_script("arguments[0].click();", download_button)
                    
                    # Give some time for the download to start
                    print("Download initiated!")
                    print("Waiting for download to complete...")
                except Exception as e:
                    print(f"Could not find Download button: {e}")
                    print("Please click the Download button manually when audio generation is complete.")
                
                # Wait for a reasonable time for download to complete
                time.sleep(10)
                
                print("\nThe audio processor will continue running in the background.")
                print("Any downloaded audio files will be automatically converted to WAV format.")
                print("Converted files will be saved to:", audio_processor.output_dir)
                
                # Keep the browser open for the user to continue
                print("\nBrowser will stay open for you to continue manually.")
                print("Press Enter when you're done to close the browser...")
                input()

            else:
                print("Couldn't find the search bar. Please navigate the website manually.")
                
        except Exception as e:
            print(f"Error interacting with the website: {e}")
            print("You can continue manually from here.")
        
    except Exception as e:
        print(f"Error starting Chrome: {e}")
        print("Let's try a different approach...")
        
        # Option 2: Try a different approach without user data directory
        try:
            # Create a completely new set of options
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Set download directory
            prefs = {"download.default_directory": downloads_folder}
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Explicitly start without any user data directory
            print("Starting Chrome without custom profile...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            print("Chrome started! Opening https://speechma.com/...")
            driver.get("https://speechma.com/")
            print("Website opened. Please continue manually:")
            print(f"1. Search for 'Emily' voice")
            print(f"2. Select it from the results")
            print(f"3. Paste this text into the input area: {user_script}")
            
            print("\nThe audio processor will continue running in the background.")
            print("Any downloaded audio files will be automatically converted to WAV format.")
            print("Converted files will be saved to:", audio_processor.output_dir)
            
            print("\nPress Enter when you're done to close the browser...")
            input()
            
        except Exception as e2:
            print(f"Second attempt also failed: {e2}")
            print("\nPlease try the following manually:")
            print("1. Open Chrome yourself")
            print("2. Go to https://speechma.com/")
            print("3. Search for 'Emily' voice")
            print("4. Select it and paste your script")
            
            print("\nThe audio processor will continue running in the background.")
            print("Any downloaded audio files will be automatically converted to WAV format.")
            print("Converted files will be saved to:", audio_processor.output_dir)
            
            print("\nPress Enter when you're done to exit the program...")
            input()
    
    finally:
        # Clean up
        print("Closing browser...")
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        
        print("\nBrowser closed. Audio processor will continue running...")
        print("Press Ctrl+C to terminate the program completely when finished.")
        
        # Wait for the monitoring thread to finish - this keeps the program running
        # until the user manually terminates it
        try:
            monitor_thread.join()
        except KeyboardInterrupt:
            print("\nProgram terminated by user.")

if __name__ == "__main__":
    main()