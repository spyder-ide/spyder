# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
String search and match utilities useful when filtering a list of texts.
"""

import re

from spyder.py3compat import to_text_string

NOT_FOUND_SCORE = -1
NO_SCORE = 0


def get_search_regex(query, ignore_case=True):
    """Returns a compiled regex pattern to search for query letters in order.

    Parameters
    ----------
    query : str
        String to search in another string (in order of character occurrence).
    ignore_case : True
        Optional value perform a case insensitive search (True by default).

    Returns
    -------
    pattern : SRE_Pattern

    Notes
    -----
    This function adds '.*' between the query characters and compiles the
    resulting regular expression.
    """
    regex_text = [char for char in query if char != ' ']
    regex_text = '.*'.join(regex_text)

    regex = u'({0})'.format(regex_text)

    if ignore_case:
        pattern = re.compile(regex, re.IGNORECASE)
    else:
        pattern = re.compile(regex)

    return pattern


def get_search_score(query, choice, ignore_case=True, apply_regex=True,
                     template='{}'):
    """Returns a tuple with the enriched text (if a template is provided) and
    a score for the match.

    Parameters
    ----------
    query : str
        String with letters to search in choice (in order of appearance).
    choice : str
        Sentence/words in which to search for the 'query' letters.
    ignore_case : bool, optional
        Optional value perform a case insensitive search (True by default).
    apply_regex : bool, optional
        Optional value (True by default) to perform a regex search. Useful
        when this function is called directly.
    template : str, optional
        Optional template string to surround letters found in choices. This is
        useful when using a rich text editor ('{}' by default).
        Examples: '<b>{}</b>', '<code>{}</code>', '<i>{}</i>'

    Returns
    -------
    results : tuple
        Tuples where the first item is the text (enriched if a template was
        used) and the second item is a search score.

    Notes
    -----
    The score is given according the following precedence (high to low):

    - Letters in one word and no spaces with exact match.
      Example: 'up' in 'up stroke'
    - Letters in one word and no spaces with partial match.
      Example: 'up' in 'upstream stroke'
    - Letters in one word but with skip letters.
      Example: 'cls' in 'close up'
    - Letters in two or more words
      Example: 'cls' in 'car lost'
    """
    original_choice = to_text_string(choice, encoding='utf-8')
    result = (original_choice, NOT_FOUND_SCORE)

    # Handle empty string case
    if not query:
        return result

    query = to_text_string(query, encoding='utf-8')
    choice = to_text_string(choice, encoding='utf-8')

    if ignore_case:
        query = query.lower()
        choice = choice.lower()

    if apply_regex:
        pattern = get_search_regex(query, ignore_case=ignore_case)
        r = re.search(pattern, choice)
        if r is None:
            return result
    else:
        sep = u'-'  # Matches will be replaced by this character
        let = u'x'  # Nonmatches (except spaed) will be replaced by this
        score = 0

        exact_words = [query == to_text_string(word, encoding='utf-8')
                       for word in choice.split(u' ')]
        partial_words = [query in word for word in choice.split(u' ')]

        if any(exact_words) or any(partial_words):
            pos_start = choice.find(query)
            pos_end = pos_start + len(query)
            score += pos_start
            text = choice.replace(query, sep*len(query), 1)

            enriched_text = original_choice[:pos_start] +\
                template.format(original_choice[pos_start:pos_end]) +\
                original_choice[pos_end:]

        if any(exact_words):
            # Check if the query words exists in a word with exact match
            score += 1
        elif any(partial_words):
            # Check if the query words exists in a word with partial match
            score += 100
        else:
            # Check letter by letter
            text = [l for l in original_choice]
            if ignore_case:
                temp_text = [l.lower() for l in original_choice]
            else:
                temp_text = text[:]

            # Give points to start of string
            score += temp_text.index(query[0])

            # Find the query letters and replace them by `sep`, also apply
            # template as needed for enricching the letters in the text
            enriched_text = text[:]
            for char in query:
                if char != u'' and char in temp_text:
                    index = temp_text.index(char)
                    enriched_text[index] = template.format(text[index])
                    text[index] = sep
                    temp_text = [u' ']*(index + 1) + temp_text[index+1:]

        enriched_text = u''.join(enriched_text)

        patterns_text = []
        for i, char in enumerate(text):
            if char != u' ' and char != sep:
                new_char = let
            else:
                new_char = char
            patterns_text.append(new_char)
        patterns_text = u''.join(patterns_text)
        for i in reversed(range(1, len(query) + 1)):
            score += (len(query) - patterns_text.count(sep*i))*100000

        temp = patterns_text.split(sep)
        while u'' in temp:
            temp.remove(u'')
        if not patterns_text.startswith(sep):
            temp = temp[1:]
        if not patterns_text.endswith(sep):
            temp = temp[:-1]

        for pat in temp:
            score += pat.count(u' ')*10000
            score += pat.count(let)*100

    return original_choice, enriched_text, score


def get_search_scores(query, choices, ignore_case=True, template='{}',
                      valid_only=False, sort=False):
    """Search for query inside choices and return a list of tuples.

    Returns a list of tuples of text with the enriched text (if a template is
    provided) and a score for the match. Lower scores imply a better match.

    Parameters
    ----------
    query : str
        String with letters to search in each choice (in order of appearance).
    choices : list of str
        List of sentences/words in which to search for the 'query' letters.
    ignore_case : bool, optional
        Optional value perform a case insensitive search (True by default).
    template : str, optional
        Optional template string to surround letters found in choices. This is
        useful when using a rich text editor ('{}' by default).
        Examples: '<b>{}</b>', '<code>{}</code>', '<i>{}</i>'

    Returns
    -------
    results : list of tuples
        List of tuples where the first item is the text (enriched if a
        template was used) and a search score. Lower scores means better match.
    """
    # First remove spaces from query
    query = query.replace(' ', '')
    pattern = get_search_regex(query, ignore_case)
    results = []

    for choice in choices:
        r = re.search(pattern, choice)
        if query and r:
            result = get_search_score(query, choice, ignore_case=ignore_case,
                                      apply_regex=False, template=template)
        else:
            if query:
                result = (choice, choice, NOT_FOUND_SCORE)
            else:
                result = (choice, choice, NO_SCORE)

        if valid_only:
            if result[-1] != NOT_FOUND_SCORE:
                results.append(result)
        else:
            results.append(result)

    if sort:
        results = sorted(results, key=lambda row: row[-1])

    return results


def test():
    template = '<b>{0}</b>'
    names = ['close pane', 'debug continue', 'debug exit', 'debug step into',
             'debug step over', 'debug step return', 'fullscreen mode',
             'layout preferences', 'lock unlock panes', 'maximize pane',
             'preferences', 'quit', 'restart', 'save current layout',
             'switch to breakpoints', 'switch to console', 'switch to editor',
             'switch to explorer', 'switch to find_in_files',
             'switch to historylog', 'switch to help',
             'switch to ipython_console', 'switch to onlinehelp',
             'switch to outline_explorer', 'switch to project_explorer',
             'switch to variable_explorer',
             'use next layout', 'use previous layout', 'clear line',
             'clear shell', 'inspect current object', 'blockcomment',
             'breakpoint', 'close all', 'code completion',
             'conditional breakpoint', 'configure', 'copy', 'copy line', 'cut',
             'debug', 'debug with winpdb', 'delete', 'delete line',
             'duplicate line', 'end of document', 'end of line',
             'file list management', 'find next', 'find previous', 'find text',
             'go to definition', 'go to line', 'go to next file',
             'go to previous file', 'inspect current object', 'kill next word',
             'kill previous word', 'kill to line end', 'kill to line start',
             'last edit location', 'move line down', 'move line up',
             'new file', 'next char', 'next cursor position', 'next line',
             'next word', 'open file', 'paste', 'previous char',
             'previous cursor position', 'previous line', 'previous word',
             'print', 're-run last script', 'redo', 'replace text',
             'rotate kill ring', 'run', 'run selection', 'save all', 'save as',
             'save file', 'select all', 'show/hide outline',
             'show/hide project explorer', 'start of document',
             'start of line', 'toggle comment', 'unblockcomment', 'undo',
             'yank', 'run profiler', 'run analysis']

    a = get_search_scores('lay', names, template=template, )
    b = get_search_scores('lay', names, template=template, valid_only=True,
                          sort=True)
    # Full results
    for r in a:
        print(r)  # spyder: test-skip

    # Ordered and filtered results
    print('\n')  # spyder: test-skip

    for r in b:
        print(r)  # spyder: test-skip

if __name__ == '__main__':
    test()
