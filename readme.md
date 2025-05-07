# Simple Lyrics Extraction & Subtitle Website

A tool for extracting, translating lyrics and generating synchronized subtitles from audio sources

## Features:

- **Audio Download**: Utilizes [yt-dlp](https://github.com/yt-dlp/yt-dlp) to download audio from various sources
- **Text Extraction**: Leverages [stable-ts](https://github.com/jianfch/stable-ts) to extract detailed text and lyrics from audio
- **Subtitle Integration**: Presents the extracted text with synchronized subtitles
- **Web Interface**: Provides a user-friendly interface to view and interact with lyrics

## Usage:

1. **Installation**:
  ```bash
  pip install -r requirements.txt
  ```

2. **Running the Application**:
  ```bash
  python -m web.py
  ```
  The application will start a FastAPI server that can be accessed through your browser.

3. **Accessing the Interface**:
  Open your browser and navigate to `http://localhost:8000`