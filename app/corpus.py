#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import sqlite3, os, sys, datetime, mammoth, re
from flask import Flask, current_app, g
from flask import render_template, g, request, redirect, url_for, send_from_directory, session, flash
from werkzeug import secure_filename
from collections import defaultdict as dd

from nltk import tokenize
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer


from common_sql import *

import delphin
from delphin.interfaces import ace
from delphin.derivation import UdfNode, UdfTerminal

class TimeoutError(Exception):
    ''' Too long processing time '''

UPLOAD_FOLDER = 'public-uploads'
STATIC = 'static'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC'] = STATIC


# CHECK FOR PET PEEVES
wordcheck = dd(list)

# Wordcheck is checked at lemma level (important for verbs)
wordcheck['Informal'] = set(['hassle', 'tackle', 'stuff', 'stuffs', 'handy', 'air-con', 'info', 'fantastic', 'humongous', 'cash'])

wordchoice = set(["I would like to say","to wrap up","come up with","total waste of time","come into play",
                  "without further ado", "tons of","fork out"])


wordcheck['Formal'] = set(['aforementioned'])

wordcheck['PronounStyle']= set(["I", "me", "mine", "my", "myself",  "you", "your", "yours", "yourself"])

contractions = set(["ain't", "aren't", "can't", "could've", "couldn't", "didn't", "doesn't",
                    "don't", "gonna", "gotta", "hadn't", "hasn't", "haven't", "he'd", "he'll",
                    "he's", "how'd", "how'll", "how's", "I'd", "I'll", "I'm", "I've", "isn't",
                    "it'd", "it'll", "it's", "mayn't", "may've", "mightn't", "might've", "mustn't",
                    "must've", "needn't", "oughtn't", "shan't", "she'd", "she'll", "she's",
                    "should've", "shouldn't",  "that'll", "that're", "that's", "that'd", "there'd",
                    "there're", "there's", "these're", "they'd", "they'll", "they're", "they've",
                    "this's", "those're", "wasn't", "we'd", "we'll", "we're", "we've", "weren't",
                    "what'd", "what'll", "what're", "what's", "what've", "when's", "where'd", "where're",
                    "where's", "where've", "which's", "who'd", "who'll", "who're", "who's", "who've",
                    "why'd", "why're", "why's", "won't", "would've", "wouldn't", "y'all", "you'd",
                    "you'll", "you're", "you've"])
new_contractions = set([])
for c in contractions:
    new_contractions.add(c.replace("'","’"))
contractions = contractions | new_contractions

wordcase_ntu = set(["Executive Committee", "Student Services Center", "Student Services Centre", "Jurong East", "NTU", "Student Union",
                    "Computer Science","Google", "Singaporeans","Singaporean", "Singapore","School of Engineering",
                    "Nanyang Techonological University","MRT"])

months = set(["January", "February", "March", "April", "June", "July", "August", "September", "October", "November", "December"]) # "May" is ambigous, leaving it out

places = set(["Alexandra", "Aljunied", "Geylang", "Ayer Rajah", "Balestier", "Bartley", "Bishan", "Marymount", "Sin Ming", "Bukit Timah", "Sixth Avenue",
              "Buona Vista", "Holland Village", "One North", "Ghim Moh", "Chinatown", "Clarke Quay", "Kreta Ayer", "Telok Ayer", "Kallang", "Bendemeer",
              "Geylang Bahru", "Kallang Bahru", "Kallang Basin", "Kolam Ayer", "Tanjong Rhu", "Mountbatten", "Old Airport", "Lavender", "Boon Keng",
              "Kent Ridge", "Kim Seng", "Little India", "Farrer Park", "Jalan Besar", "MacPherson", "Marina Bay", "Esplanade", "Marina Bay Sands",
              "Marina Centre", "Marina East", "Marina South", "Mount Faber", "Mount Vernon", "Museum", "Newton", "Novena", "Orchard Road", "Dhoby Ghaut",
              "Emerald Hill", "Peranakan Place", "Tanglin", "Outram", "Pasir Panjang", "Paya Lebar", "Eunos", "Geylang East", "Potong Pasir",
              "Rochor-Kampong Glam", "Bencoolen", "Bras Basah", "Bugis", "Queenstown", "Dover", "Commonwealth", "Raffles Place", "River Valley",
              "Singapore River", "Southern Islands", "Tanjong Pagar", "Shenton Way", "Telok Blangah", "Bukit Chandu", "Bukit Purmei", "HarbourFront",
              "Keppel", "Radin Mas", "Mount Faber", "Tiong Bahru", "Bukit Ho Swee", "Bukit Merah", "Toa Payoh", "Bukit Brown", "Caldecott Hill",
              "Thomson", "Whampoa", "St. Michael's", "Bedok", "Bedok Reservoir", "Chai Chee", "Kaki Bukit", "Tanah Merah", "Changi", "Changi Bay",
              "Changi East", "Changi Village", "East Coast", "Joo Chiat", "Katong", "Kembangan", "Pasir Ris", "Elias", "Lorong Halus", "Loyang",
              "Marine Parade", "Siglap", "Tampines", "Simei", "Ubi", "Central Catchment Nature Reserve", "Kranji", "Lentor", "Lim Chu Kang",
              "Neo Tiew", "Sungei Gedong", "Mandai", "Sembawang", "Canberra", "Senoko", "Simpang", "Sungei Kadut", "Woodlands", "Admiralty", "Innova",
              "Marsiling", "Woodgrove", "Yishun", "Chong Pang", "Ang Mo Kio", "Cheng San", "Chong Boon", "Kebun Baru", "Teck Ghee", "Yio Chu Kang",
              "Bidadari", "Hougang", "Defu", "Kovan", "Lorong Chuan", "North-Eastern Islands", "Punggol", "Punggol Point", "Punggol New Town",
              "Seletar", "Sengkang", "Serangoon", "Serangoon Gardens", "Serangoon North", "Boon Lay", "Tukang", "Liu Fang", "Samulun", "Shipyard",
              "Bukit Batok", "Bukit Gombak", "Hillview", "Guilin", "West", "East", "Bukit Panjang", "Choa Chu Kang", "Yew Tee", "Clementi", "Toh Tuck",
              "West Coast", "Jurong East", "Toh Guan", "International Business Park", "Teban Gardens", "Pandan Gardens", "Penjuru", "Yuhua",
              "Jurong Regional Centre", "Lake", "River", "Port", "Jurong West", "Hong Kah", "Taman Jurong", "Boon Lay Place", "Chin Bee", "Yunnan",
              "Kian Teck", "Safti", "Wenya", "Lim Chu Kang", "Pioneer", "Joo Koon", "Gul Circle", "Pioneer Sector", "Tengah", "Tuas", "Wrexham", "Promenade",
              "Pioneer", "Soon Lee", "Tuas South", "Western Islands Planning Area", "Western Water Catchment", "Murai", "Sarimbun"])
wordcase = wordcase_ntu | months | places


# # ONLY FOR PRIVATE USE
# erg_mal = dd(lambda: dd(lambda: dd(dict)))
# for rw in open("erg+mal_result.txt", "r"):
#     if len(rw.strip()) == 0:
#         continue
#     docid, sid, doc_eid, confidence, position, string, label = rw.strip().split("\t")
#     if string == "NNON":
#         string = None
#     if label.startswith("[") and label.endswith("]"):
#         if len(label) == 2:
#             label = "empty_tag_or_label"
#         else:
#             label = label[1:-1].replace(" ", ":")
#     erg_mal[int(docid)][int(sid)][int(doc_eid)] = {"confidence": int(confidence), "position": position, "string": string, "label": label}



def checkd(obj,errors):
    """check each node"""
    if isinstance(obj, UdfNode):
        error = ''
        if 'rbst' in obj.entity:
            error = obj.entity
        if  obj.type and 'mal_' in obj.type:
            error = obj.type
        if error:
            span = " ".join([t.form for t in obj.terminals()])
            errors.append((error, span))
            print(error, span)
        for dtr in obj.daughters:
            dtrs = checkd(dtr,errors)
    return errors



with app.app_context():


    def put_p_for_headings(html):
        html =  html.replace("<h1>", "<h1><p>").replace("</h1>", "</p></h1>")
        html =  html.replace("<h2>", "<h2><p>").replace("</h2>", "</p></h2>")
        html =  html.replace("<h3>", "<h3><p>").replace("</h3>", "</p></h3>")
        html =  html.replace("<h4>", "<h4><p>").replace("</h4>", "</p></h4>")
        html =  html.replace("<h5>", "<h5><p>").replace("</h4>", "</p></h5>")

        return html


    def put_p_or_LF(html):
        ''' This puts LF("\n") before single '<br />'s
            or puts '</p>' before and '<p>' after double (or more) '<br />'s 

            LF("\n") only act as a spliter, so it has to be removed later '''

        unchecked_html = html
        checked_html = ""

        pttn = re.compile(r'(<br\s/>)+')

        while re.search(pttn, unchecked_html):
            mtc = re.search(pttn, unchecked_html)
            mtc_str = mtc.group()

            checked_html += unchecked_html[:mtc.start()]
            unchecked_html = unchecked_html[mtc.end():]

            if len(mtc_str) == 6:    # '<br />'
                checked_html += "\n"
                checked_html += mtc_str
            else:                    # '<br /><br />...'
                if '</p>' in unchecked_html:
                    checked_html += '</p>'
                    checked_html += mtc_str
                    checked_html += '<p>'
                else:
                    checked_html += mtc_str

        checked_html += unchecked_html

        return checked_html


    def remove_LF(string):
        return string.replace("\n", "")

    def put_p_into_list(html):
        ''' This puts <p> and <\p> into a list
            <p> duplicates if it is a footnote list (like '<li id="footnote-XX"><p><p>...'),
             so this script replaces '<p><p>' with '<p>'                                   '''

        unchecked_html = html
        checked_html = ""

        pttn = re.compile('(</?(ol|ul|li)>)|(<li\sid.+?>)')

        (l_start_count, l_end_count) = (0, 0)
        while re.search(pttn, unchecked_html):
            m = re.search(pttn, unchecked_html)
            if m.group(0).startswith("<ol") or m.group(0).startswith("<ul") or m.group(0).startswith("<li"):
                l_start_count += 1
            else:
                l_end_count += 1
            first_end_pstn = m.end()
            checked_html += unchecked_html[:first_end_pstn]
            unchecked_html = unchecked_html[first_end_pstn:]
            if l_start_count == l_end_count:
                continue
            if not re.search(pttn, unchecked_html):
                break
            second = re.search(pttn, unchecked_html)
            if second.start() != 0:
                checked_html += '<p>'
                checked_html += unchecked_html[:second.start()]
                checked_html += '</p>'
                unchecked_html = unchecked_html[second.start():]
                ''' if it is a footnote list '''
                checked_html = checked_html.replace("<p><p>", "<p>").replace("</p></p>", "</p>")

        checked_html += unchecked_html

        return checked_html


    def put_pid(html):
        """This includes pid in each paragraph """
        pid = 1
        while "<p>" in html:
            pttn = "<p id=\"p"+str(pid)+"\">"
            html = html.replace("<p>", pttn, 1)
            pid += 1
        return html

    # def put_p_in_lists(html):
    #     ''' Put <p> and </p> for <ol> and <ul>
    #         If it's a nested list, put <p> and </p> only for the parent 
    #         For example, '<p><ul><li>XXXXXXXX</li></ul></p>'            '''
    #     ''' This doesn't work well with footnote lists
    #          since mammoth gives them <p> by himself                    '''

    #     unchecked_html = html
    #     checked_html = ""

    #     while ('<ol>' in unchecked_html) or ('<ul>' in unchecked_html):
    #         tag_index = {}
    #         if '<ol>' in unchecked_html:
    #             tag_index["<ol>"] = unchecked_html.index('<ol>')
    #         if '<ul>' in unchecked_html:
    #             tag_index["<ul>"] = unchecked_html.index('<ul>')

    #         ''' Detect the parent of a list '''
    #         l_tag, l_tag_index = min(tag_index.items(), key=lambda x:x[1])

    #         if l_tag_index != 0:
    #             checked_html += unchecked_html[:l_tag_index]
    #             unchecked_html = unchecked_html[l_tag_index:]

    #         ''' put '<p>' into checked_html '''
    #         checked_html += '<p>'

    #         l_close_tag = '</'+l_tag[1:]   # </ol> or </ul>

    #         l_parent_close_index = 0   # for the posision of l_close_tag, but only initialise now

    #         for lc in re.finditer(l_close_tag, unchecked_html):
    #             in_checking = unchecked_html[:lc.start()]
    #             l_child_count = in_checking.count(l_tag)-1   # count of nested l_tag
    #             l_child_close_count = in_checking.count(l_close_tag)   # count of nested l_tag (close, </*l>)
    #             if l_child_count == l_child_close_count:
    #                 l_parent_close_index = lc.end()
    #                 break

    #         checked_html += unchecked_html[:l_parent_close_index]+'</p>'
    #         unchecked_html = unchecked_html[l_parent_close_index:]

    #     checked_html += unchecked_html

    #     return checked_html


    def html2list(html):
        """Given HTML, it splits it into tags and text"""
        html = html.replace("<", "---kyoukai---<").replace(">", ">---kyoukai---").replace("---kyoukai------kyoukai---", "---kyoukai---")
        html_list = html.split("---kyoukai---")[1:-1]
        return html_list


    def add_errors_into_html(html, error_list):
        for sid in error_list.keys():
            #colour = ""
            label_and_string = ""
            cfds = []
            for eid in sorted(error_list[sid].keys()):
                cfds.append(error_list[sid][eid]["confidence"])
                label_and_string += '''<nobr><b>{}</b>'''.format(error_list[sid][eid]["label"])
                if error_list[sid][eid]["string"] != None:
                    label_and_string += ": "
                    label_and_string += '<i>'+error_list[sid][eid]["string"]+'</i>'
                label_and_string += ";</nobr> "

            if max(cfds) > 5:
                html = html.replace('error_s{}'.format(sid), "seriouserror")
            else:
                html = html.replace('error_s{}'.format(sid), "milderror")


            rplc = '''<span class=\"tooltiptext\">{}</span>'''.format(label_and_string)
            html = html.replace('errortext_s{}'.format(sid), rplc)


        pttn1 = r'(\sclass=\"tooltip\serror_s[0-9]+\")'
        html = re.sub(pttn1, "", html)

        pttn2 = r'(errortext_s[0-9]+)'
        html = re.sub(pttn2, "", html)

        return html

    def make_structure_valid(html):
        ''' make the structure valid if it is destroied when putting <span>s '''

        pttn_opcl = re.compile(r'(<span(.*?)>)|(</span></span>)')

        ''' dealing with <strong> '''
        unchecked_html = html
        checked_html = ""

        while '<strong>' in unchecked_html:
            open_start_pos = unchecked_html.index('<strong>')
            open_end_pos = open_start_pos+8
            checked_html += unchecked_html[:open_end_pos]
            unchecked_html = unchecked_html[open_end_pos:]

            while re.search(pttn_opcl, unchecked_html[:unchecked_html.index('</strong>')]):
                m = re.search(pttn_opcl, unchecked_html[:unchecked_html.index('</strong>')])
                checked_html += unchecked_html[:m.start()]
                checked_html += '</strong>'
                checked_html += m.group(0)
                checked_html += '<strong>'
                unchecked_html = unchecked_html[m.end():]

            close_end_pos = unchecked_html.index('</strong>')+9
            checked_html += unchecked_html[:close_end_pos]
            unchecked_html = unchecked_html[close_end_pos:]

        checked_html += unchecked_html
        checked_html = checked_html.replace('<strong></strong>', '')

        ''' dealing with <em> '''

        unchecked_html = checked_html
        checked_html = ""

        while '<em>' in unchecked_html:
            open_start_pos = unchecked_html.index('<em>')
            open_end_pos = open_start_pos+8
            checked_html += unchecked_html[:open_end_pos]
            unchecked_html = unchecked_html[open_end_pos:]

            while re.search(pttn_opcl, unchecked_html[:unchecked_html.index('</em>')]):
                m = re.search(pttn_opcl, unchecked_html[:unchecked_html.index('</em>')])
                checked_html += unchecked_html[:m.start()]
                checked_html += '</em>'
                checked_html += m.group(0)
                checked_html += '<em>'
                unchecked_html = unchecked_html[m.end():]

            close_end_pos = unchecked_html.index('</em>')+9
            checked_html += unchecked_html[:close_end_pos]
            unchecked_html = unchecked_html[close_end_pos:]

        checked_html += unchecked_html
        checked_html = checked_html.replace('<em></em>', '')

        return checked_html


    def unescape(s):
      s = s.replace("&lt;", "<")
      s = s.replace("&gt;", ">")
      s = s.replace("&amp;", "&")
      s = s.replace('&quot;', '"')
      return s

    def escape(s):
      s = s.replace("&", "&amp;")
      s = s.replace("<", "&lt;")
      s = s.replace(">", "&gt;")
      s = s.replace('"', '&quot;')
      return s



    def sent2words(sent):
        """Given a sentence string, get a list of (word,pos) elements."""
        return pos_tag(word_tokenize(sent))


    def pos_converter(lemma, pos):
        if pos in ['CD', 'NN', 'NNS', 'NNP', 'NNPS', 'WP', 'PRP']: 
                # include proper nouns and pronouns
                ## fixme flag for proper nouns
            return 'n'
        elif pos.startswith('V'):
            return('v')
        elif pos.startswith('J') or pos in ['WDT',  'WP$', 'PRP$', 'PDT', 'PRP'] or \
                    (pos=='DT' and not lemma in ['a', 'an', 'the']):  ### most determiners
            return('a')
        elif pos.startswith('RB') or pos == 'WRB':
            return('r')
        else:
            return 'x'

    def pos_lemma(lemmatize, tagged_sent):
        #wnl = WordNetLemmatizer()
        # Lemmatize = lru_cache(maxsize=5000)(wnl.lemmatize)
        #lemmatize = wnl.lemmatize
        record_list = []
        wid = 0
        for word, pos in tagged_sent:
            lemma = word
            if wid == 0:
                lemma = lemma.lower()
                wid = 1
            wn_pos = pos_converter(lemma, pos)
            if wn_pos in "avnr":
                lemma = lemmatize(lemma, wn_pos)
            record_list.append((word, pos, lemma))
        return record_list




    def pid_sids2html(html, docname):

        # INSERT INTO doc TABLE
        docid = fetch_max_doc_id() + 1
        insert_into_doc(docid, docname)

        # WORK ON PARAGRAPHS AND SENTENCES
        html_list = html2list(html)
        p_tags = [nn for nn in html_list if nn.startswith("<p id=")]
        pid_max = len(p_tags)

        # FIXME sids are throwing sqlite constraint errors if multime documents are uploaded at the same time 
        # sid = fetch_max_sid()  # LMC Testing if this solves multiple document submission
        sid = docid * 1000000 
        

        ''' activate lemmatizer for pos_lemma '''
        wnl = WordNetLemmatizer()
        lemmatize = wnl.lemmatize

        ''' SET A TIME LIMIT '''
        time_limit = time.time() + 240

        for pid in range(1, pid_max+1):
            p_tag = "<p id=\"p"+str(pid)+"\">"
            p_start = html_list.index(p_tag)  # these 2 should be merged # FIND PID
            position = p_start+1              # these 2 should be merged
            p_string = ""
            string_positions = []
            #    for position in range(p_start, ):
            while True:
                if not html_list[position].startswith("<"):
                    p_string += html_list[position]
                    string_positions.append(position)
                if html_list[position] == "</p>":
                    break
                position += 1

            if p_string == "":
                continue

            split_strings = [ss for ss in unescape(p_string).split("\n") if ss != ""]
            #sents = tokenize.sent_tokenize(unescape(p_string))
            sents = []
            for split_string in split_strings:
                for snt in tokenize.sent_tokenize(split_string):
                    sents.append(snt)
            #    sid = 0
            matching_position = min(string_positions)
            string_positions.remove(matching_position)
            matching_string = remove_LF(html_list[matching_position])
            matched_string = ""
            
            print(sents)
            for sent in sents:
                sid += 1
                # print(sid)

                # INSERT INTO SENT TABLE
                insert_into_sent(sid, docid, pid, sent)

                # INSERT INTO WORD TABLE
                word_list = pos_lemma(lemmatize, sent2words(sent))  # e.g. [('He', 'PRP', 'he'), ('runs', 'VB', 'run')]

                for w in word_list:
                    wid = fetch_max_wid(sid) + 1
                    (surface, pos, lemma) = w
                    insert_into_word(sid, wid, surface, pos, lemma)


                #print(sent)
                sent = escape(sent)
                #print(sent)
                matched_sent = ""
                #print(sent)
                #print(matching_string)
                
                # You need this. Mammoth can make html strings like '<p>			<strong>	Abc def gg</strong></p>'
                while (len(matching_string) == 0) or (matching_string[0] in [" ", u"　", u"\t"]):
                    while (len(matching_string) > 0) and (matching_string[0] in [" ", u"　", u"\t"]):
                        matched_string += matching_string[0]
                        matching_string = matching_string[1:]
                
                    ''' If the matching_string got empty in the last while section '''
                    if len(matching_string) == 0:
                        html_list[matching_position] = matched_string
                        if len(string_positions) == 0:
                            break
                        matching_position = min(string_positions)
                        string_positions.remove(matching_position)
                        matching_string = remove_LF(html_list[matching_position])
                        matched_string = ""

                sent = sent.lstrip()  # nltk.tokenize.sent_tokenize can return [u'               Overall View']
                while len(sent) > 0:
                    ''' This section may go into an infinite loop if there is something wrong
                         with the input html                                                '''
                    if time.time() > time_limit:
                        raise TimeoutError
                    #time.sleep(10)
                    #print("SENTENCE: ", sent)
                    #print("MS: ", matching_string)
                    if matching_string.startswith(sent):  # matching_string contains sent or they are the same
                        if len(matched_sent) == 0:  # whole the sentence matches
                            #matched_string += "<span id=\"s"+str(sid)+"\">"+sent+"</span>"
                            matched_string += '''<span id=\"s{0}\" class=\"tooltip error_s{1}\">{2}errortext_s{3}</span>'''.format(sid, sid, sent, sid)
                            if len(matching_string) > len(sent):
                                matching_string = matching_string[len(sent):]
                            else:
                                matching_string = ""
                        else: # html tag(s) is/are inserted in the middle of the sentence
                            matched_string += '''{0}errortext_s{1}</span>'''.format(sent, sid)
                            if len(matching_string) > len(sent):
                                matching_string = matching_string[len(sent):]
                            else:
                                matching_string = ""
                        sent = ""
                        while (len(matching_string) > 0) and (matching_string[0] in [" ", u"　", u"\t"]):
                            matched_string += matching_string[0]
                            matching_string = matching_string[1:]

                    elif sent.startswith(matching_string):   # sent contains matching_string
                        if len(matched_sent) == 0:  # the starting points are the same
                            #matched_string += "<span id=\"s"+str(sid)+"\">"+matching_string
                            matched_string += '''<span id=\"s{0}\" class=\"tooltip error_s{1}\">{2}'''.format(sid, sid, matching_string)
                        else:
                            matched_string += matching_string
                        matched_sent += matching_string
                        sent = sent[len(matching_string):]
                        matching_string = ""
                    # else:
                    #     print(pid)
                    #     sys.exit(1)
                    # FIX ME, MAKE SOME CHECKS LATER ON


                    if len(matching_string) == 0:
                        # print(matched_string)
                        html_list[matching_position] = matched_string
                        if len(string_positions) == 0:
                            break
                        matching_position = min(string_positions)
                        string_positions.remove(matching_position)
                        matching_string = remove_LF(html_list[matching_position])
                        matched_string = ""



        html = "".join(html_list)
        html = remove_LF(html)
        #update_html_into_doc(docid, html)   ####tk#### moved after check_doc

        return html, docid


    
    def docx2html(docname):
        """ Convert an uploaded .docx document into HTML, and upload it into the database."""


        with open(os.path.join(app.config['UPLOAD_FOLDER'], docname), 'rb') as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
            html = html.replace(u'\xa0', ' ') # replacing non-breaking with a space
            print(html)


            #html = put_h1(html)  #LMC:FIXME: This is bad, cause any word that is bold get's put into a new line, behaving as a title.
            #html = put_p_in_lists(html)    # This doesn't work well
            html = put_p_or_LF(html)
            html = put_p_into_list(html)
            html = put_p_for_headings(html)
            html = put_pid(html)
            #print("\n"+html)
            html, docid = pid_sids2html(html, docname)

            

            #errors = check_doc(docid)


            #return errors + html

            #error_list, error_html = check_doc(docid)
            error_list = check_doc(docid)

            html = add_errors_into_html(html, error_list)
            html = make_structure_valid(html)
            print("\n"+html)
            #### html should be added to doc table here    ####tk####
            update_html_into_doc(docid, html)              ####tk####
            #return error_html + html

            return html




    #############################
    # CHECKS TO DOCUMENT
    #############################

    def check_doc(docid, gold=False):
        """Given a docid, it checks the document for multiple problems. 
        It returns html reporting this."""
        # FIXME, THIS SHOULD BE RETURNING JS/CSS code instead of HTML

        #html = "<h5>Diagnosis:</h5>"
        sents = fetch_sents_by_docid(docid, gold)
        sid_min = min(sents.keys())
        sid_max = max(sents.keys())
        words = fetch_words_by_sid(sid_min, sid_max, gold)

        doc_eid = 0
        onsite_error = dd(lambda: dd(dict))

        # ONLY FOR PRIVATE USE
        #f = open("erg+mal_result.txt", "a")

        seriousthreshold = 50
        mildthreshold = 40
        for sid in words.keys():
            sentlen = len(list(words[sid].keys()))
            if sentlen >= seriousthreshold:

                onsite_error[sid][doc_eid] = {"confidence": 10, "position": "all", "string": None, "label": "VeryLongSentence"}
                doc_eid += 1

            elif sentlen >= mildthreshold:
                onsite_error[sid][doc_eid] = {"confidence": 5, "position": "all", "string": None, "label": "LongSentence"}
                doc_eid += 1

                
        for sid in words.keys():
            for wid in words[sid].keys():

                lemma = words[sid][wid][2].lower()
                word = words[sid][wid][0].lower()

                # Checking for repeated words
                if (wid+1 in words[sid]) and (words[sid][wid+1][0].lower() == word):
                        onsite_error[sid][doc_eid] = {"confidence": 5, "position": str(wid), "string": word+' '+word, "label": "RepeatedWord"}
                        doc_eid += 1
                    
                
                # Lemma checks in wordcheck
                for check in wordcheck:
                    if lemma in wordcheck[check]:
                        onsite_error[sid][doc_eid] = {"confidence": 10, "position": str(wid), "string": lemma, "label": check}
                        doc_eid += 1
                        

            ################################        
            # SENTENCE-LEVEL CHECKS
            ################################

            # Contractions
            for c in contractions:
                if re.search(r'\b{}\b'.format(c), sents[sid][2], re.IGNORECASE):
                    # if c in sents[sid][2]:
                    onsite_error[sid][doc_eid] = {"confidence": 10, "position": "all", "string": c, "label": "Contraction"}
                    doc_eid += 1

            # Word Case
            for exp in wordcase:
                if re.search(r'\b{}\b'.format(exp), sents[sid][2], re.IGNORECASE) and (re.search(r'\b{}\b'.format(exp), sents[sid][2], re.IGNORECASE).group() != exp):
                    onsite_error[sid][doc_eid] = {"confidence": 5, "position": "all", "string": exp, "label": "WordCase"}
                    doc_eid += 1
                    
            # Word Choice (style)
            for exp in wordchoice:
                if re.search(r'\b{}\b'.format(exp), sents[sid][2], re.IGNORECASE):
                    onsite_error[sid][doc_eid] = {"confidence": 5, "position": "all", "string": exp, "label": "WordChoice"}
                    doc_eid += 1
            


        # # USE ACE TO CHECK PARSES FOR EACH SENTENCE (ONLY FOR PRIVATE USE)
        # if docid in erg_mal.keys():
        #     for sid in erg_mal[docid].keys():
        #         for mal_eid in erg_mal[docid][sid].keys():
        #             #print(docid, sid, erg_mal[docid][sid][mal_eid])
        #             onsite_error[sid][doc_eid] = erg_mal[docid][sid][mal_eid]
        #             doc_eid += 1

        # USE ACE TO CHECK PARSES FOR EACH SENTENCE
        with ace.AceParser(os.path.join(app.config['STATIC'], "erg.dat"),
                           executable=os.path.join(app.config['STATIC'], "ace"),
                           cmdargs=['-1', '--timeout=10']) as parser, \
             ace.AceParser(os.path.join(app.config['STATIC'], "erg-mal.dat"),
                           executable=os.path.join(app.config['STATIC'], "ace"),
                           cmdargs=['-1', '--timeout=10', '--udx']) as mal:

            
            for sid in sents.keys():
                
                erg_parse = parser.interact(sents[sid][2])
                parses = len(erg_parse['RESULTS'])

                print("sid:" + str(sid) + " - " + str(parses) + " parses.", flush=True)  #TEST#
                if parses == 0:

                    mal_result = mal.interact(sents[sid][2]) 

                    if len(mal_result['RESULTS']) > 0:  # If the mal-grammar can get a parse

                        print("MALPARSE >>> sid:" + str(sid) + " - " + str(len(mal_result['RESULTS'])) + " parses.", flush=True)  #TEST#

                        # d = str(mal_result.result(0).derivation())
                        # rbst_tags = re.findall(r'[_a-z]+rbst[_a-z]*', d)
                        rbst_tags = checkd(mal_result.result(0).derivation(),[])

                        
                        # for tag in rbst_tags:
                        for tag, string in rbst_tags:
                            if type(tag) == list:
                                if len(tag) == 0:
                                    tag = "empty_tag"
                                else:
                                    tag = ":".join(tag)
                                
                            onsite_error[sid][doc_eid] = {"confidence": 10, "position": "all", "string": string, "label": tag}

                            # ONLY FOR PRIVATE USE
                            #f.write('''{0}\t{1}\t{2}\t10\tall\t{3}\t{4}\n'''.format(docid, sid, doc_eid, string, tag))

                            doc_eid += 1

                            # subva = "third_sg_fin_v_rbst"

                        
                    else: # only a general NoParse tag can be given
                        onsite_error[sid][doc_eid] = {"confidence": 5, "position": "all", "string": None, "label": "NoParse"}

                        # ONLY FOR PRIVATE USE
                        #f.write('''{0}\t{1}\t{2}\t5\tall\tNNON\tNoParse\n'''.format(docid, sid, doc_eid))

                        doc_eid += 1


                
                else: # If the sentence is grammatical, perform other checks (e.g. mood)
                    mrs_error_logging = open("mrs_error_log", "a")
                    try:
                        mrs = erg_parse.result(0).mrs()
                    
                        # CHECKING NON-PROPOSIITONS (mood)
                        sf = mrs.properties(mrs.index)['SF']
                    except:
                        sf = []
                        tm = datetime.datetime.now()
                        mrs_error_logging.write('''{0}\tdocid:{1}\tsid={2}\n'''.format(tm.strftime('%Y-%m-%d_%H:%M:%S'), docid, sid))
                        mrs_error_logging.close()

                    if 'prop' not in sf:

                        # print('non proposition:', mrs.properties(mrs.index)['SF'])

                        if type(sf) == list:
                            if len(sf) == 0:
                                sf = "empty_sf"
                            else:
                                sf = ":".join(sf)

                        onsite_error[sid][doc_eid] = {"confidence": 5, "position": "all", "string": None, "label": sf }

                        # ONLY FOR PRIVATE USE
                        #f.write('''{0}\t{1}\t{2}\t5\tall\tNNON\t{3}\n'''.format(docid, sid, doc_eid, sf))

                        doc_eid += 1

                    
                



        return onsite_error




    #############################
    # UPDATES TO CORPUS DB
    #############################

    def fetch_max_doc_id():
        for r in query_corpus("""SELECT MAX(docid) from doc"""):
            if r['MAX(docid)']:
                return r['MAX(docid)']
            else:
                return 0


    def fetch_max_sid():
        for r in query_corpus("""SELECT MAX(sid) from sent"""):
            if r['MAX(sid)']:
                return r['MAX(sid)']
            else:
                return 0


    def fetch_sents_by_docid(docid, gold=False):
        sents = dd(lambda: dd())
        if gold:
            for r in query_gold("""SELECT sid, pid, sent from sent
            WHERE docid = ?""", [docid]):
                sents[r['sid']]=[r['sid'], r['pid'],r['sent']]
        else:
            for r in query_corpus("""SELECT sid, pid, sent from sent
            WHERE docid = ?""", [docid]):
                sents[r['sid']]=[r['sid'], r['pid'],r['sent']]
        return sents


    def fetch_words_by_sid(sid_min, sid_max, gold=False):
        words = dd(lambda: dd())
        if gold:
            for r in query_gold("""SELECT sid, wid, word, pos, lemma from word
                                 WHERE sid >= ? AND sid <= ?""", [sid_min, sid_max]):    
                words[r['sid']][r['wid']]=[r['word'], r['pos'],r['lemma']]
        else:
            for r in query_corpus("""SELECT sid, wid, word, pos, lemma from word
            WHERE sid >= ? AND sid <= ?""", [sid_min, sid_max]):
                words[r['sid']][r['wid']]=[r['word'], r['pos'],r['lemma']]
        return words



    def fetch_max_wid(sid):
        for r in query_corpus("""SELECT MAX(wid) from word WHERE sid = ?""", [sid]):

            if r['MAX(wid)']:
                return r['MAX(wid)']
            else:
                return 0


    def insert_into_doc(docid, docname):
        return write_corpus("""INSERT INTO doc (docid, title)
                               VALUES (?,?)
                            """, [docid, docname])

    def update_html_into_doc(docid, html):
        return write_corpus("""UPDATE doc SET doc = ? 
                               WHERE docid = ?
                            """, [html, docid])


    def insert_into_sent(sid, docid, pid, sent):
        return write_corpus("""INSERT INTO sent (sid, docID, pid, sent)
                               VALUES (?,?,?,?)
                            """, [sid, docid, pid, sent])


    def insert_into_word(sid, wid, word, pos, lemma):
        return write_corpus("""INSERT INTO word (sid, wid, word, pos, lemma)
                               VALUES (?,?,?,?,?)
                            """, [sid, wid, word, pos, lemma])
