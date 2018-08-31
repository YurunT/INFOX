import os
import re
import nltk
import itertools
import time
from collections import Counter
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer
from ...models import *
from collections import OrderedDict
from . import language_tool

stemmer = PorterStemmer()
lemmatizer = WordNetLemmatizer()

def word_split_by_char(s):
    """ split the word by some separators
        Args:
            Word
        Returns:
            List of the split words
    """
    old_words = []
    old_words.append(s)
    result = []
    while len(old_words) > 0:
        new_words = []
        for s in old_words:
            if '-' in s:  # Case: ab-cd-ef
                new_words+=s.split('-')
            elif '.' in s:  # Case: ab.cd.ef
                new_words+=s.split('.')
            elif '_' in s:  # Case: ab_cd_ef
                new_words+=s.split('_')
            elif '/' in s:  # Case: ab/cd/ef
                new_words+=s.split('/')
            elif '\\' in s: # Case: ab\cd\ef
                new_words+=s.split('\\')
            else:
                if re.search('[A-Z]+', s):  # Case AbcDefGh or abcDefGh
                    result+=re.sub('([a-zA-Z])([A-Z])', lambda match: match.group(1).lower() + "_" + match.group(2).lower(), s).split('_')
                result.append(s)
        old_words = new_words
    return result

def word_process(word):
    #将word词尾不为[0-9A-Za-z_]的去掉
    search_result = re.search("[0-9A-Za-z_]", word)
    if not search_result:
        return ""
    word = word[search_result.start():]
    while (len(word) > 0) and (not re.match("[0-9A-Za-z_]", word[-1:])):
        word = word[:-1]
    return word


def word_filter(word):
    """ The filter used for deleting the noisy words in changed code.
    Here is the method:
        1. Delete character except for digit, alphabet, '_'.
        2. the word shouldn't be all digit.
        3. the length should large than 2.
    Args:
        word
    Returns:
        True for not filtering, False for filtering.
    """
    if word[:2] == '0x':
        return False
    if '=' in word:
        return False
    if '/' in word:
        return False
    if '.' in word:
        return False
    if '$' in word:
        return False
    word = re.sub("[^0-9A-Za-z_]", "", word)
    if(word.isdigit()):
        return False
    if(len(word) <= 2):
        return False
    return True

"""
def stem_process(tokens):
    # Do stem on the tokens.
    for try_times in range(3):
        try:
            result = [stemmer.stem(word) for word in tokens]
            return result
        except:
            print('error on stem_process')
            time.sleep(5)
    return tokens
"""

def lemmatize_process(obj):
    for try_times in range(3): # NLTK is not thread-safe, use simple retry to fix it.
        try:
            result = [lemmatizer.lemmatize(word) for word in obj]
        except:
            print('error on lemmatize_process')
            time.sleep(5)
    return result




def move_other_char(text):
    return re.sub("[^0-9A-Za-z_]", "", text)

def get_words_from_file(file, text):
    """
        Args:
            file: file full name
            text: the raw text of the file
        Returns:
            A list of the tokens of the result of the participle. 
    """
    if file and (not language_tool.is_text(file)):
        return []
    if text is None:
        return []
    raw_tokens = nltk.word_tokenize(text)
    origin_tokens = [word_process(x) for x in raw_tokens]
    tokens = origin_tokens
    tokens = list(itertools.chain(*[word_split_by_char(token) for token in origin_tokens]))
    tokens.extend(list(itertools.chain(*[word_split_by_char(token) for token in origin_tokens]))) # Keep original tokens

    #tokens = sum([word_split_by_char(token) for token in origin_tokens], origin_tokens)
    tokens = [x.lower() for x in tokens]
    tokens = filter(word_filter, tokens)
    tokens = filter(lambda x: x not in language_tool.get_language_stop_words(
        language_tool.get_language(file)), tokens)
    tokens = filter(lambda x: x not in language_tool.get_general_stopwords(), tokens)
    tokens = list(tokens)

    # stemmed_tokens = [PorterStemmer().stem(word) for word in tokens] # do stem on the tokens

    return tokens

def get_words(text):
    return get_words_from_file('1.txt', text)

def get_counter(tokens):
    tokens = filter(lambda x: x is not None, tokens)
    return Counter(tokens)

def get_top_words(tokens, top_number, list_option = True):
    if tokens is None:
        return None
    counter = get_counter(tokens).most_common(top_number)
    if list_option:
        return [x for x, y in counter]
    else:
        return dict([(x,y) for x, y in counter])

# just for test
def get_top_words_from_text(text, top_number=10):
    return get_top_words(get_words(text), top_number)

def split_text_to_lines(part_dic):
    """
            Args:
                text: the raw text of the file, in the form of dic, to indicate different parts in file ,
                Such as:{'@@ -46,6 +46,15 @@': '#define DEFAULT_LCD_CONTRAST 17\n',  '@@ -76,8 +76,8 @@': '#endif\n \n+  #if ENABLED(ANET_KEYPAD_LCD)'}
            Returns:
                A dic of num of the lines of the the different parts of the file.
                Such as : {'@@ -112,7 +167,7 @@':{'112/167':this is me','-1/170':'+he is good','117/-1':'+he is good',...},..}
                p.s. minus symbol represents a blank space
                e.g.
                '112/167' means: this line is the #112 in base file while #167 in compared file.
                '-1/170'  means: this line are not in base file, but only exists in line #170 of compared file, indicating a '+' symbol at the beginning of the line.
                '117,-1'  means alike.

    """
    print("this is split_text_to_lines")
    part_dic2 = OrderedDict()
    for part_tag, text in part_dic.items():
        split_text = text.split("\n")
        mode = re.compile(r'\d+')
        part_num = mode.findall(part_tag)  # like:['16', '7', '16', '7']
        origin_start_num = int(part_num[0])
        origin_length = int(part_num[1])
        thisTime_start_num = int(part_num[2])
        thisTime_length = int(part_num[3])

        lines_dic = OrderedDict()
        i = 0
        for line in split_text:
            d1 = ""
            d2 = ""
            if line != '' and line[0] == '+':
                d1 = '-1'
                d2 = str(thisTime_start_num + i)
            elif line != '' and line[0] == '-':
                d1 = str(origin_start_num + i)
                d2 = '-1'
            else:
                d1 = str(origin_start_num + i)
                d2 = str(thisTime_start_num + i)
            i+=1
            key = d1 + '/' + d2
            lines_dic[key] = line
        part_dic2[part_tag] = lines_dic
    return part_dic2


def list_word_linenumber(split_text,tokens):
    """
               Args:
                   split_text: {'@@ -112,7 +167,7 @@':{'112/167':this is me','-1/170':'+he is good','117/-1':'+me is good',...},..}
                   tokens: filtered tokens from added_code
               Returns:
                   A dic of the mapping from tokens to the num of lines where they exist.
                   Such as: {'@@ -112,7 +167,7 @@':{'is': ['112/167', '-1/170'], 'me': ['117/-1']},...}
    """
    print("this is list_word_linenumber ")
    word_linenumber_dic=OrderedDict()
    for part_tag,line_dic in split_text.items():
        token_dic={}
        for token in tokens:
            for try_times in range(3):  # NLTK is not thread-safe, use simple retry to fix it.
                try:
                    lemmatize_token = lemmatizer.lemmatize(token)
                except:
                    print('error on lemmatize_process')
            token_list=[]
            for line_tag, line in line_dic.items():
                if token in line.lower():
                    token_list.append(line_tag)
            if token_list!=[]:
                token_dic[token]=token_list
        word_linenumber_dic[part_tag]=token_dic
    return word_linenumber_dic


