# -*- coding: utf-8 -*-
# Standard library imports
import re


class RuleIgnorer(object):
    """Class for insert lint rules ignores automatically."""

    __base_ignore_comment = '# pylint: disable='

    def __init__(self, code_editor):
        """Initialize and Add code_editor to the variable."""
        self.__code_editor = code_editor

    def __is_function_or_class_definition(self):
        text_at_line = self.__code_editor.get_text('sol', 'eol').strip()
        return text_at_line.startswith('def') or text_at_line.startswith('class')

    def __exist_other_ignored_rules(self, line_number):
        self.__code_editor.go_to_line(line_number)
        return self.__code_editor.get_text('sol', 'eol').strip().startswith(self.__base_ignore_comment)

    def __calculate_line_number_for_comment(self, line_number):
        self.__code_editor.go_to_line(line_number)
        if self.__is_function_or_class_definition():
            return line_number + 1
        else:
            if self.__exist_other_ignored_rules(line_number - 1):
                return line_number - 1
            else:
                return line_number

    def __add_new_rule(self, rule_id):
        indentation = self.__get_text_indentation(self.__code_editor.get_text('sol', 'eol'))
        ignore_comment = f"{indentation}{self.__base_ignore_comment} {rule_id}\n"
        self.__code_editor.insert_text(ignore_comment)

    def __add_rule_to_existent(self, rule_id):
        text_at_line = self.__code_editor.get_text('sol', 'eol')
        ignore_comment = f"{text_at_line.rstrip()}, {rule_id}"
        self.__code_editor.text_helper.remove_line_under_cursor()
        self.__code_editor.insert_text(ignore_comment)

    @staticmethod
    def __get_text_indentation(text):
        return re.match(r'(\s*)', text).group(1)

    def ignore_rule_in_line(self, rule_id, line_number):
        """Write the ignored rule id in the line number or add it if there are existent rules"""
        if self.__exist_other_ignored_rules(self.__calculate_line_number_for_comment(line_number)):
            self.__add_rule_to_existent(rule_id)
        else:
            self.__add_new_rule(rule_id)
