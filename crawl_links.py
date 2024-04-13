import sys
from time import sleep

from icecream import ic

from _db import Database
from crawler import Crawler
from settings import CONFIG
from telegram_noti import send_direct_message

LINKS = [
    # links
    "https://trumtruyen.vn/vo-nho-cuoi-cung-em-da-lon/",
    "https://trumtruyen.vn/co-vo-dang-gom-cua-lang-thieu/",
]


def main():
    _crawler = Crawler()

    try:
        is_trumtruyen_domain_work = _crawler.is_trumtruyen_domain_work()
        if not is_trumtruyen_domain_work:
            send_direct_message(msg="Trumtruyen domain might be changed!!!")
            sys.exit(1)

        for link in LINKS:
            _crawler.crawl_comic(href=link)
    except Exception as e:
        ic(e)


if __name__ == "__main__":
    main()
