#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sqlite3, os, sys, datetime, mammoth
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


UPLOAD_FOLDER = 'public-uploads'
STATIC = 'static'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC'] = STATIC


with app.app_context():


    def put_h1(html):
        """This tags text marked as bold with h5 headers"""
        return html.replace("<strong>", "<h5><strong>").replace("</strong>", "</strong></h5>")

    def put_pid(html):
        """This includes pid in each paragraph """
        pid = 1
        while "<p>" in html:
            pttn = "<p id=\"p"+str(pid)+"\">"
            html = html.replace("<p>", pttn, 1)
            pid += 1
        return html


    def html2list(html):
        """Given HTML, it splits it into tags and text"""
        html = html.replace("<", "---kyoukai---<").replace(">", ">---kyoukai---").replace("---kyoukai------kyoukai---", "---kyoukai---")
        html_list = html.split("---kyoukai---")[1:-1]
        return html_list



    def unescape(s):
      s = s.replace("&lt;", "<")
      s = s.replace("&gt;", ">")
      s = s.replace("&amp;", "&")
      return s

    def escape(s):
      s = s.replace("<", "&lt;")
      s = s.replace(">", "&gt;")
      s = s.replace("&", "&amp;")
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

    def pos_lemma(tagged_sent):
        wnl = WordNetLemmatizer()
        # Lemmatize = lru_cache(maxsize=5000)(wnl.lemmatize)
        lemmatize = wnl.lemmatize
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

        sid = fetch_max_sid()



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

            sents = tokenize.sent_tokenize(unescape(p_string))
            #    sid = 0
            matching_position = min(string_positions)
            string_positions.remove(matching_position)
            matching_string = html_list[matching_position]
            matched_string = ""
            for sent in sents:
                sid += 1
                # print(sid)

                # INSERT INTO SENT TABLE
                insert_into_sent(sid, docid, pid, sent)

                # INSERT INTO WORD TABLE
                word_list = pos_lemma(sent2words(sent))  # e.g. [('He', 'PRP', 'he'), ('runs', 'VB', 'run')]

                for w in word_list:
                    wid = fetch_max_wid(sid) + 1
                    (surface, pos, lemma) = w
                    insert_into_word(sid, wid, surface, pos, lemma)



                sent = escape(sent)
                matched_sent = ""
                # print(sent)
                # print(matching_string)
                while len(sent) > 0:
                    if matching_string.startswith(sent):  # matching_string contains sent or they are the same
                        if len(matched_sent) == 0:  # whole the sentence matches
                            matched_string += "<span id=\"s"+str(sid)+"\">"+sent+"</span>"
                            if len(matching_string) > len(sent):
                                matching_string = matching_string[len(sent):]
                            else:
                                matching_string = ""
                        else: # html tag(s) is/are inserted in the middle of the sentence
                            matched_string += sent+"</span>"
                            if len(matching_string) > len(sent):
                                matching_string = matching_string[len(sent):]
                            else:
                                matching_string = ""
                        sent = ""
                        while len(matching_string) > 0 and matching_string[0] == " ":
                            matched_string += matching_string[0]
                            matching_string = matching_string[1:]

                    elif sent.startswith(matching_string):   # sent contains matching_string
                        if len(matched_sent) == 0:  # the starting points are the same
                            matched_string += "<span id=\"s"+str(sid)+"\">"+matching_string
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
                        matching_string = html_list[matching_position]
                        matched_string = ""



        html = "".join(html_list)
        update_html_into_doc(docid, html)

        return html, docid






    def convert_image(image):
        """This should save the image into the UPLOAD_FOLDER. """
        with image.open() as image_bytes:
            # encoded_src = base64.b64encode(image_bytes.read()).decode("ascii")
            # FOR NOW JUST PUT A PLACEHOLDER
            encoded_src = "IMAGE PLACEHOLDER"
        return {
            # "src": "data:{0};base64,{1}".format(image.content_type, encoded_src)
            "src": encoded_src
        }

    
    def docx2html(docname):
        """ Convert an uploaded .docx document into HTML, and upload it into the database."""


        with open(os.path.join(app.config['UPLOAD_FOLDER'], docname), 'rb') as docx_file:
            result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.img_element(convert_image))
            print("MESSAGES: " + str(result.messages)) # print if anyting went wrong during convertion

            html = result.value
            print(html)

            

            html = put_h1(html)  #LMC:FIXME: This is bad, cause any word that is bold get's put into a new line, behaving as a title.
            html = put_pid(html)

            html, docid = pid_sids2html(html, docname)



            errors = check_doc(docid)


            return errors + html





    #############################
    # CHECKS TO DOCUMENT
    #############################

    def check_doc(docid):
        """Given a docid, it checks the document for multiple problems. 
        It returns html reporting this."""
        # FIXME, THIS SHOULD BE RETURNING JS/CSS code instead of HTML

        html = "<h5>Diagnosis:</h5>"

        sents = fetch_sents_by_docid(docid)
        sid_min = min(sents.keys())
        sid_max = max(sents.keys())

        words = fetch_words_by_sid(sid_min, sid_max)


        # CHECK FOR SENTENCE LENGTH
        threshold = 35
        change = False
        for sid in words.keys():
            if len(list(words[sid].keys())) >= threshold:
                
                # FIXME! this u"string" will not work on python3
                change = True
                html += u"""<p><b>Sentence:</b> <em>{}</em>
                <br> The sentence above seems to be a bit long. 
                You might want to consider splitting it into shorter sentences.
                 </p>""".format(sents[sid][2])

        if change: # Add a separator if something was added 
            html += "<hr>"



        # CHECK FOR PET PEEVES
        informal_lang = ['hassle', 'Hassle', 'tackle', 'Tackle'] 
        # LMC FIXME!, it seems that lemmatizer doesn't work well when it thinks it's a proper noun. 
        # I added the capitalised forms by hand for now  
        change = False
        for sid in words.keys():
            for wid in words[sid].keys():
                if words[sid][wid][2] in informal_lang:
                    change = True
                    html += u"""<p><b>Sentence:</b> <em>{}</em><br>
                    The sentence above seems to make use of informal 
                    language. Please refrain from using the word 
                    <b><em>{}</em></b>.</p>
                    """.format(sents[sid][2], words[sid][wid][0])



        # USE ACE TO CHECK PARSES FOR EACH SENTENCE
        with ace.AceParser(os.path.join(app.config['STATIC'], "erg.dat"), executable=os.path.join(app.config['STATIC'], "ace"), cmdargs=['-1']) as parser:

            for sid in sents.keys():
                
                parses = len(parser.interact(sents[sid][2])['RESULTS'])
                print("sid:" + str(sid) + " - " + str(parses) + " parses.")
                if parses == 0:
                    change = True
                    html += u"""<p><b>Sentence:</b> <em>{}</em><br>
                    The sentence above seems to have some problem with its grammar.
                    Consider breaking it into smaller sentences or, possibly, revise it.   
                    </p>
                    """.format(sents[sid][2])



        if change: # Add a separator if something was added 
            html += "<hr>"



        return html




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


    def fetch_sents_by_docid(docid):
        sents = dd(lambda: dd())
        for r in query_corpus("""SELECT sid, pid, sent from sent
                                 WHERE docid = ?""", [docid]):    
            sents[r['sid']]=[r['sid'], r['pid'],r['sent']]
        return sents


    def fetch_words_by_sid(sid_min, sid_max):
        words = dd(lambda: dd())
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
