import logging
import os
import time
from datetime import datetime
from decimal import Decimal

import pytz
from phpserialize import serialize
from PIL import Image
from slugify import slugify

from _db import Database
from chapter import _chapter
from helper import helper
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")


class Nuitruyen:
    def __init__(self) -> None:
        self.database = Database()

    def get_backend_chapters_slug(self, comic_id: int) -> list:
        chapters = self.database.select_all_from(
            table=f"posts",
            condition=f'post_parent="{comic_id}" AND post_type="chapter"',
        )
        chapters_slug = [
            chapter[CONFIG.INSERT["posts"].index("post_name") + 1]
            for chapter in chapters
        ]
        return chapters_slug

    def insert_postmeta(self, postmeta_data: list, table: str = "postmeta"):
        self.database.insert_into(table=table, data=postmeta_data, is_bulk=True)

    def get_timeupdate(self) -> str:
        # TODO: later
        timeupdate = datetime.now(vn_timezone).strftime("%Y/%m/%d %H:%M:%S")

        return timeupdate

    def get_comic_timeupdate(self) -> str:
        # TODO
        return int(time.time())

    def download_and_save_thumb(self, cover_url: str):
        try:
            # Download the cover image
            image_name = cover_url.split("/")[-1]
            thumb_save_path, is_not_saved = helper.save_image(
                image_url=cover_url, image_name=image_name, is_thumb=True
            )

            # return thumb_save_path.replace(CONFIG.IMAGE_SAVE_PATH, CONFIG.CUSTOM_CDN)
            return f"covers/{image_name}", thumb_save_path
        except Exception:
            return CONFIG.DEFAULT_THUMB, thumb_save_path

    def get_wp_attachment_metadata(
        self, saved_thumb_url: str, thumb_save_path: str
    ) -> str:
        if not thumb_save_path:
            return ""

        image = Image.open(thumb_save_path)
        width, height = image.size
        size_in_bytes = os.path.getsize(thumb_save_path)

        _wp_attachment_metadata_dict = {
            "width": width,
            "height": height,
            "file": saved_thumb_url,
            "filesize": size_in_bytes,
            "image_meta": {
                "aperture": "0",
                "credit": "",
                "camera": "",
                "caption": "",
                "created_timestamp": "0",
                "copyright": "",
                "focal_length": "0",
                "iso": "0",
                "shutter_speed": "0",
                "title": "",
                "orientation": "0",
                "keywords": {},
            },
        }
        _wp_attachment_metadata = serialize(_wp_attachment_metadata_dict).decode(
            "utf-8"
        )
        return _wp_attachment_metadata

    def insert_thumb(self, cover_url: str) -> int:
        if not cover_url:
            return 0

        saved_thumb_url, thumb_save_path = self.download_and_save_thumb(
            cover_url=cover_url
        )

        thumb_name = saved_thumb_url.split("/")[-1].split(".")[0]

        timeupdate = self.get_timeupdate()
        thumb_post_data = (
            0,
            timeupdate,
            timeupdate,
            "",
            thumb_name,
            "",
            "inherit",
            "closed",
            "closed",
            "",
            slugify(thumb_name),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "attachment",
            "image/png",
            0,
            # "",
        )

        thumb_id = self.database.insert_into(table="posts", data=thumb_post_data)

        postmeta_data = [
            (thumb_id, "_wp_attached_file", saved_thumb_url),
            (
                thumb_id,
                "_wp_attachment_metadata",
                self.get_wp_attachment_metadata(
                    saved_thumb_url=saved_thumb_url, thumb_save_path=thumb_save_path
                ),
            ),
        ]

        self.insert_postmeta(postmeta_data)
        # self.database.insert_into(
        #     table="postmeta",
        #     data=(thumb_id, "_wp_attached_file", saved_thumb_url),
        # )

        # self.database.insert_into(
        #     table="postmeta",
        #     data=(thumb_id, "_wp_attached_file", saved_thumb_url),
        # )
        return thumb_id

    def insert_terms(
        self,
        post_id: int,
        terms: str,
        descriptions,
        taxonomy: str,
        is_title: str = False,
        term_slug: str = "",
    ):
        try:
            terms = (
                [term.strip() for term in terms.split(",")] if not is_title else [terms]
            )
            if isinstance(descriptions, str):
                descriptions = [descriptions]
            new_terms = dict(zip(terms, descriptions))
        except Exception as e:
            if CONFIG.DEBUG:
                logging.error(f"[-] Error in insert terms: {e}")
            return
        term_ids = []
        for term in new_terms:
            term_insert_slug = slugify(term_slug) if term_slug else slugify(term)
            if term_insert_slug == "truyen-moi-cap-nhat":
                term_insert_slug = "truyen-moi"
            cols = "tt.term_taxonomy_id, tt.term_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.slug = "{term_insert_slug}" AND tt.term_id=t.term_id AND tt.taxonomy="{taxonomy}"'

            query = f"SELECT {cols} FROM {table} WHERE {condition}"

            be_term = self.database.select_with(query=query)
            if not be_term:
                term_id = self.database.insert_into(
                    table="terms",
                    data=(term, term_insert_slug, 0),
                )
                term_taxonomy_count = 1 if taxonomy == "category" else 0
                term_taxonomy_id = self.database.insert_into(
                        table="term_taxonomy",
                        data=(term_id, taxonomy, new_terms[term], 0, term_taxonomy_count),
                    )
                term_ids = [term_taxonomy_id, True]
            else:
                term_taxonomy_id = be_term[0][0]
                term_id = be_term[0][1]
                term_ids = [term_taxonomy_id, False]

            try:
                self.database.insert_into(
                    table="term_relationships",
                    data=(post_id, term_taxonomy_id, 0),
                )
            except:
                pass
        return term_ids

    def get_rating_scores(self, comic_data: dict) -> int:
        ratingCount = comic_data.get("ratingCount", "1")
        ratingValue = comic_data.get("ratingValue", "5")

        try:
            rating_score = float(ratingValue) * float(ratingCount)
            return f"{rating_score:.2f}", ratingCount, ratingValue
        except:
            return "5", "1", "5"

    def insert_comic(self, comic_data: dict):
        thumb_id = self.insert_thumb(comic_data.get("cover_url"))
        timeupdate = self.get_timeupdate()
        description = comic_data.get("description", "")
        for watermark, watermark_replacement in CONFIG.WATERMARK_REPLACEMENTS.items():
            description = description.replace(watermark, watermark_replacement)

        data = (
            1,
            timeupdate,
            timeupdate,
            description,
            comic_data["title"],
            "",
            "publish",
            "open",
            "open",
            "",
            comic_data.get("slug", ""),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "post",
            "",
            0,
        )

        try:
            comic_id = self.database.insert_into(table=f"posts", data=data)
        except Exception as e:
            helper.error_log(
                msg=f"Failed to insert comic\n{e}", filename="helper.comic_id.log"
            )
            return 0
        comic_status = comic_data['info']['trang-thai']
        if comic_status.lower() in ["Hoàn Thành".lower(), "Full".lower()]:
            comic_status = "full"
        else:
            comic_status = "ongoing"

        ratingScore, ratingCount, ratingValue = self.get_rating_scores(
            comic_data=comic_data
        )
        postmeta_data = [
            (comic_id, "_edit_last", "1"),
            (comic_id, "_edit_lock", f"{self.get_comic_timeupdate()}:1"),
            (comic_id, "_thumbnail_id", thumb_id),
            (comic_id,"_comic_status",comic_status,),
            # (comic_id, "tw_multi_chap", "1"),
            # (comic_id, "ratings_users", ratingCount),
            # (comic_id, "ratings_score", ratingScore),
            # (comic_id, "ratings_average", ratingValue),
            # # (comic_id, "_wp_manga_alternative", comic_data.get("ten-khac", "")),
            # # (comic_id, "manga_adult_content", ""),
            # # (comic_id, "manga_title_badges", "no"),
            # (comic_id, "_wp_manga_chapter_type", "text"),
        ]

        self.insert_postmeta(postmeta_data)
        def get_description(url_description):
            soup = helper.crawl_soup(url_description)
            description = soup.find("div", class_="panel-body")
            if not description:
                return ""
            return str(description)
        def get_description_author():
            url_description = f"{CONFIG.AUTHOR}/{slugify(comic_data['info']['tac-gia'])}"
            return get_description(url_description)

        def get_description_tag():
            list_tag = comic_data['info']['the-loai'].split(",")
            descriptions = []  # Tạo một danh sách để giữ các mô tả
            for tag in list_tag:
                url_description = f"{CONFIG.TAG}/{slugify(tag.strip())}"  # Dùng strip() để loại bỏ khoảng trắng
                description = get_description(url_description)
                if description:  # Thêm mô tả vào danh sách nếu có
                    descriptions.append(description)
            return descriptions
        def get_description_category(slug_category):
            url_description = f"{CONFIG.CATEGORY}/{slug_category}"  # Dùng strip() để loại bỏ khoảng trắng
            return get_description(url_description)
        self.insert_terms(
            post_id=comic_id,
            terms=comic_data['info']['tac-gia'],
            descriptions = get_description_author(),
            taxonomy="tac-gia",
        )
        self.insert_terms(
            post_id=comic_id,
            terms=comic_data['info']['the-loai'],
            descriptions = get_description_tag(),
            taxonomy="post_tag",
        )
        self.insert_terms(
            post_id=comic_id,
            terms=comic_data['category'],
            descriptions = get_description_category(comic_data['slug_category']),
            taxonomy="category",
        )
        return comic_id

    def get_or_insert_comic(self, comic_details: dict) -> int:
        if not comic_details.get("slug", ""):
            return 0

        condition = f"""post_name = '{comic_details["slug"]}'"""
        be_post = self.database.select_all_from(table=f"posts", condition=condition)
        if not be_post:
            return self.insert_comic(comic_data=comic_details)
        else:
            return be_post[0][0]

    def get_download_chapter_content(
        self,
        comic_title: str,
        comic_slug: str,
        chapter_details: dict,
        chapter_name: str,
        chapter_href: str,
    ):
        result = ""
        image_numbers = list(chapter_details.keys())
        # sorted(image_numbers, key=lambda x: int(x))

        if CONFIG.DEBUG:
            image_numbers = image_numbers[:5]

        for image_number in image_numbers:
            image_details = chapter_details[image_number]
            image_alt = image_details.get("alt")
            image_src = image_details.get("src")
            saved_image, _ = helper.save_image(
                image_url=image_src,
                comic_seo=comic_slug,
                chap_seo=_chapter.get_chapter_slug(chapter_name=chapter_href),
                image_name=f"{image_number}.jpg",
            )
            if not saved_image:
                continue

            if CONFIG.SAVE_CHAPTER_IMAGES_TO_S3:
                img_src = f"{CONFIG.S3_BUCKET_IMAGE_URL_PREFIX}/{saved_image}"
            else:
                img_src = saved_image.replace(CONFIG.IMAGE_SAVE_PATH, CONFIG.CUSTOM_CDN)
            result += (
                CONFIG.IMAGE_ELEMENT.format(img_src=img_src, img_alt=image_alt) + "\n"
            )

        if result:
            result = (
                CONFIG.CHAPTER_PREFIX.format(
                    comic_name=comic_title,
                    chapter=chapter_name.lower().replace("chapter", "").strip(),
                )
                + result
            )

        return result

    def insert_chapter_content_to_posts(
        self, chapter_id: int, chapter_slug: str, content: str
    ):
        chapter_post_slug = slugify(f"{chapter_id}-{chapter_slug}")
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            content,
            chapter_post_slug,
            "",
            "publish",
            "open",
            "closed",
            "",
            chapter_post_slug,
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            chapter_id,
            "",
            0,
            "chapter_text_content",
            "",
            0,
            "",
        )

        try:
            condition = f"post_name='{chapter_post_slug}'"
            self.database.select_or_insert(
                table="posts", condition=condition, data=data
            )
            # self.database.insert_into(table=f"posts", data=data)
        except Exception as e:
            helper.error_log(
                msg=f"Failed to insert comic\n{e}",
                filename="madara.insert_chapter_content_to_posts.log",
            )
            return 0

    def insert_chapter(
        self,
        comic_id: int,
        chapter_name: str,
        content: str,
    ):
        timeupdate = self.get_timeupdate()

        chapter_slug = _chapter.get_chapter_slug(
            comic_id=comic_id, chapter_name=chapter_name
        )
        if ":" in chapter_name:
            chapter_number = chapter_name.split(":")[0].split()[-1]
        else:
            chapter_number = chapter_name.split()[-1]
        # chapter_slug = "chuong-" + chapter_number.replace("Chương ", "").strip()
        data = (
            1,
            timeupdate,
            timeupdate,
            content,
            chapter_name,
            "",
            "publish",
            "closed",
            "closed",
            "",
            chapter_slug,
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "chapter",
            "",
            0,
        )
        # condition = f"post_parent={comic_id} AND post_name='{chapter_slug}'"
        try:
            chapter_id = self.database.insert_into(table=f"posts", data=data)
        except Exception as e:
            helper.error_log(
                msg=f"Failed to insert chapter\n{e}", filename="helper.chapter_id.log"
            )
            return 0
        postmeta_data = [
            (chapter_id, "_edit_last", "1"),
            (chapter_id, "_edit_lock", f"{self.get_comic_timeupdate()}:1"),
            (chapter_id, "_parent_post_id", comic_id),
            (chapter_id,"_chapter_number",chapter_number,),
        ]
        self.insert_postmeta(postmeta_data)
    def get_or_insert_chapter(
        self,
        comic_id: int,
        chapter_name: str,
        content: str,
    ):
        chapter_post_slug = _chapter.get_chapter_slug(
            comic_id=comic_id, chapter_name=chapter_name
        )
        condition = f"""post_name='{chapter_post_slug}' AND post_type='chapter'"""
        be_post = self.database.select_all_from(table=f"posts", condition=condition)
        if not be_post:
            self.insert_chapter(
                comic_id=comic_id, chapter_name=chapter_name, content=content
            )
