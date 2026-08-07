from app.config.logging_config import configure_logging
from app.crawler.ecommerce_crawler import EcommerceCrawler


def main():

    configure_logging()

    crawler = EcommerceCrawler()

    crawler.run()


if __name__ == "__main__":

    main()
