import sys
from time import sleep

from icecream import ic

from _db import Database
from crawler import Crawler
from settings import CONFIG
from telegram_noti import send_direct_message


def main():
    _crawler = Crawler()

    try:
        is_trumtruyen_domain_work = _crawler.is_trumtruyen_domain_work()
        if not is_trumtruyen_domain_work:
            send_direct_message(msg="Trumtruyen domain might be changed!!!")
            sys.exit(1)
        ic("Crawling page 1...")
        _crawler.crawl_page(page=1)
    except Exception as e:
        ic(e)


if __name__ == "__main__":
    while True:
        main()
        sleep(CONFIG.WAIT_BETWEEN_LATEST)
