import re

from bs4 import BeautifulSoup
from slugify import slugify

from helper import helper
from settings import CONFIG
from time import sleep
import time
from urllib.parse import urlparse
class Comic:
    def get_title(self, item_detail: BeautifulSoup) -> str:
        title = item_detail.find("h3", class_="title")
        if not title:
            return ""

        return title.text.strip()

    def get_cover_url(self, item_detail: BeautifulSoup) -> str:
        try:
            books = item_detail.find("div", class_="books")
            img = books.find("img")

            cover_url = img.get("data-cfsrc", "")
            if not cover_url:
                cover_url = img.get("src", "")

            if cover_url and not cover_url.startswith("https://"):
                cover_url = "https://" + cover_url

            cover_url = cover_url.replace("////", "//")
        except:
            cover_url = ""

        return cover_url

    def get_list_info(self, item_detail: BeautifulSoup) -> dict:
        result = {}
        info = item_detail.find("div", class_="info")
        if info:
            divs = info.find_all("div")
            for div in divs:
                b = div.find("b")
                if not b:
                    continue

                key = slugify(b.text)
                value = div.text.replace(b.text, "").strip()
                if value:
                    result[key] = value

        rate = item_detail.find("div", class_="rate")
        if rate:
            ratingValue = rate.find("span", {"itemprop": "ratingValue"})
            ratingCount = rate.find("span", {"itemprop": "ratingCount"})

            if ratingValue and ratingCount:
                result["ratingValue"] = ratingValue.text
                result["ratingCount"] = ratingCount.text
        return result

    def get_description(self, item_detail: BeautifulSoup) -> str:
        summary = item_detail.find("div", class_="desc-text")
        if not summary:
            return ""

        return str(summary)
        return summary.text

    def get_chapters_from_soup(self, soup: BeautifulSoup) -> dict:
        list_chapter = soup.find("div", {"id": "list-chapter"})
        if not list_chapter:
            return {}

        result = {}

        uls = list_chapter.find_all("ul", class_="list-chapter")
        for ul in uls:
            lis = ul.find_all("li")
            for li in lis:
                a = li.find("a")
                if not a:
                    continue

                chapter_name = li.text.strip()
                href = a.get("href")
                if href:
                    result[chapter_name] = href

        return result

    def get_last_chapter_page(self, soup: BeautifulSoup) -> int:
        last_page = 0

        try:
            pagination = soup.find("ul", class_="pagination")
            lis = pagination.find_all("li")
            for li in lis:
                try:
                    a = li.find("a")
                    href = a.get("href")
                    pattern = re.compile(r"trang-(\d+)")
                    matches = pattern.search(href)

                    page = int(matches.group(1))
                    if page > last_page:
                        last_page = page

                except:
                    pass
        except:
            pass

        print(f"{last_page = }")
        return last_page

    def get_chapters_href(self, soup: BeautifulSoup, story_href: str) -> dict:
        chapters_dict = self.get_chapters_from_soup(soup=soup)
        chapter_last_page = self.get_last_chapter_page(soup=soup)

        for chapter_page in range(2, chapter_last_page + 1):
            url = f"{story_href}/trang-{chapter_page}/#list-chapter"
            soup = helper.crawl_soup(url)
            chapters_dict.update(self.get_chapters_from_soup(soup=soup))
        return chapters_dict

    def format_slug(self, href: str) -> str:
        slug = href.strip().strip("/").split("/")[-1]
        return slug
        slug_splitted = slug.split("-")
        if slug_splitted[-1].isdigit():
            slug_splitted = slug_splitted[:-1]

        return "-".join(slug_splitted)
    
    def crawl_category_page(self, category_href, href, page: int = 1):
        if self.find_event.is_set():
            return
        url = f"{category_href}trang-{page}/"
        soup = helper.crawl_soup(url)
        titles_to_hrefs = {}
        attempts = 0
        while attempts < 3:  # Thử tối đa 3 lần
            list_page = soup.find("div", {"id": "list-page"})
            if list_page:
                break  # Nếu tìm thấy list_page, thoát khỏi vòng lặp
            else:
                print(f"List page not found, retrying in 1 second... Attempt {attempts + 1}")
                time.sleep(1)  # Đợi 1 giây trước khi thử lại
                soup = helper.crawl_soup(url)  # Lấy lại soup sau khi đợi
                attempts += 1

        if not list_page:
            print("Failed to find list page after 3 attempts.")
            return False

        rows = list_page.find_all("div", class_="row")
        for row in rows:
            truyen_title = row.find("h3", class_="truyen-title")
            if truyen_title:
                link = truyen_title.find('a')
                title = link.text.strip()  # Lấy tiêu đề
                href = link['href']  # Lấy href
                # Cập nhật vào từ điển, giả sử mỗi tiêu đề là duy nhất
                if title in titles_to_hrefs:
                    titles_to_hrefs[title] += ',' + href
                else:
                    titles_to_hrefs[title] = href
        return titles_to_hrefs

    def get_category_and_slug(self, soup: BeautifulSoup) -> tuple:
        dropdown_menu = soup.find('ul', class_='dropdown-menu')
        if not dropdown_menu:
            print("Dropdown menu not found.")
            return "", ""

        link = dropdown_menu.find('a')
        if link:
            title = link.get('title', "")
            href = link.get('href', "")
            slug = urlparse(href).path.strip('/').split('/')[-1]
            return title, slug
        else:
            return "", ""
    def get_comic_details(self, href: str, soup: BeautifulSoup) -> dict:
        col_info_desc = soup.find("div", class_="col-info-desc")
        if not col_info_desc:
            return {}

        title = self.get_title(item_detail=col_info_desc)
        slug = self.format_slug(href=href)
        description = self.get_description(item_detail=col_info_desc)

        info_holder = col_info_desc.find("div", class_="info-holder")

        cover_url = self.get_cover_url(item_detail=info_holder)
        detail_list_info = self.get_list_info(item_detail=info_holder)
        chapters_dict = self.get_chapters_href(soup=soup, story_href=href)
        category, slug_category = self.get_category_and_slug(soup)
        return {
            "title": title,
            "slug": slug,
            "cover_url": cover_url,
            "description": description,
            "info":detail_list_info,
            "chapters": chapters_dict,
            "category": category,
            "slug_category": slug_category
        }


_comic = Comic()
