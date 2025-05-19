# filepath: c:\Users\User\Desktop\simple-lyrics-extraction-and-subtitle-website\scrawl.py
"""
歌詞爬蟲模組：從多個免費歌詞網站爬取歌詞
"""
from bs4 import BeautifulSoup, Tag
import re
import urllib.parse
import asyncio
import aiohttp
from typing import Dict, Any, Optional

# 支援的歌詞網站
SUPPORTED_SITES = {
    "mojim": {
        "name": "魔鏡歌詞網",
        "url": "https://mojim.com",
        "search_url": "https://mojim.com/{query}.html?t3"
    },
    "genius": {
        "name": "Genius",
        "url": "https://genius.com",
        "search_url": "https://genius.com/api/search/song?q={query}",
        "needs_api": False
    }
}


class LyricsCrawler:
    """歌詞爬蟲基礎類別"""

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """初始化爬蟲"""
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋歌詞（需在子類別中實現）"""
        raise NotImplementedError("搜尋方法需在子類別中實現")

    async def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """透過URL取得歌詞（需在子類別中實現）"""
        raise NotImplementedError("取得歌詞方法需在子類別中實現")

    async def format_lyrics(self, raw_lyrics: str) -> Dict[str, Any]:
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


class MojimCrawler(LyricsCrawler):
    """魔鏡歌詞網爬蟲"""

    async def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋魔鏡歌詞網"""
        query = song_name
        if artist:
            query = f"{artist} {song_name}"

        search_url = SUPPORTED_SITES["mojim"]["search_url"].format(
            query=urllib.parse.quote(query))

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 找到第一個搜尋結果
                    result = soup.select_one('div.mxsh_ll1 a')
                    if not result:
                        return None

                    lyrics_url = f"{SUPPORTED_SITES['mojim']['url']}{result['href']}"
                    return await self.get_lyrics_by_url(lyrics_url)

        except Exception as e:
            print(f"魔鏡搜尋錯誤: {e}")
            return None

    async def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """從魔鏡網頁取得歌詞"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 取得歌曲資訊
                    title_element = soup.select_one('div.fsZx3')
                    title = title_element.text.strip() if title_element else "未知歌曲"

                    # 取得歌詞內容
                    lyrics_element = soup.select_one('div#fsZx2')
                    if not lyrics_element:
                        return None

                    # 清理歌詞文本
                    raw_lyrics = lyrics_element.get_text('\n').strip()
                    # 移除歌詞備註和方括號註釋
                    raw_lyrics = re.sub(r'\[.*?\]', '', raw_lyrics)

                    # 格式化歌詞
                    lyrics_json = await self.format_lyrics(raw_lyrics)

                    # 添加歌曲資訊
                    lyrics_json["title"] = title
                    lyrics_json["source"] = "魔鏡歌詞網"
                    lyrics_json["url"] = url

                    return lyrics_json

        except Exception as e:
            print(f"取得魔鏡歌詞錯誤: {e}")
            return None


class GeniusCrawler(LyricsCrawler):
    """Genius 歌詞網站爬蟲"""

    async def search_lyrics(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """搜尋 Genius 網站歌詞"""
        query = song_name
        if artist:
            query = f"{artist} {song_name}"

        search_url = SUPPORTED_SITES["genius"]["search_url"].format(
            query=urllib.parse.quote(query))

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    hits = data.get("response", {}).get(
                        "sections", [])[0].get("hits", [])

                    if not hits:
                        return None

                    # 取得第一個搜尋結果的URL
                    lyrics_url = hits[0].get("result", {}).get("url")
                    if not lyrics_url:
                        return None

                    return await self.get_lyrics_by_url(lyrics_url)

        except Exception as e:
            print(f"Genius 搜尋錯誤: {e}")
            return None

    async def get_lyrics_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """從 Genius 網頁取得歌詞"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 取得歌曲標題
                    title_element = soup.select_one(
                        'h1[class*="SongHeader__Title"]')
                    title = title_element.text.strip() if title_element else "未知歌曲"

                    # 取得歌詞內容
                    lyrics_div = soup.find(
                        'div', {'data-lyrics-container': 'true'})
                    if not lyrics_div:
                        return None

                    # 清理 HTML 標籤
                    for br in lyrics_div.find_all('br'):  # type: ignore
                        # 清理 HTML 標籤
                        if isinstance(lyrics_div, Tag):
                            # 將所有<br>標籤替換為換行符
                            for br in lyrics_div.find_all('br'):
                                br.replace_with(soup.new_string('\n'))

                    raw_lyrics = lyrics_div.get_text('\n').strip()
                    lyrics_json = await self.format_lyrics(raw_lyrics)

                    # 添加歌曲資訊
                    lyrics_json["title"] = title
                    lyrics_json["source"] = "Genius"
                    lyrics_json["url"] = url

                    return lyrics_json

        except Exception as e:
            print(f"取得 Genius 歌詞錯誤: {e}")
            return None


async def scrawl_lyrics_multi_sites(song_name: str, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    從多個網站爬取歌詞，返回第一個成功的結果
    """
    crawlers = [
        MojimCrawler(),
        GeniusCrawler()
    ]

    for crawler in crawlers:
        result = await crawler.search_lyrics(song_name, artist)
        if result:
            return result

    return None


async def scrawl_lyrics_http(song_name: str) -> Optional[Dict[str, Any]]:
    """
    從網站爬取歌詞的公開接口，配合 web.py 使用
    """
    # 嘗試從歌名中提取可能的歌手名
    parts = song_name.split(' - ', 1)
    artist = None

    if len(parts) > 1:
        artist = parts[0]
        song_name = parts[1]

    return await scrawl_lyrics_multi_sites(song_name, artist)

# 測試功能


async def test_crawler():
    """測試爬蟲功能"""
    test_song = "告白氣球"
    test_artist = "周杰倫"

    print(f"測試爬取歌詞: {test_song} - {test_artist}")
    lyrics = await scrawl_lyrics_multi_sites(test_song, test_artist)

    if lyrics:
        print(f"成功爬取! 標題: {lyrics.get('title')}, 來源: {lyrics.get('source')}")
        print(f"首幾句歌詞:")
        for i, line in enumerate(lyrics.get("lines", [])[:3]):
            print(f"{i+1}. {line.get('text', '')}")
    else:
        print("未找到歌詞")

if __name__ == "__main__":
    # 測試爬蟲功能
    asyncio.run(test_crawler())
