# filepath: c:\Users\User\Desktop\simple-lyrics-extraction-and-subtitle-website\simple_scrawl.py
"""
簡易歌詞爬蟲模組：從免費歌詞網站爬取歌詞
只使用基本 Python 套件，減少依賴性
"""
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, List, Union


class SimpleLyricsCrawler:
    """簡易歌詞爬蟲基礎類別"""

    def __init__(self):
        """初始化爬蟲"""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _make_request(self, url: str) -> Optional[str]:
        """發送 HTTP 請求並取得回應內容"""
        try:
            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.text()
        except Exception as e:
            print(f"請求錯誤 ({url}): {e}")
            return None

    def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋歌詞（需在子類別中實現）"""
        raise NotImplementedError("搜尋方法需在子類別中實現")

    def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """透過URL取得歌詞（需在子類別中實現）"""
        raise NotImplementedError("取得歌詞方法需在子類別中實現")

    def format_lyrics(self, raw_lyrics: str) -> Dict[str, Any]:
        """格式化歌詞文本為JSON格式"""
        lines = raw_lyrics.strip().split('\n')
        result = {
            "lyrics": raw_lyrics,
            "lines": []
        }

        # 簡單處理，將每行作為一個單位並賦予預設時間
        for i, line in enumerate(lines):
            if line.strip():  # 忽略空行
                result["lines"].append({
                    "text": line.strip(),
                    "start": i * 3,  # 預設每行3秒
                    "end": (i + 1) * 3
                })

        return result


class AZLyricsCrawler(SimpleLyricsCrawler):
    """AZLyrics 英文歌詞網站爬蟲"""

    def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋 AZLyrics 歌詞"""
        if not artist:
            print("AZLyrics 需要提供歌手名稱")
            return None

        # AZLyrics 的 URL 模式是 artist 名和歌曲名都轉小寫並移除特殊字元
        artist_name = re.sub(r'[^\w]', '', artist.lower())
        song_title = re.sub(r'[^\w]', '', song_name.lower())

        # 嘗試直接使用 URL 模式
        url = f"https://www.azlyrics.com/lyrics/{artist_name}/{song_title}.html"

        return self.get_lyrics_by_url(url)

    def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """從 AZLyrics 網頁取得歌詞"""
        html = self._make_request(url)
        if not html:
            return None

        try:
            # AZLyrics 的歌詞在 <!-- 和 --> 注釋中間
            lyrics_pattern = re.compile(
                r'<!-- Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->(.*?)<!-- MxM banner -->', re.DOTALL)
            match = lyrics_pattern.search(html)

            if not match:
                return None

            raw_lyrics = match.group(1).strip()
            # 清理 HTML 標籤
            raw_lyrics = re.sub(r'<.*?>', '', raw_lyrics)
            # 清理多餘空白行
            raw_lyrics = re.sub(r'\n\s*\n', '\n\n', raw_lyrics).strip()

            # 取得歌曲標題
            title_pattern = re.compile(
                r'<title>(.*?) Lyrics \| AZLyrics.com</title>')
            title_match = title_pattern.search(html)
            title = title_match.group(1) if title_match else "未知歌曲"

            # 格式化歌詞
            lyrics_json = self.format_lyrics(raw_lyrics)

            # 添加歌曲資訊
            lyrics_json["title"] = title
            lyrics_json["source"] = "AZLyrics"
            lyrics_json["url"] = url

            return lyrics_json

        except Exception as e:
            print(f"解析 AZLyrics 錯誤: {e}")
            return None


class KasitimeCrawler(SimpleLyricsCrawler):
    """歌詞タイム（Kasitime）日文歌詞網站爬蟲"""

    def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋歌詞タイム的歌詞"""
        query = song_name
        if artist:
            query = f"{artist} {song_name}"

        search_url = f"https://www.kasi-time.com/search.php?keyword={urllib.parse.quote(query)}"
        html = self._make_request(search_url)

        if not html:
            return None

        try:
            # 從搜尋結果頁面找出第一個歌詞連結
            song_link_pattern = re.compile(r'<a href="(item-\d+\.html)"')
            match = song_link_pattern.search(html)

            if not match:
                return None

            lyrics_url = f"https://www.kasi-time.com/{match.group(1)}"
            return self.get_lyrics_by_url(lyrics_url)

        except Exception as e:
            print(f"搜尋歌詞タイム錯誤: {e}")
            return None

    def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """從歌詞タイム網頁取得歌詞"""
        html = self._make_request(url)
        if not html:
            return None

        try:
            # 取得歌詞內容
            lyrics_pattern = re.compile(
                r'<div class="lyrics">(.*?)</div>', re.DOTALL)
            match = lyrics_pattern.search(html)

            if not match:
                return None

            raw_lyrics = match.group(1).strip()
            # 清理 HTML 標籤
            raw_lyrics = re.sub(r'<br\s*/?>', '\n', raw_lyrics)
            raw_lyrics = re.sub(r'<.*?>', '', raw_lyrics)

            # 取得歌曲標題和歌手
            title_pattern = re.compile(r'<h1 class="title">(.*?)</h1>')
            artist_pattern = re.compile(r'<p class="artist">(.*?)</p>')

            title_match = title_pattern.search(html)
            artist_match = artist_pattern.search(html)

            title = title_match.group(1) if title_match else "未知歌曲"
            artist = artist_match.group(1) if artist_match else "未知歌手"

            # 格式化歌詞
            lyrics_json = self.format_lyrics(raw_lyrics)

            # 添加歌曲資訊
            lyrics_json["title"] = title
            lyrics_json["artist"] = artist
            lyrics_json["source"] = "歌詞タイム"
            lyrics_json["url"] = url

            return lyrics_json

        except Exception as e:
            print(f"解析歌詞タイム錯誤: {e}")
            return None


class LyricsTranslateCrawler(SimpleLyricsCrawler):
    """LyricsTranslate 多語言歌詞網站爬蟲"""

    def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋 LyricsTranslate 歌詞"""
        query = song_name
        if artist:
            query = f"{artist} {song_name}"

        search_url = f"https://lyricstranslate.com/en/search/node/{urllib.parse.quote(query)}"
        html = self._make_request(search_url)

        if not html:
            return None

        try:
            # 從搜尋結果頁面找出第一個歌詞連結
            song_link_pattern = re.compile(
                r'<a href="(/en/[^"]+?)"[^>]*?class="search-result__title')
            match = song_link_pattern.search(html)

            if not match:
                return None

            lyrics_url = f"https://lyricstranslate.com{match.group(1)}"
            return self.get_lyrics_by_url(lyrics_url)

        except Exception as e:
            print(f"搜尋 LyricsTranslate 錯誤: {e}")
            return None

    def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """從 LyricsTranslate 網頁取得歌詞"""
        html = self._make_request(url)
        if not html:
            return None

        try:
            # 取得歌詞內容
            lyrics_pattern = re.compile(
                r'<div class="ltf">.*?<div>(.*?)</div>', re.DOTALL)
            match = lyrics_pattern.search(html)

            if not match:
                return None

            raw_lyrics = match.group(1).strip()
            # 清理 HTML 標籤
            raw_lyrics = re.sub(r'<br\s*/?>', '\n', raw_lyrics)
            raw_lyrics = re.sub(r'<.*?>', '', raw_lyrics)

            # 取得歌曲標題和歌手
            title_pattern = re.compile(r'<h2 class="title-h2">(.*?)</h2>')
            artist_pattern = re.compile(
                r'<a[^>]*?class="author[^>]*?>(.*?)</a>')

            title_match = title_pattern.search(html)
            artist_match = artist_pattern.search(html)

            title = title_match.group(1) if title_match else "未知歌曲"
            artist = artist_match.group(1) if artist_match else "未知歌手"

            # 格式化歌詞
            lyrics_json = self.format_lyrics(raw_lyrics)

            # 添加歌曲資訊
            lyrics_json["title"] = title
            lyrics_json["artist"] = artist
            lyrics_json["source"] = "LyricsTranslate"
            lyrics_json["url"] = url

            return lyrics_json

        except Exception as e:
            print(f"解析 LyricsTranslate 錯誤: {e}")
            return None


def scrawl_lyrics_multi_sites(song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    從多個網站爬取歌詞，返回第一個成功的結果
    """
    crawlers = [
        KasitimeCrawler(),  # 日文歌詞
        AZLyricsCrawler(),  # 英文歌詞
        LyricsTranslateCrawler()  # 多語言歌詞
    ]

    for crawler in crawlers:
        result = crawler.search_lyrics(song_name, artist)
        if result:
            return result

    return None


def extract_artist_from_title(video_title: str) -> tuple[str, str]:
    """
    從影片標題中提取歌手和歌曲名
    常見格式: "歌手名 - 歌曲名", "歌曲名 - 歌手名", "歌手名「歌曲名」"
    """
    if " - " in video_title:
        parts = video_title.split(" - ", 1)
        # 假設格式為 "歌手 - 歌曲"
        artist, song = parts[0], parts[1]

        # 有些 YouTube 標題是 "歌曲 - 歌手"，嘗試檢測並交換
        if "official" in song.lower() or "mv" in song.lower() or "m/v" in song.lower():
            artist, song = song, artist

        return artist, song

    # 日文格式常用「」包住歌曲名
    match = re.search(r'(.+?)「(.+?)」', video_title)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # 如果無法拆分，返回整個標題作為歌曲名
    return "", video_title


def scrawl_lyrics_http(video_title: str) -> Optional[Dict[str, Any]]:
    """
    從網站爬取歌詞的公開接口，配合 web.py 使用
    """
    # 嘗試從影片標題中提取歌手和歌曲名
    artist, song_name = extract_artist_from_title(video_title)

    # 如果有歌手資訊，優先使用
    if artist:
        result = scrawl_lyrics_multi_sites(song_name, artist)
        if result:
            return result

    # 如果無法提取或搜尋失敗，使用完整標題搜尋
    return scrawl_lyrics_multi_sites(video_title)


# 測試功能
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"搜尋歌詞: {query}")

        artist, song = extract_artist_from_title(query)
        if artist:
            print(f"提取到歌手: {artist}, 歌曲: {song}")

        result = scrawl_lyrics_http(query)

        if result:
            print(f"成功找到歌詞!")
            print(f"標題: {result.get('title')}")
            print(f"來源: {result.get('source')}")
            print(f"連結: {result.get('url')}")
            print("\n歌詞預覽 (前3行):")

            lines = result.get("lines", [])
            for i, line in enumerate(lines[:3]):
                print(f"{i+1}. {line.get('text', '')}")

            # 保存到文件
            with open(f"{song or query}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n歌詞已保存到 {song or query}.json")
        else:
            print("未找到歌詞")
    else:
        print("使用方式: python simple_scrawl.py 歌手名 - 歌曲名")
        print("範例: python simple_scrawl.py 周杰倫 - 告白氣球")
