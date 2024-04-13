import json
import logging
import re
import sys
from pathlib import Path
from time import sleep

import requests
from bs4 import BeautifulSoup
from slugify import slugify

from chapter import _chapter
from comic import _comic
from helper import helper
from nuitruyen import Nuitruyen
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Crawler:
    def __init__(self) -> None:
        self._nuitruyen = Nuitruyen()

    def crawl_chapter(
        self,
        comic_title: int,
        comic_id: int,
        comic_slug: str,
        chapter_name: str,
        chapter_href: str,
    ) -> None:
        soup = helper.crawl_soup(chapter_href)
        chapter_content = ""
        for _ in range(3):
            try:
                chapter_content = _chapter.get_chapter_content(
                    chapter_name=chapter_name, soup=soup
                )
                if chapter_content:
                    break
            except Exception as e:
                sleep(5)

        if not chapter_content:
            return

        for watermark, watermark_replacement in CONFIG.WATERMARK_REPLACEMENTS.items():
            chapter_content = chapter_content.replace(watermark, watermark_replacement)

        # if CONFIG.DEBUG:
        #     chapter_post_slug = _chapter.get_chapter_slug(
        #         comic_id=comic_id, chapter_name=chapter_name
        #     )

        else:
            self._nuitruyen.get_or_insert_chapter(
                comic_id=comic_id,
                chapter_name=chapter_name,
                content=chapter_content,
            )

        if CONFIG.DEBUG:
            logging.info(f"Inserted {chapter_name}")

    def crawl_comic(self, href: str):
        soup = helper.crawl_soup(href)
        comic_details = _comic.get_comic_details(href=href, soup=soup)
        if CONFIG.DEBUG:
            with open("json/comic.json", "w") as f:
                f.write(json.dumps(comic_details, indent=4, ensure_ascii=False))

        comic_id = self._nuitruyen.get_or_insert_comic(comic_details)
        if CONFIG.DEBUG:
            logging.info(f"Got (or inserted) comic: {comic_id}")

        if not comic_id:
            if CONFIG.DEBUG:
                logging.error(f"Cannot crawl comic with: {href}")
            return

        chapters = comic_details.get("chapters", {})
        chapters_name = list(chapters.keys())
        if CONFIG.DEBUG:
            chapters_name = chapters_name[:5]

        # chapters_name = chapters_name[::-1]

        inserted_chapters_slug = self._nuitruyen.get_backend_chapters_slug(comic_id)

        for chapter_name in chapters_name:
            chapter_href = chapters.get(chapter_name)
            chapter_slug = _chapter.get_chapter_slug(
                comic_id=comic_id, chapter_name=chapter_name
            )
            if chapter_slug in inserted_chapters_slug:
                continue

            self.crawl_chapter(
                comic_title=comic_details.get("title"),
                comic_id=comic_id,
                comic_slug=comic_details.get("slug"),
                chapter_name=chapter_name,
                chapter_href=chapter_href,
            )
            sleep(1)

    def crawl_item(self, row: BeautifulSoup):
        try:
            truyen_title = row.find("h3", class_="truyen-title")
            href = truyen_title.find("a").get("href")
        except:
            href = ""

        if not href:
            if CONFIG.DEBUG:
                logging.error("[-] Could not find href for item")
            return

        self.crawl_comic(href=href)

    def crawl_page(self, page: int = 1):
        url = f"{CONFIG.TRUMTRUYEN_UPDATE_PAGE}/trang-{page}/"
        soup = helper.crawl_soup(url)

        list_page = soup.find("div", {"id": "list-page"})
        if not list_page:
            return 0

        rows = list_page.find_all("div", class_="row")

        for row in rows:
            self.crawl_item(row=row)
            if CONFIG.DEBUG:
                break

        return 1

    def get_trumtruyen_last_page(self):
        url = f"{CONFIG.TRUMTRUYEN_UPDATE_PAGE}/trang-1/"
        soup = helper.crawl_soup(url)

        try:
            pagination = soup.find("ul", class_="pagination")
            lis = pagination.find_all("li")
            last_li = lis[-2]
            a = last_li.find("a")
            href = a.get("href")
            pattern = re.compile(r"trang-(\d+)")
            matches = pattern.search(href)
            page = matches.group(1)
            return int(page)
        except:
            return CONFIG.TRUMTRUYEN_LAST_PAGE

    def is_trumtruyen_domain_work(self):
        for _ in range(5):
            try:
                response = helper.download_url(CONFIG.TRUMTRUYEN_UPDATE_PAGE)
                if response.status_code == 200:
                    return True

            except Exception as e:
                pass

            sleep(5)

        return False
