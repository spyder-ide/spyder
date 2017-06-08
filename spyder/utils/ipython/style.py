# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Style for IPython Console
"""
# Standard imports
import os

# Local imports
from spyder.config.gui import get_color_scheme
from spyder.config.main import CONF

# Third party imports
from qtconsole.styles import dark_color

def get_style_sheet():
    """Returns a CSS stylesheet with spyder color scheme settings.

    The stylesheet can contain classes for:
        Qt: QPlainTextEdit, QFrame, QWidget, etc
       Pygments: .c, .k, .o, etc. (see PygmentsHighlighter)
        IPython: .error, .in-prompt, .out-prompt, etc
    """

    def give_font_weight(is_bold):
        if is_bold:
            return 'bold'
        else:
            return 'normal'

    def give_font_style(is_italic):
        if is_italic:
            return 'italic'
        else:
            return 'normal'

    selected_color_scheme = CONF.get('color_schemes', 'selected')
    color_scheme = get_color_scheme(selected_color_scheme)
    fon_c, fon_fw, fon_fs = color_scheme['normal']
    font_color =  fon_c
    if dark_color(font_color):
        in_prompt_color = 'navy'
        out_prompt_color = 'darkred'
    else:
        in_prompt_color = 'lime'
        out_prompt_color = 'red'
    background_color = color_scheme['background']
    selection_background_color = '#ccc'
    error_color = 'red'
    in_prompt_number_font_weight = 'bold'
    out_prompt_number_font_weight = 'bold'
    inverted_background_color = font_color
    inverted_font_color = background_color

    sheet = """QPlainTextEdit, QTextEdit, ControlWidget {{
                                          color: {} ;
                                          background-color: {};
                                          selection-background-color: {}
                                         }}
              .error {{ color: {}; }}
              .in-prompt {{ color: {}; }}
              .in-prompt-number {{ color: {}; font-weight: {}; }}
              .out-prompt {{ color: {}; }}
              .out-prompt-number {{ color: {}; font-weight: {}; }}
              .inverted {{ color: {}; background-color: {}; }}
              """

    sheet_formatted = sheet.format(font_color, background_color,
                                   selection_background_color,
                                   error_color,
                                   in_prompt_color, in_prompt_color,
                                   in_prompt_number_font_weight,
                                   out_prompt_color, out_prompt_color,
                                   out_prompt_number_font_weight,
                                   inverted_background_color,
                                   inverted_font_color)

    return sheet_formatted

def get_syntax_style_dictionary():
    """Create a dictionary to create the syntax style."""

    def give_font_weight(is_bold):
        if is_bold:
            return 'bold'
        else:
            return ''

    def give_font_style(is_italic):
        if is_italic:
            return 'italic'
        else:
            return ''

    selected_color_scheme = CONF.get('color_schemes', 'selected')
    color_scheme = get_color_scheme(selected_color_scheme)

    fon_c, fon_fw, fon_fs = color_scheme['normal']
    font_color =  fon_c
    font_font_weight = give_font_weight(fon_fw)
    font_font_style = give_font_style(fon_fs)
    key_c, key_fw, key_fs = color_scheme['keyword']
    keyword_color =  key_c
    keyword_font_weight = give_font_weight(key_fw)
    keyword_font_style = give_font_style(key_fs)
    bui_c, bui_fw, bui_fs = color_scheme['builtin']
    builtin_color =  bui_c
    builtin_font_weight = give_font_weight(bui_fw)
    builtin_font_style = give_font_style(bui_fs)
    str_c, str_fw, str_fs = color_scheme['string']
    string_color =  str_c
    string_font_weight = give_font_weight(str_fw)
    string_font_style = give_font_style(str_fs)
    num_c, num_fw, num_fs = color_scheme['number']
    number_color =  num_c
    number_font_weight = give_font_weight(num_fw)
    number_font_style = give_font_style(num_fs)
    com_c, com_fw, com_fs = color_scheme['comment']
    comment_color =  com_c
    comment_font_weight = give_font_weight(com_fw)
    comment_font_style = give_font_style(com_fs)
    def_c, def_fw, def_fs = color_scheme['definition']
    definition_color =  def_c
    definition_font_weight = give_font_weight(def_fw)
    definition_font_style = give_font_style(def_fs)
    ins_c, ins_fw, ins_fs = color_scheme['instance']
    instance_color =  ins_c
    instance_font_weight = give_font_weight(ins_fw)
    instance_font_style = give_font_style(ins_fs)

    syntax_style_dic = {}
    syntax_style_dic['Name'] = [font_font_style, font_font_weight,
                                font_color]
    syntax_style_dic['Name.Class'] = [definition_font_style,
                                      definition_font_weight,
                                      definition_color]
    syntax_style_dic['Name.Function'] = [definition_font_style,
                                         definition_font_weight,
                                         definition_color]
    syntax_style_dic['Name.Builtin'] = [builtin_font_style,
                                        builtin_font_weight, builtin_color]
    syntax_style_dic['Name.Builtin.Pseudo'] = [instance_font_style,
                                               instance_font_weight,
                                               instance_color]
    syntax_style_dic['Keyword'] = [keyword_font_style, keyword_font_weight,
                                   keyword_color]
    syntax_style_dic['Keyword.Type'] = [builtin_font_style,
                                        builtin_font_weight, builtin_color]
    syntax_style_dic['Comment'] = [comment_font_style, comment_font_weight,
                                   comment_color]
    syntax_style_dic['String'] = [string_font_style, string_font_weight,
                                  string_color]
    syntax_style_dic['Number'] = [number_font_style, number_font_weight,
                                  number_color]
    syntax_style_dic['Punctuation'] = [font_font_style, font_font_weight,
                                       font_color]

    return syntax_style_dic

def get_syntax_style(name='spyder'):
    """Create a .py with the spyder custom style as a Pygment class.

    The file is stored in the pygment/styles folder.
    Returns the name of this file (whithout path nor entension)
    """

    import pygments
    syntax_path = os.path.join(pygments.__file__.rpartition(os.sep)[0],
                               'styles')
    syntax_name = name.replace('/', '').capitalize() + 'spyder'
    syntax_filename = syntax_path + syntax_name + '.py'

    syntax_style_imports = ['Name', 'Keyword', 'Comment', 'String',
                            'Number', 'Punctuation']

    imports_string = ", ".join(syntax_style_imports)
    
    syntax_style_dic = get_syntax_style_dictionary()
    syntax_keyword =  []
    syntax_style_subproperties = {'Keyword': syntax_keyword }

    syntax_file_string = "# -*- coding: utf-8 -*-\n"
    syntax_file_string += "from pygments.style import Style\n"
    syntax_file_string += "from pygments.token import {}\n\n".format(imports_string)
    syntax_file_string += "class {}Style(Style):\n".format(syntax_name)
    syntax_file_string += "\tstyles = {\n"
    for key in syntax_style_dic:
        syntax_file_string += "\t\t{}:'".format(key)
        values = syntax_style_dic[key]
        property_values = ''
        for val in values:
            if val != '':
                property_values += "{} ".format(val)
        syntax_file_string += property_values.strip()
        syntax_file_string += "',\n"
        try:
            values_subproperties = syntax_style_subproperties[key]
            for key_val in values_subproperties:
                syntax_file_string += "\t\t{}:'".format(key_val)
                property_values = ''
                syntax_file_string += property_values.strip()
                syntax_file_string += "',\n"
        except:
            pass
    syntax_file_string += "\t}"

    with open(syntax_filename, "w") as syntax_file:
        syntax_file.write(syntax_file_string)

    return syntax_name