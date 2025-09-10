
# 🧠🎬 Automated Talking-Head Video Generation & Instagram Reels Uploader

This project automates the generation and publishing of personalized talking-head videos using AI-driven tools like SadTalker, browser-based TTS (Speechma.io), and Selenium automation. It enables the creation of high-quality videos with human-like speech and facial animation, followed by auto-upload to Instagram Reels—all orchestrated via Python.

## 🔧 How It Works

1. **Script Generation**: Generate content scripts using LLMs (e.g., LLaMA).
2. **Speech Synthesis**: Convert script to voice using Speechma.io via Selenium automation.
3. **Video Generation**: Use SadTalker to create a talking-head video from an image and the synthesized audio.
4. **Instagram Automation**: Automatically upload the generated video to Instagram Reels using browser automation.

## 📸 Screenshots

Here’s a preview of the project in action:

![App Interface](assets/screenshot1.png)
*Main interface with automation controls.*

![Generated Video Preview] https://github.com/laiba-javaid/automated-video-generation/blob/main/2025_05_19_2.12.17.mp4
*Example of a generated talking-head video.*

> 🔄 **Note**: While SadTalker is used as the core video generation engine, this project builds an **end-to-end pipeline** around it. The system is designed to automate the full process—from script to Instagram post—using Python and browser automation (e.g., Selenium opens Chrome, navigates to Speechma.io, downloads audio, and triggers SadTalker), which goes beyond the scope of SadTalker's original functionality.

---

## 🚀 Quick Start

### 1. Clone and Set Up SadTalker

> SadTalker GitHub: [https://github.com/OpenTalker/SadTalker](https://github.com/OpenTalker/SadTalker)

First, install and run SadTalker on your system. Follow their setup instructions to ensure all dependencies and models are properly installed.

### 2. Add Your Files

Once SadTalker is set up:

* Go to SadTalker’s main directory.
* Add your avatar image (e.g., `avatar.jpg`).
* Copy the following files from this repository into the SadTalker directory:

  * `audio.wav` (your generated speech file)
  * `automate.py` or `gui.py` (depending on your preferred interface)

### 3. Run the Script

To generate the video:

```bash
python automate.py
```

Or use the GUI:

```bash
python gui.py
```

SadTalker will then generate the lip-synced video.

> ⚠️ Anyone running this will need to download necessary models manually. This is the user's responsibility and not handled automatically. Make sure they understand how SadTalker works before proceeding.

---

## 📤 Auto-Publish to Instagram

After generating the video:

1. The Python script uses Selenium to open a browser.
2. It logs into Instagram.
3. Uploads the video as a Reel.

Make sure to update the script with your Instagram credentials or use session cookies securely.

---

## 🧪 Requirements

* Python 3.8+
* Selenium
* ChromeDriver
* SadTalker (installed separately)
* Browser automation supported TTS platform (Speechma.io)

---

## 📌 Notes

* This tool was built due to resource limitations (e.g., 8GB RAM systems). Otherwise, cloud APIs and asynchronous pipelines would be ideal.
* For now, the pipeline is desktop-based and designed for offline use with local resources.
* All modules are orchestrated via Python for ease of control and customization.

---


