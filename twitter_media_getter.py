import logging
import os
import uuid
from contextlib import asynccontextmanager

import aiofiles
import aiohttp
import re

from aiogram.types import InputMediaVideo, FSInputFile, InputMediaPhoto
logging.basicConfig(level=logging.INFO)


async def get_links(url: str):
    """
    Takes a standard x.com/twitter.com URL, fetches data from vxtwitter API,
    and returns a list of dictionaries with 'type' and 'url'.
    """
    # 1. Convert URL to api.vxtwitter.com
    # Replace x.com or twitter.com with api.vxtwitter.com
    api_url = re.sub(r"(twitter\.com|x\.com)", "api.vxtwitter.com", url)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()

            if "media_extended" not in data or not data["media_extended"]:
                return None
            logging.info(data)
            results = []
            caption = data.get("text", "")
            for media in data["media_extended"]:
                media_type = media.get("type")
                media_url = media.get("url")
                logging.info(media)
                logging.info(media_type)
                logging.info(media_url)
                if media_type == "image":
                    results.append({"is_video": False, "url": media_url})
                elif media_type == "video" or media_type == "gif":
                    results.append({"is_video": True, "url": media_url})
            print(results)
            return {
                "captions": caption,
                "media_list": results
            }


async def download_file(url):
    async with aiohttp.ClientSession() as session:
        fname = f"temp_{str(uuid.uuid4())}"
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(fname, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        await f.write(chunk)

        return fname

@asynccontextmanager
async def get_media(url):
    global is_session_loaded
    filenames = []
    result_data = {}
    try:
        posts = await get_links(url)
        if not result_data:
            captions = posts.get("captions", "")
            media_urls = posts.get("media_list", [])
            media_group = []

            for item in media_urls:
                file_path = await download_file(item["url"])
                filenames.append(file_path)
                if item["is_video"]:
                    media = InputMediaVideo(media=FSInputFile(file_path))
                else:
                    media = InputMediaPhoto(media=FSInputFile(file_path))
                media_group.append(media)

            result_data = {
                "media": media_group,
                "captions": captions
            }

    except Exception as e:
        result_data = {"error": f"Error during processing: {e}"}

    try:
        yield result_data
    finally:
        for fname in filenames:
            if os.path.exists(fname):
                try:
                    os.remove(fname)
                except OSError:
                    pass