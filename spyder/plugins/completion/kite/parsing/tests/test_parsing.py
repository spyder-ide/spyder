# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)


from spyder.plugins.completion.kite.parsing import find_returning_function_path


def test_find_returning_function_path():
    # maps expected definition value to file content
    # $ marks the cursor position and will be removed before "parsing"
    table = [
        ['pd.read_csv', '''import pandas as pd
df = pd.read_csv("a")
df.$'''],
        ['pd.read_csv', '''import pandas as pd
df = pd.read_csv("a")
df.a$'''],
        ['pd.read_csv', '''import pandas as pd
df = pd.read_csv("a")
foo = df.$'''],
        ['pd.read_csv', '''import pandas as pd
df = pd.read_csv("a")
foo = df.a$'''],
        ['plt.figure', '''import matplotlib.pyplot as plt
fig=plt.figure(figsize=(15, 10))
fig.$'''],
        ['sns.pairplot', '''import seaborn as sns
g = sns.pairplot(temp[[u'Pclass', u'Sex', u'Age', u'Parch', u'Fare',
    u'Embarked', u'FamilySize', u'Title', u'Survived']],
    hue='Survived', palette = 'seismic',size=1.2,diag_kind = 'kde',
    diag_kws=dict(shade=True),plot_kws=dict(s=10) )
g.s$''']
    ]

    for k in table:
        expected, content = k
        offset = content.find('$')
        content = content[0:offset]
        print('Checking {}: {}\n'.format(
            expected,
            content.replace('\n', '\\n')))
        assert expected == find_returning_function_path(content, offset)
