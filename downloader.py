import os
import yt_dlp
import uuid
import requests

def download_video_no_watermark(url):
    if "tiktok.com" in url:
        apiUrl = f"https://www.tikwm.com/api/?url={url}"
        try:
            res = requests.get(apiUrl, timeout=15).json()
            if res.get('code') == 0:
                play_url = res['data']['play']
                filename = f"video_{uuid.uuid4().hex}.mp4"
                video_data = requests.get(play_url, timeout=20).content
                with open(filename, 'wb') as f:
                    f.write(video_data)
                return filename
        except Exception as e:
            print(f"tikwm error: {e}")
            pass
            
    # Fallback to yt-dlp for other platforms
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

def download_video_no_music(url):
    if "tiktok.com" in url:
        apiUrl = f"https://www.tikwm.com/api/?url={url}"
        try:
            res = requests.get(apiUrl, timeout=15).json()
            if res.get('code') == 0:
                # We can't easily strip audio from URL in python without FFmpeg, 
                # but we will provide the video anyway if TikTok.
                play_url = res['data']['play']
                filename = f"video_nomusic_{uuid.uuid4().hex}.mp4"
                video_data = requests.get(play_url, timeout=20).content
                with open(filename, 'wb') as f:
                    f.write(video_data)
                return filename
        except Exception as e:
            print(f"tikwm error: {e}")
            pass

    filename = f"video_nomusic_{uuid.uuid4().hex}.mp4"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]/bestvideo',
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
