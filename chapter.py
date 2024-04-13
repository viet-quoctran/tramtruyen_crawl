from bs4 import BeautifulSoup
from slugify import slugify


class Chapter:
    def get_chapter_slug(self, comic_id: int, chapter_name: str) -> str:
        chapter_slug = f"{chapter_name}"
        return slugify(chapter_slug)

    def get_chapter_content(self, chapter_name: str, soup: BeautifulSoup) -> dict:
        chapter_c = soup.find("div", {"id": "chapter-c"})
        if not chapter_c:
            return ""

        pretty = chapter_c.prettify()
        pretty = pretty.replace("<br>", "\n")

        chapter_c_soup = BeautifulSoup(pretty, "html.parser")
        return chapter_c_soup.get_text().strip("\n").strip()

    def get_chapter_detail(self, chapter_name: str, soup: BeautifulSoup) -> dict:
        result = {}

        ctl00_divCenter = soup.find("div", {"id": "ctl00_divCenter"})
        if not ctl00_divCenter:
            return result

        page_chapters = ctl00_divCenter.find_all("div", class_="page-chapter")
        for index, page_chapter in enumerate(page_chapters):
            img = page_chapter.find("img")
            if not img:
                continue

            img_alt = img.get("alt")
            img_src = img.get("src")
            img_data_index = img.get("data-index")

            if not img_src:
                continue

            if not img_data_index:
                img_data_index = index

            if not img_src.startswith("https:"):
                img_src = "https:" + img_src

            result[img_data_index] = {
                "alt": img_alt,
                "src": img_src,
            }

        return result


_chapter = Chapter()
