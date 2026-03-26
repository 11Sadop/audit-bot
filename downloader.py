import os
import yt_dlp
import uuid

def download_video_no_watermark(url):
    filename = f"video_{uuid.uuid4().hex}.mp4"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            if os.path.exists(filename):
                return filename
            return None
    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None
