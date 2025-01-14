# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Style for IPython Console
"""

# Third party imports
from pygments.style import Style
from pygments.token import (
    Name,
    Keyword,
    Comment,
    String,
    Number,
    Punctuation,
    Operator,
)


def create_pygments_dict(color_scheme_dict):
    """
    Create a dictionary that saves the given color scheme as a
    Pygments style.
    """

    def give_font_weight(is_bold):
        if is_bold:
            return "bold"
        else:
            return ""

    def give_font_style(is_italic):
        if is_italic:
            return "italic"
        else:
            return ""

    color_scheme = color_scheme_dict

    fon_c, fon_fw, fon_fs = color_scheme["normal"]
    font_color = fon_c
    font_font_weight = give_font_weight(fon_fw)
    font_font_style = give_font_style(fon_fs)

    key_c, key_fw, key_fs = color_scheme["keyword"]
    keyword_color = key_c
    keyword_font_weight = give_font_weight(key_fw)
    keyword_font_style = give_font_style(key_fs)

    bui_c, bui_fw, bui_fs = color_scheme["builtin"]
    builtin_color = bui_c
    builtin_font_weight = give_font_weight(bui_fw)
    builtin_font_style = give_font_style(bui_fs)

    str_c, str_fw, str_fs = color_scheme["string"]
    string_color = str_c
    string_font_weight = give_font_weight(str_fw)
    string_font_style = give_font_style(str_fs)

    num_c, num_fw, num_fs = color_scheme["number"]
    number_color = num_c
    number_font_weight = give_font_weight(num_fw)
    number_font_style = give_font_style(num_fs)

    com_c, com_fw, com_fs = color_scheme["comment"]
    comment_color = com_c
    comment_font_weight = give_font_weight(com_fw)
    comment_font_style = give_font_style(com_fs)

    def_c, def_fw, def_fs = color_scheme["definition"]
    definition_color = def_c
    definition_font_weight = give_font_weight(def_fw)
    definition_font_style = give_font_style(def_fs)

    ins_c, ins_fw, ins_fs = color_scheme["instance"]
    instance_color = ins_c
    instance_font_weight = give_font_weight(ins_fw)
    instance_font_style = give_font_style(ins_fs)

    font_token = font_font_style + " " + font_font_weight + " " + font_color
    definition_token = (
        definition_font_style
        + " "
        + definition_font_weight
        + " "
        + definition_color
    )
    builtin_token = (
        builtin_font_style + " " + builtin_font_weight + " " + builtin_color
    )
    instance_token = (
        instance_font_style + " " + instance_font_weight + " " + instance_color
    )
    keyword_token = (
        keyword_font_style + " " + keyword_font_weight + " " + keyword_color
    )
    comment_token = (
        comment_font_style + " " + comment_font_weight + " " + comment_color
    )
    string_token = (
        string_font_style + " " + string_font_weight + " " + string_color
    )
    number_token = (
        number_font_style + " " + number_font_weight + " " + number_color
    )

    syntax_style_dic = {
        Name: font_token.strip(),
        Name.Class: definition_token.strip(),
        Name.Function: definition_token.strip(),
        Name.Builtin: builtin_token.strip(),
        Name.Builtin.Pseudo: instance_token.strip(),
        Keyword: keyword_token.strip(),
        Keyword.Type: builtin_token.strip(),
        Comment: comment_token.strip(),
        String: string_token.strip(),
        Number: number_token.strip(),
        Punctuation: font_token.strip(),
        Operator.Word: keyword_token.strip(),
    }

    return syntax_style_dic


def create_style_class(color_scheme_dict):
    """Create a Pygments Style class with the given color scheme."""

    class StyleClass(Style):
        default_style = ""
        styles = create_pygments_dict(color_scheme_dict)

    return StyleClass
