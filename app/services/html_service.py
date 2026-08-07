from bs4 import BeautifulSoup


class HtmlService:

    @staticmethod
    def soup(html):

        return BeautifulSoup(

            html,

            "lxml"

        )

    @staticmethod
    def text(node):

        if node is None:

            return ""

        return node.get_text(

            " ",

            strip=True

        )

    @staticmethod
    def attr(node, attr):

        if node is None:

            return ""

        return node.get(attr, "")

    @staticmethod
    def exists(node):

        return node is not None