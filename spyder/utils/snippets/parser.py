# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
LL(1) predictive parser for snippets CFG grammar.

Aho, Sethi, Ullman
Compilers: Principles, Techniques, and Tools, Addison-Wesley, 1986
"""

# The following grammar extracts snippets from a given text, regardless of the
# programming language used.

GRAMMAR = """
START -> EXPRLIST
EXPRLIST -> EXPR MOREEXPR
MOREEXPR -> EXPR MOREEXPR | EPSILON

EXPR -> SNIPPET | ANY
TEXT_SNIPPETS -> MOREEXPR

TEXT -> ANY MOREANY
MOREANY -> ANY MOREANY | EPSILON

TEXT_NO_COL -> ANY_NO_COL MORE_ANY_NO_COL
MORE_ANY_NO_COL -> ANY_NO_COL MORE_ANY_NO_COL | EPSILON

TEXT_COL -> ANY_COL MORE_COL
MORE_COL -> ANY_COL MORE_COL | EPSILON

TEXT_REGEX -> ANY_REGEX MORE_REGEX
MORE_REGEX -> ANY_REGEX MORE_REGEX | EPSILON

TEXT_FORMAT -> ANY FOLLOW_ANY
FOLLOW_ANY -> ANY FOLLOW_ANY | EPSILON

ANY_REGEX -> ANY | dollar

ANY -> ANY_COL | ,
ANY_COL -> ANY_NO_COL | COLONS
ANY_NO_COL -> name | int | case | SYMBOLS | whitespace | left_curly_name
COLONS -> : | :+ | :- | :?
SYMBOLS ->  \\: | \\$ | text_pipe | { | \\} | \\ | \\/ | \\, | symbol

SNIPPET -> dollar SNIPPETBODY
SNIPPETBODY -> SNIPPETID | INTSNIPPET | VARSNIPPET

INTSNIPPET -> int | { int INTSNIPPETBODY }
INTSNIPPETBODY -> COLONBODY | PIPEBODY | EPSILON
COLONBODY -> : TEXT_SNIPPETS
PIPEBODY -> pipe TEXTSEQ pipe

TEXTSEQ -> TEXT_COL MORETEXT
MORETEXT -> , TEXT_COL MORETEXT | EPSILON

VARSNIPPET -> left_curly_name VARSNIPPETBODY } | name
VARSNIPPETBODY -> COLONBODY | REGEXBODY | EPSILON
REGEXBODY -> / REGEX / FORMATTEXT / OPTIONS

REGEX -> TEXT_REGEX | EPSILON
OPTIONS -> TEXT_REGEX | EPSILON

FORMATTEXT -> FORMAT MOREFORMAT
MOREFORMAT -> FORMAT MOREFORMAT | EPSILON
FORMAT -> FORMATEXPR | TEXT_FORMAT

FORMATTEXT_NO_COL -> FORMAT_NO_COL MOREFORMAT_NO_COL
MOREFORMAT_NO_COL -> FORMAT_NO_COL MOREFORMAT_NO_COL | EPSILON
FORMAT_NO_COL -> FORMATEXPR | TEXT_NO_COL

FORMATEXPR -> dollar FORMATBODY

FORMATBODY -> int | { int FORMATOPTIONS }
FORMATOPTIONS -> CASEOPTS | IFOPTS | IFELSEOPTS | ELSEOPTS | EPSILON

CASEOPTS -> : FORMATTEXT
IFOPTS -> :+ FORMATTEXT
IFELSEOPTS -> :? FORMATTEXT_NO_COL : FORMATTEXT
ELSEOPTS -> PROLOGFUNCT FORMATTEXT
PROLOGFUNCT -> : | :-
"""


def _preprocess_grammar(grammar):
    grammar_lines = grammar.strip().splitlines()
    grammar_lines = [line.strip() for line in grammar_lines if line != '']
    grammar = {}
    for line in grammar_lines:
        production_name, rules = line.split(' -> ')
        rules = rules.split(' | ')
        productions = []
        for rule in rules:
            rule_parts = rule.strip().split()
            productions.append(rule_parts)
        grammar[production_name] = productions
    return grammar


def create_LL1_parsing_table(grammar=GRAMMAR, starting_rule='START'):
    """Create LL(1) parsing table for a given grammar."""
    grammar = _preprocess_grammar(grammar)
    fne = first_no_epsilon(grammar)
    first = {}
    for rule in fne:
        first[rule] = list(set([i[1] for i in fne[rule]]))
    follow_rules = follow(grammar, first, starting_rule)
    parse_table = {}
    for rule in fne:
        parse_table[rule] = {}
        for _, sym, production in fne[rule]:
            if sym != 'EPSILON':
                parse_table[rule][sym] = production
            else:
                for follow_sym in follow_rules[rule]:
                    parse_table[rule][follow_sym] = []
    return grammar, fne, follow_rules, parse_table


def first_no_epsilon(grammar):
    """Compute FIRST sets for all grammar rules."""
    fne = {}
    for rule in grammar:
        fne = first(grammar, rule, fne)
    return fne


def first(grammar, rule, fne):
    """
    Compute FIRST set for a given rule.

    The first set of a sequence of symbols u, written as First(u) is the set
    of terminals which start the sequences of symbols derivable from u.
    A bit more formally, consider all strings derivable from u. If u =>* v,
    where v begins with some terminal, that terminal is in First(u).
    If u =>* epsilon, then epsilon is in First(u).
    """
    first_set = []
    if rule not in fne:
        for productions in grammar[rule]:
            epsilon_found = True
            for production in productions:
                if production not in grammar:
                    # Terminal symbol
                    first_set.append((rule, production, productions))
                    epsilon_found = False
                    break
                else:
                    # Further productions
                    first_production = productions[0]
                    fne = first(grammar, production, fne)
                    num_epsilon = 0
                    for _, sym, _ in fne[first_production]:
                        if sym != 'EPSILON':
                            first_set.append((rule, sym, productions))
                        else:
                            num_epsilon += 1
                    if num_epsilon == 0:
                        epsilon_found = False
                        break
            if epsilon_found:
                first_set.append((rule, 'EPSILON', productions))
        fne[rule] = first_set
    return fne


def follow(grammar, fne, starting_rule):
    """Compute FOLLOW sets for all grammar rules."""
    follow = {}
    position = {}
    follow[starting_rule] = ['<eof>']
    for rule1 in grammar:
        rule1_position = []
        for rule2 in grammar:
            if rule1 == rule2:
                continue
            for i, productions in enumerate(grammar[rule2]):
                for j, production in enumerate(productions):
                    if production == rule1:
                        rule1_position.append((rule2, i, j))
        position[rule1] = rule1_position

    for rule in grammar:
        follow = _follow(grammar, fne, rule, follow, position, starting_rule)
    return follow


def _follow(grammar, fne, rule, follow, position, starting_rule):
    """
    Compute FOLLOW set for a grammar rule.

    The follow set of a nonterminal A is the set of terminal symbols that can
    appear immediately to the right of A in a valid sentence.
    A bit more formally, for every valid sentence S =>* uAv, where v begins
    with some terminal, and that terminal is in Follow(A).
    """
    rule_follow = []

    if rule not in follow or rule == starting_rule:
        if rule == starting_rule:
            rule_follow = follow[rule]
        for derived_rule, i, j in position[rule]:
            production = grammar[derived_rule][i]
            if j < len(production) - 1:
                next_rule = production[j + 1]
                if next_rule in grammar:
                    next_rule_first = [x for x in fne[next_rule]
                                       if x != 'EPSILON']
                    rule_follow += next_rule_first
                    if 'EPSILON' in fne[next_rule]:
                        follow = _follow(grammar, fne, derived_rule,
                                         follow, position, starting_rule)
                        rule_follow += follow[derived_rule]
                else:
                    rule_follow.append(next_rule)
            else:
                follow = _follow(grammar, fne, derived_rule,
                                 follow, position, starting_rule)
                rule_follow += follow[derived_rule]
        follow[rule] = list(set(rule_follow))
    return follow
