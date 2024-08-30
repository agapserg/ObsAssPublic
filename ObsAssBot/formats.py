from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

def list_formats(url):
    ydl_opts = {
        'listformats': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.extract_info(url, download=False)
        except DownloadError as e:
            print(f"DownloadError: {e}")

# Пример использования
url = "https://youtube.com/shorts/W6w8A5bc134"
list_formats(url)