#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, sqlite3, datetime
from flask import Flask, current_app
from flask import render_template, g, request, redirect, url_for, send_from_directory, session, flash
import urllib, gzip, requests
from werkzeug import secure_filename
from lxml import etree

from common_sql import *
# from omw_sql import *
from datetime import datetime as dt

import json # to print dd

# ILI_DTD = 'db/WN-LMF.dtd'
UPLOAD_FOLDER = 'public-uploads'
ALLOWED_EXTENSIONS = set(['xml','gz','xml.gz','doc','tab'])


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


with app.app_context():
    

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS



    def uploadFile(current_user):

        format = "%Y_%b_%d_%H:%M:%S"
        now = datetime.datetime.utcnow().strftime(format)

        try:
            file = request.files['file']
            lic = request.form['license']
        except:
            file = None
            lic = None

        print(lic)

        if file and allowed_file(file.filename):
            filename = now + '_' +str(current_user) + '_' + 'lic' + lic + '_' + file.filename
            filename = secure_filename(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_uploaded = True

        else:
            filename = None
            file_uploaded = False

        return file_uploaded, filename



    def confirmUpload(filename=None, u=None):

        try:

            # print("\n")   #TEST
            # print("ENTERING 1st Iteration")   #TEST
            # print("\n")   #TEST


            l = lambda:dd(l)
            r = l()  # report
            r['new_ili_ids'] = []

            # OPEN FILE
            if filename.endswith('.xml'):
                wn = open(os.path.join(app.config['UPLOAD_FOLDER'],
                                       filename), 'rb')
                wnlmf = etree.XML(wn.read())

            elif filename.endswith('.gz'):
                with gzip.open(os.path.join(app.config['UPLOAD_FOLDER'],
                                            filename), 'rb') as wn:
                    wnlmf = etree.XML(wn.read())


            # PARSE WN & GET ALL NEEDED
            src_id = fetch_src()
            ssrels = fetch_ssrel()
            langs, langs_code = fetch_langs()
            poss = fetch_pos()
            wn, wn_dtls = parse_wn(wnlmf)

            for lexicon in  wn.keys():

                proj_id = f_proj_id_by_code(lexicon)
                lang = wn[lexicon]['attrs']['language']
                lang_id = langs_code['code'][lang]
                version = wn[lexicon]['attrs']['version']
                lex_conf = float(wn[lexicon]['attrs']['confidenceScore'])

                ################################################################
                # CREATE NEW SOURCE BASED ON PROJECT+VERSION
                ################################################################
                src_id = insert_src(int(proj_id), version, u)
                wn[lexicon]['src_id'] = src_id

                ################################################################
                # BULK INSERT SOURCE META
                ################################################################
                blk_src_data = [] # [(src_id, attr, val, u),...]
                for attr, val in wn[lexicon]['attrs'].items():
                    blk_src_data.append((src_id, attr, val, u))
                blk_insert_src_meta(blk_src_data)


                ################################################################
                # GATHER NEW ILI CANDIDATES
                ################################################################
                max_ili_id = fetch_max_ili_id()
                blk_ili_data = []
                # (id, kind, ili_def, status, src_id, origin_key, u)
                for new_ili in wn_dtls['ss_ili_new'][lexicon]:
                    ili_key = max_ili_id + 1
                    synset = wn[lexicon]['syns'][new_ili]

                    status = 2 # TEMPORARY
                    kind = synset['ili_kind']
                    ili_def = None
                    for (l, d) in synset['ili_def'].keys():
                        ili_def = d
                    origin_key = synset['ili_origin_key']

                    blk_ili_data.append((ili_key, kind, ili_def, status,
                                         src_id, origin_key, u))

                    synset['ili_key'] = ili_key
                    r['new_ili_ids'].append(ili_key)
                    max_ili_id = ili_key

                ################################################################
                # WRITE NEW ILI CANDIDATES TO DB
                ################################################################
                blk_insert_into_ili(blk_ili_data)
                ################################################################



                ################################################################
                # GATHER NEW SYNSETS: NEW ILI CONCEPTS + OUT OF ILI CONCEPTS
                ################################################################
                blk_ss_data = list()
                blk_ss_src_data = list()
                blk_def_data = list()
                blk_def_src_data = list()
                blk_ssexe_data = list()
                blk_ssexe_src_data = list()
                max_ss_id = fetch_max_ss_id()
                max_def_id = fetch_max_def_id()
                max_ssexe_id = fetch_max_ssexe_id()
                for new_ss in wn_dtls['ss_ili_new'][lexicon] + \
                              wn_dtls['ss_ili_out'][lexicon]:

                    synset = wn[lexicon]['syns'][new_ss]
                    origin_key = synset['ili_origin_key']
                    ili_id = synset['ili_key']
                    ss_pos = poss['tag'][synset['SSPOS']]

                    ss_id = max_ss_id + 1
                    synset['omw_ss_key'] = ss_id

                    try:
                        ss_conf = float(synset['attrs']['confidenceScore'])
                    except:
                        ss_conf = lex_conf

                    blk_ss_data.append((ss_id, ili_id, ss_pos, u))

                    blk_ss_src_data.append((ss_id, src_id, origin_key,
                                            ss_conf, u))


                    ############################################################
                    # DEFINITIONS
                    ############################################################
                    for (def_lang_id, def_txt) in synset['def'].keys():


                        def_id = max_def_id + 1


                        # if def_id and ss_id and def_lang_id and def_txt and u: #TEST
                        #     test = True #TEST
                        # else: #TEST
                        #     print(def_id, ss_id, def_lang_id, def_txt, u) #TEST


                        blk_def_data.append((def_id, ss_id, def_lang_id, def_txt, u))



                        try:
                            wn_def = synset['def'][(def_lang_id, def_txt)]
                            def_conf = float(wn_def['attrs']['confidenceScore'])
                        except:
                            def_conf = ss_conf

                        blk_def_src_data.append((def_id, src_id, def_conf, u))

                        max_def_id = def_id

                    ############################################################
                    # EXAMPLES
                    ############################################################
                    for (exe_lang_id, exe_txt) in synset['ex'].keys():
                        exe_id = max_ssexe_id + 1

                        blk_ssexe_data.append((exe_id, ss_id, exe_lang_id,
                                               exe_txt, u))

                        try:
                            wn_exe = synset['ex'][(exe_lang_id, exe_txt)]
                            exe_conf = float(wn_exe['attrs']['confidenceScore'])
                        except:
                            exe_conf = ss_conf

                        blk_ssexe_src_data.append((exe_id, src_id, exe_conf, u))

                        max_ssexe_id = exe_id

                    max_ss_id = ss_id  # Update max_ss_id

                ################################################################
                # WRITE NEW SYNSETS TO DB
                ################################################################
                blk_insert_omw_ss(blk_ss_data)
                blk_insert_omw_ss_src(blk_ss_src_data)
                blk_insert_omw_def(blk_def_data)
                blk_insert_omw_def_src(blk_def_src_data)
                blk_insert_omw_ssexe(blk_ssexe_data)
                blk_insert_omw_ssexe_src(blk_ssexe_src_data)
                ################################################################


                ################################################################
                # UPDATE OLD SYNSETS IN OMW (E.G. SOURCE, DEFs, EXEs, etc.)
                ################################################################
                # NOTE: IF THE OLD SYNSET HAS A DIFFERENT POS, IT SHOULD BE
                #       CONSIDERED A NEW SYNSET, BUT LINKED TO THE SAME ILI.
                ################################################################
                blk_ss_data = list()
                blk_ss_src_data = list()
                blk_def_data = list()
                blk_def_data_unique = set()
                blk_def_src_data = list()
                blk_ssexe_data = list()
                blk_ssexe_src_data = list()

                ili_ss_map = f_ili_ss_id_map()
                defs = fetch_all_defs_by_ss_lang_text()
                ssexes = fetch_all_ssexe_by_ss_lang_text()

                max_ss_id = fetch_max_ss_id()
                max_def_id = fetch_max_def_id()
                max_ssexe_id = fetch_max_ssexe_id()
                for linked_ss in wn_dtls['ss_ili_linked'][lexicon]:

                    synset = wn[lexicon]['syns'][linked_ss]
                    ss_pos = poss['tag'][synset['SSPOS']]
                    origin_key = synset['ili_origin_key']
                    ili_id = synset['ili_key']

                    try:
                        ss_conf = float(synset['attrs']['confidenceScore'])
                    except:
                        ss_conf = lex_conf

                    ############################################################
                    # FETCH ALL OMW SYNSETS LINKED TO THIS ILI ID
                    ############################################################
                    linked_ss_ids = ili_ss_map['ili'][ili_id]

                    ############################################################
                    # 2 CASES: SAME POS = SHARE SS, DIFFERENT POS = NEW SS
                    ############################################################
                    ss_id = None
                    for (ss, pos) in linked_ss_ids:
                        if pos == ss_pos:
                            ss_id = ss

                    ############################################################
                    # IF POS MATCH >> UPDATE OLD OMW SYNSET
                    ############################################################
                    if ss_id:

                        synset['omw_ss_key'] = ss_id

                        blk_ss_src_data.append((ss_id, src_id,
                                                origin_key, ss_conf, u))

                        ########################################################
                        # DEFINITIONS
                        ########################################################
                        for (def_lang_id, def_txt) in synset['def'].keys():

                            try:
                                def_id = defs[ss_id][(def_lang_id, def_txt)]
                            except:
                                def_id = None

                            if not def_id:

                                # avoid duplicates linking to the same omw_concept
                                if (ss_id, def_lang_id, def_txt) not in blk_def_data_unique:

                                    def_id = max_def_id + 1

                                    # if def_id and ss_id and def_lang_id and def_txt and u: #TEST
                                    #     test = True #TEST
                                    # else: #TEST
                                    #     print(def_id, ss_id, def_lang_id, def_txt, u) #TEST

                                    blk_def_data_unique.add((ss_id, def_lang_id, def_txt))
                                    blk_def_data.append((def_id, ss_id, def_lang_id,
                                                 def_txt, u))
                                    max_def_id = def_id

                                    try:
                                        wn_def = synset['def'][(def_lang_id, def_txt)]
                                        def_conf = float(wn_def['attrs']['confidenceScore'])
                                    except:
                                        def_conf = ss_conf

                                    blk_def_src_data.append((def_id, src_id,
                                                            def_conf, u))


                                else:
                                    def_id = max_def_id
                                    # print((ss_id, def_lang_id,def_txt)) #TEST #IGNORED

                                max_def_id = def_id




                        ############################################################
                        # EXAMPLES
                        ############################################################
                        for (exe_lang_id, exe_txt) in synset['ex'].keys():

                            try:
                                exe_id = ssexes[ss_id][(exe_lang_id, exe_txt)]
                            except:
                                exe_id = None

                            if not exe_id:
                                exe_id = max_ssexe_id + 1
                                blk_ssexe_data.append((exe_id, ss_id, exe_lang_id,
                                                   exe_txt, u))
                                max_ssexe_id = exe_id

                            try:
                                wn_exe = synset['ex'][(exe_lang_id, exe_txt)]
                                exe_conf = float(wn_exe['attrs']['confidenceScore'])
                            except:
                                exe_conf = ss_conf

                            blk_ssexe_src_data.append((exe_id, src_id, exe_conf, u))

                    ############################################################
                    # NO POS MATCH >> CREATE NEW SYNSET
                    ############################################################
                    else:
                        ss_id = max_ss_id + 1
                        synset['omw_ss_key'] = ss_id

                        blk_ss_data.append((ss_id, ili_id, ss_pos, u))
                        blk_ss_src_data.append((ss_id, src_id, origin_key,
                                                ss_conf, u))

                        ############################################################
                        # DEFINITIONS
                        ############################################################
                        for (def_lang_id, def_txt) in synset['def'].keys():


                            # avoid duplicates linking to the same omw_concept
                            if (ss_id, def_lang_id,def_txt) not in blk_def_data_unique:

                                def_id = max_def_id + 1

                                # if def_id and ss_id and def_lang_id and def_txt and u: #TEST
                                #     test = True #TEST
                                # else: #TEST
                                #     print(def_id, ss_id, def_lang_id, def_txt, u) #TEST

                                blk_def_data_unique.add((ss_id, def_lang_id,def_txt))
                                blk_def_data.append((def_id, ss_id, def_lang_id,
                                             def_txt, u))
                                max_def_id = def_id


                                try:
                                    wn_def = synset['def'][(def_lang_id, def_txt)]
                                    def_conf = float(wn_def['attrs']['confidenceScore'])
                                except:
                                    def_conf = ss_conf

                                blk_def_src_data.append((def_id, src_id, def_conf, u))

                            else:
                                def_id = max_def_id
                                # print((ss_id, def_lang_id,def_txt)) #TEST #IGNORED


                            max_def_id = def_id

                        ############################################################
                        # EXAMPLES
                        ############################################################
                        for (exe_lang_id, exe_txt) in synset['ex'].keys():
                            exe_id = max_ssexe_id + 1

                            blk_ssexe_data.append((exe_id, ss_id, exe_lang_id,
                                                   exe_txt, u))

                            try:
                                wn_exe = synset['ex'][(exe_lang_id, exe_txt)]
                                exe_conf = float(wn_exe['attrs']['confidenceScore'])
                            except:
                                exe_conf = ss_conf

                            blk_ssexe_src_data.append((exe_id, src_id, exe_conf, u))

                            max_ssexe_id = exe_id

                        max_ss_id = ss_id  # Update max_ss_id



                ################################################################
                # INSERT/UPDATE ILI LINKED SYNSETS IN DB
                ################################################################
                blk_insert_omw_ss(blk_ss_data)
                blk_insert_omw_ss_src(blk_ss_src_data)
                blk_insert_omw_def(blk_def_data)
                blk_insert_omw_def_src(blk_def_src_data)
                blk_insert_omw_ssexe(blk_ssexe_data)
                blk_insert_omw_ssexe_src(blk_ssexe_src_data)
                ################################################################



            # print("\n")   #TEST
            # print("ENTERING 2nd Iteration")   #TEST
            # print(r)   #TEST
            # print("\n")   #TEST
            ################################################################
            # 2nd ITERATION: LEXICAL ENTRIES
            ################################################################
            for lexicon in  wn.keys():

                proj_id = f_proj_id_by_code(lexicon)
                lang = wn[lexicon]['attrs']['language']
                lang_id = langs_code['code'][lang]
                version = wn[lexicon]['attrs']['version']
                lex_conf = float(wn[lexicon]['attrs']['confidenceScore'])


                ################################################################
                # INSERT LEXICAL ENTRIES IN DB   - FIXME, ADD TAGS & script
                ################################################################
                blk_f_data = list()
                blk_f_src_data = list()
                blk_w_data = list()
                blk_wf_data = list()
                blk_sense_data = list()
                blk_sense_src_data = list()

                max_f_id = fetch_max_f_id()
                max_w_id = fetch_max_w_id()
                max_s_id = fetch_max_s_id()
                forms = fetch_all_forms_by_lang_pos_lemma()

                for le_id in wn[lexicon]['le'].keys():
                    wn_le = wn[lexicon]['le'][le_id]
                    pos = wn_le['lemma']['attrs']['partOfSpeech']
                    pos_id = poss['tag'][pos]
                    lemma = wn_le['lemma']['attrs']['writtenForm']

                    try:
                        le_conf = float(wn_le['attrs']['confidenceScore'])
                    except:
                        le_conf = lex_conf

                    try:
                        can_f_id = forms[lang_id][(pos_id,lemma)]
                    except:
                        can_f_id = None

                    if not can_f_id:
                        can_f_id = max_f_id + 1
                        blk_f_data.append((can_f_id, lang_id,
                                           pos_id, lemma, u))
                        max_f_id = can_f_id

                        w_id = max_w_id + 1
                        blk_w_data.append((w_id, can_f_id, u))
                        blk_wf_data.append((w_id, can_f_id, src_id,
                                            le_conf, u))
                        max_w_id = w_id

                    else: # New word (no way to know if the word existed!) FIXME!?
                        w_id = max_w_id + 1
                        blk_w_data.append((w_id, can_f_id, u))
                        blk_wf_data.append((w_id, can_f_id, src_id,
                                            le_conf, u))
                        max_w_id = w_id

                    blk_f_src_data.append((can_f_id, src_id, le_conf, u))


                    # ADD OTHER FORMS OF THE SAME WORD
                    for (lem_form_w, lem_form_script) in wn_le['forms'].keys():

                        try:
                            f_id = forms[lang_id][(pos_id,lem_form_w)]
                        except:
                            f_id = None
                        if not f_id:
                            f_id = max_f_id + 1
                            blk_f_data.append((f_id, lang_id,
                                               pos_id, lem_form_w, u))
                            max_f_id = f_id

                        # Always link to word
                        blk_wf_data.append((w_id, f_id, src_id,
                                            le_conf, u))


                    # ADD SENSES
                    for (sens_id, sens_synset) in wn_le['senses'].keys():
                        wn_sens = wn_le['senses'][(sens_id, sens_synset)]
                        try:
                            sens_conf = float(wn_sens['attrs']['confidenceScore'])
                        except:
                            sens_conf = le_conf


                        synset = wn[lexicon]['syns'][sens_synset]
                        ss_id = synset['omw_ss_key']

                        s_id = max_s_id + 1
                        blk_sense_data.append((s_id, ss_id, w_id, u))
                        max_s_id = s_id
                        blk_sense_src_data.append((s_id, src_id, sens_conf, u))


                    # FIXME! ADD Form.Script
                    # FIXME! ADD SenseRels, SenseExamples, Counts
                    # FIXME! ADD SyntacticBehaviour

                ################################################################
                # INSERT LEXICAL ENTRIES IN DB
                ################################################################
                blk_insert_omw_f(blk_f_data)
                blk_insert_omw_f_src(blk_f_src_data)
                blk_insert_omw_w(blk_w_data)
                blk_insert_omw_wf_link(blk_wf_data)
                blk_insert_omw_s(blk_sense_data)
                blk_insert_omw_s_src(blk_sense_src_data)
                ################################################################



            # print("\n")   #TEST
            # print("ENTERING 3rd Iteration")   #TEST
            # print(r)   #TEST
            # print("\n")   #TEST
            ############################################################
            # 3rd ITTERATION: AFTER ALL SYNSETS WERE CREATED
            ############################################################
            # SSREL (SYNSET RELATIONS)   FIXME, ADD SENSE-RELS
            ############################################################
            ili_ss_map = f_ili_ss_id_map()
            sslinks = fetch_all_ssrels_by_ss_rel_trgt()
            blk_sslinks_data = list()
            blk_sslinks_data_unique = set()
            blk_sslinks_src_data = list()
            max_sslink_id = fetch_max_sslink_id()
            for lexicon in wn.keys():
                src_id = wn[lexicon]['src_id']
                lang = wn[lexicon]['attrs']['language']
                lang_id = langs_code['code'][lang]
                lex_conf = float(wn[lexicon]['attrs']['confidenceScore'])

                for new_ss in wn_dtls['ss_ili_new'][lexicon] + \
                              wn_dtls['ss_ili_out'][lexicon]:
                    synset = wn[lexicon]['syns'][new_ss]
                    ss1_id = synset['omw_ss_key']

                    try:
                        ss_conf = float(synset['attrs']['confidenceScore'])
                    except:
                        ss_conf = lex_conf

                    for (rel, trgt) in synset['ssrel'].keys():

                        lex2 = trgt.split('-')[0]
                        synset2 = wn[lex2]['syns'][trgt]
                        ss2_id = synset2['omw_ss_key']
                        ssrel_id = ssrels['rel'][rel][0]


                        if (ss1_id, ssrel_id, ss2_id) not in blk_sslinks_data_unique:
                            blk_sslinks_data_unique.add((ss1_id, ssrel_id, ss2_id))

                            sslink_id = max_sslink_id + 1
                            blk_sslinks_data.append((sslink_id, ss1_id, ssrel_id,
                                                     ss2_id, u))

                            try:
                                sslink_attrs = synset['ssrel'][(rel, trgt)]['attrs']
                                sslink_conf = float(sslink_attrs['confidenceScore'])
                            except:
                                sslink_conf = ss_conf


                            blk_sslinks_src_data.append((sslink_id, src_id,
                                                         sslink_conf, lang_id, u))

                        else:
                            sslink_id = max_sslink_id
                            # print((ss1_id, ssrel_id, ss2_id)) #TEST #IGNORED

                        max_sslink_id = sslink_id




                ############################################################
                # IN THIS CASE WE NEED TO FIND WHICH MAP IT RECEIVED ABOVE
                ############################################################
                for linked_ss in wn_dtls['ss_ili_linked'][lexicon]:

                    synset = wn[lexicon]['syns'][linked_ss]
                    ss_pos = poss['tag'][synset['SSPOS']]
                    origin_key = synset['ili_origin_key']
                    ili_id = synset['ili_key']

                    ############################################################
                    # FETCH ALL OMW SYNSETS LINKED TO THIS ILI ID
                    ############################################################
                    linked_ss_ids = ili_ss_map['ili'][ili_id]

                    ss_id = None
                    for (ss, pos) in linked_ss_ids: # THERE MUST BE ONE!
                        if pos == ss_pos:
                            linked_ss = ss


                    synset = wn[lexicon]['syns'][linked_ss]
                    ss1_id = synset['omw_ss_key']

                    try:
                        ss_conf = float(synset['attrs']['confidenceScore'])
                    except:
                        ss_conf = lex_conf



                    for (rel, trgt) in synset['ssrel'].keys():

                        lex2 = trgt.split('-')[0]
                        synset2 = wn[lex2]['syns'][trgt]
                        ss2_id = synset2['omw_ss_key']
                        ssrel_id = ssrels['rel'][rel][0]



                        if (ss1_id, ssrel_id, ss2_id) not in blk_sslinks_data_unique:
                            blk_sslinks_data_unique.add((ss1_id, ssrel_id, ss2_id))


                            sslink_id = sslinks[ss1_id][(ssrel_id, ss2_id)]
                            if not sslink_id:
                                sslink_id = max_sslink_id + 1
                                blk_sslinks_data.append((sslink_id, ss1_id,
                                                         ssrel_id, ss2_id, u))
                                max_sslink_id = sslink_id


                            try:
                                sslink_attrs = synset['ssrel'][(rel, trgt)]['attrs']
                                sslink_conf = float(sslink_attrs['confidenceScore'])
                            except:
                                sslink_conf = ss_conf

                            blk_sslinks_src_data.append((sslink_id, src_id,
                                                         sslink_conf, lang_id, u))


                        else:
                            sslink_id = max_sslink_id
                            # print((ss1_id, ssrel_id, ss2_id)) #TEST #IGNORED


            ################################################################
            # INSERT SSRELS INTO THE DB
            ################################################################
            blk_insert_omw_sslink(blk_sslinks_data)
            blk_insert_omw_sslink_src(blk_sslinks_src_data)
            ################################################################




            return r
        except:
            return False
