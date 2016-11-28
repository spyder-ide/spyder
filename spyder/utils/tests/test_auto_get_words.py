# -*- coding: utf-8 -*-
"""
Editor de Spyder

Este es un archivo temporal
"""
from os.path import dirname, abspath, splitext, realpath
from os import listdir, getcwd
from re import sub, compile
from spyder.utils.introspection.utils import get_words_file


def perform_automatic_texf_file_format():
    test_path = dirname(abspath(__file__))
    
    test_files = {}
    
    for ext in listdir(test_path+"/data/"):
        file_path = test_path+"/data/"+ext
        key = splitext(file_path)[1]
        test_files.setdefault(key, {'file_path':file_path})
    
        with open(file_path) as infile:
            content = infile.read()
            
        test_files[key].update({'content':content})
        
        if key in ['.css']:
            regex = compile(r'([^a-zA-Z-])')
            expect_words = sorted(set(regex.sub(r' ', content).split()))
            
        elif key in ['.R', '.c', 'md', '.cpp, java','.py']:
            regex = compile(r'([^a-zA-Z_])')
            expect_words = sorted(set(regex.sub(r' ', content).split()))
        else:
            regex = compile(r'([^a-zA-Z])')
            expect_words = sorted(set(regex.sub(r' ', content).split()))
    
        test_files[key].update({'expect_words':expect_words})
        
    for f in test_files.keys():
        words = get_words_file(test_files[f]['file_path'])
        
        #print (sorted(words), sorted(test_files[f]['expect_words']))
        assert(sorted(words)) == sorted(test_files[f]['expect_words'])
    
perform_automatic_texf_file_format()
        
