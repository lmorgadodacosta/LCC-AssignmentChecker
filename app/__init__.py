#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, sqlite3, datetime, urllib, gzip, requests, codecs
from time import sleep
from flask import Flask, render_template, g, request, redirect, url_for, send_from_directory, session, flash, jsonify, make_response, Markup
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from functools import wraps
from itsdangerous import URLSafeTimedSerializer # for safe session cookies
from collections import defaultdict as dd
from collections import OrderedDict as od
from hashlib import md5
from werkzeug import secure_filename
#from lxml import etree

## profiler
#from werkzeug.contrib.profiler import ProfilerMiddleware


from common_login import *
from common_sql import *
from corpus import *
from check import *


from math import log

app = Flask(__name__)
app.secret_key = "!$flhgSgngNO%$#SOET!$!"
app.config["REMEMBER_COOKIE_DURATION"] = datetime.timedelta(minutes=30)

#error_logging = open("corpus_inputting_error_log", "a")#, "utf-8")    ####tk####

################################################################################
# LOGIN
################################################################################
login_manager.init_app(app)

@app.route("/login", methods=["GET", "POST"])
def login():
    """ This login function checks if the username & password
    match the admin.db; if the authentication is successful,
    it passes the id of the user into login_user() """

    if request.method == "POST" and \
       "username" in request.form and \
       "password" in request.form:
        username = request.form["username"]
        password = request.form["password"]

        user = User.get(username)

        # If we found a user based on username then compare that the submitted
        # password matches the password in the database. The password is stored
        # is a slated hash format, so you must hash the password before comparing it.
        if user and hash_pass(password) == user.password:
            login_user(user, remember=True)
            # FIXME! Get this to work properly...
            # return redirect(request.args.get("next") or url_for("index"))
            return redirect(url_for("index"))
        else:
            flash(u"Invalid username, please try again.")
    return render_template("login.html")

@app.route("/logout")
@login_required(role=0, group='open')
def logout():
    logout_user()
    return redirect(url_for("index"))
################################################################################



################################################################################
# SET UP CONNECTION WITH DATABASES
################################################################################
@app.before_request
def before_request():
    g.admin = connect_admin()
    g.corpus = connect_corpus()
    g.gold = connect_gold()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.admin.close()
        g.corpus.close()
        g.gold.close()
################################################################################


################################################################################
# AJAX REQUESTS
################################################################################
# @app.route('/_thumb_up_id')
# def thumb_up_id():
#     user = fetch_id_from_userid(current_user.id)
#     ili_id = request.args.get('ili_id', None)
#     rate = 1
#     r = rate_ili_id(ili_id, rate, user)

#     counts, up_who, down_who = f_rate_summary([ili_id])
#     html = """ <span style="color:green" title="{}">+{}</span><br>
#                <span style="color:red"  title="{}">-{}</span>
#            """.format(up_who[int(ili_id)], counts[int(ili_id)]['up'],
#                       down_who[int(ili_id)], counts[int(ili_id)]['down'])
#     return jsonify(result=html)


# @app.route('/_thumb_down_id')
# def thumb_down_id():
#     user = fetch_id_from_userid(current_user.id)
#     ili_id = request.args.get('ili_id', None)
#     rate = -1
#     r = rate_ili_id(ili_id, rate, user)

#     counts, up_who, down_who = f_rate_summary([ili_id])
#     html = """ <span style="color:green" title="{}">+{}</span><br>
#                <span style="color:red"  title="{}">-{}</span>
#            """.format(up_who[int(ili_id)], counts[int(ili_id)]['up'],
#                       down_who[int(ili_id)], counts[int(ili_id)]['down'])
#     return jsonify(result=html)


# @app.route('/_comment_id')
# def comment_id():
#     user = fetch_id_from_userid(current_user.id)
#     ili_id = request.args.get('ili_id', None)
#     comment = request.args.get('comment', None)
#     comment = str(Markup.escape(comment))
#     dbinsert = comment_ili_id(ili_id, comment, user)
#     return jsonify(result=dbinsert)


# @app.route('/_detailed_id')
# def detailed_id():
#     ili_id = request.args.get('ili_id', None)
#     rate_hist = fetch_rate_id([ili_id])
#     comm_hist = fetch_comment_id([ili_id])
#     users = fetch_allusers()

#     r_html = ""
#     for r, u, t in rate_hist[int(ili_id)]:
#         r_html += '{} ({}): {} <br>'.format(users[u]['userID'], t, r)

#     c_html = ""
#     for c, u, t in comm_hist[int(ili_id)]:
#         c_html += '{} ({}): {} <br>'.format(users[u]['userID'], t, c)

#     html = """
#     <td colspan="9">
#     <div style="width: 49%; float:left;">
#     <h6>Ratings</h6>
#     {}</div>
#     <div style="width: 49%; float:right;">
#     <h6>Comments</h6>
#     {}</div>
#     </td>""".format(r_html, c_html)

#     return jsonify(result=html)


# @app.route('/_confirm_wn_upload')
# def confirm_wn_upload_id():
#     user = fetch_id_from_userid(current_user.id)
#     fn = request.args.get('fn', None)
#     upload = confirmUpload(fn, user)
#     labels = updateLabels()
#     return jsonify(result=upload)


# @app.route('/_add_new_project')
# def add_new_project():
#     user = fetch_id_from_userid(current_user.id)
#     proj = request.args.get('proj_code', None)
#     proj = str(Markup.escape(proj))
#     if user and proj:
#         dbinsert = insert_new_project(proj, user)
#         return jsonify(result=dbinsert)
#     else:
#         return jsonify(result=False)


# @app.route("/_load_lang_selector",methods=["GET"])
# def omw_lang_selector():
#     selected_lang = request.cookies.get('selected_lang')
#     selected_lang2 = request.cookies.get('selected_lang2')
#     lang_id, lang_code = fetch_langs()
#     html = '<select name="lang" style="font-size: 85%; width: 9em" required>'
#     for lid in lang_id.keys():
#         if selected_lang == str(lid):
#             html += """<option value="{}" selected>{}</option>
#                     """.format(lid, lang_id[lid][1])
#         else:
#             html += """<option value="{}">{}</option>
#                     """.format(lid, lang_id[lid][1])
#     html += '</select>'
#     html += '<select name="lang2" style="font-size: 85%; width: 9em" required>'
#     for lid in lang_id.keys():
#         if selected_lang2 == str(lid):
#             html += """<option value="{}" selected>{}</option>
#                     """.format(lid, lang_id[lid][1])
#         else:
#             html += """<option value="{}">{}</option>
#                     """.format(lid, lang_id[lid][1])
#     html += '</select>'
#     return jsonify(result=html)

# @app.route('/_add_new_language')
# def add_new_language():
#     user = fetch_id_from_userid(current_user.id)
#     bcp = request.args.get('bcp', None)
#     bcp = str(Markup.escape(bcp))
#     iso = request.args.get('iso', None)
#     iso = str(Markup.escape(iso))
#     name = request.args.get('name', None)
#     name = str(Markup.escape(name))
#     if bcp and name:
#         dbinsert = insert_new_language(bcp, iso, name, user)
#         return jsonify(result=dbinsert)
#     else:
#         return jsonify(result=False)


# @app.route('/_load_proj_details')
# def load_proj_details():
#     proj_id = request.args.get('proj', 0)
#     if proj_id:
#         proj_id = int(proj_id)
#     else:
#         proj_id = None

#     projs = fetch_proj()
#     srcs = fetch_src()
#     srcs_meta = fetch_src_meta()

#     html = str()

#     if proj_id:
#         i = 0
#         for src_id in srcs.keys():

#             if srcs[src_id][0] == projs[proj_id]:
#                 i += 1
#                 html += "<br><p><b>Source {}: {}-{}</b></p>".format(i,
#                         projs[proj_id],srcs[src_id][1])

#                 for attr, val in srcs_meta[src_id].items():
#                     html += "<p style='margin-left: 40px'>"
#                     html += attr + ": " + val
#                     html += "</p>"


#     return jsonify(result=html)




@app.route('/_file2db', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def file2db():

    def current_time():
        '''   2017-8-17  14:35    '''
        d = datetime.datetime.now()
        return d.strftime('%Y-%m-%d_%H:%M:%S')


    error_logging = open("corpus_inputting_error_log", "a")


    filename = request.args.get('fn', None)


    try:                                                   ####tk####
        r = docx2html(filename)

    except TimeoutError:                                                       ####tk####
        current_time = current_time()                                          ####tk####
        error_logging.write(current_time+"\n")                                 ####tk####
        error_logging.write("DOCNAME: {}\n".format(filename))                         ####tk####
        error_logging.write("Type: Timeout\n\n")                            ####tk####

        #return render_template("exception.html")                               ####tk####
        #return jsonify(result=False)#  docx2html_exception()                            ####tk####
        r = False
        error_logging.close()          

    except Exception as e:                                                     ####tk####
        current_time = current_time()                                          ####tk####
        error_logging.write(current_time+"\n")                                 ####tk####
        error_logging.write("DOCNAME: {}\n".format(filename))                         ####tk####
        error_logging.write("Type: {type}\n".format(type=type(e)))               ####tk####
        error_logging.write("Args: {args}\n".format(args=e.args))                ####tk####

        if hasattr(e, 'message'):
            error_logging.write("Message: {message}\n".format(message=e.message))    ####tk####
            
        error_logging.write("Error: {error}\n\n".format(error=e))             ####tk####
        error_logging.close()          
        r = False
        #return render_template("exception.html")                            ####tk####
        #return jsonify(result=False)#docx2html_exception()                            ####tk####



#     vr, filename, wn, wn_dtls = validateFile(current_user.id, filename)
    
#     return jsonify(result=render_template('validation-report.html',
#                     vr=vr, wn=wn, wn_dtls=wn_dtls, filename=filename))

    # return jsonify(result=False)

    #else:                              ####tk####
    return jsonify(result=r)

    # finally:                           ####tk####
    #     error_logging.close()          ####tk####

################################################################################


################################################################################
# VIEWS
################################################################################
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('welcome.html')

# @app.route('/ili', methods=['GET', 'POST'])
# def ili_welcome(name=None):
#     return render_template('ili_welcome.html')

# @app.route('/omw', methods=['GET', 'POST'])
# def omw_welcome(name=None):
#     lang_id, lang_code = fetch_langs()
#     src_meta=fetch_src_meta()
#     ### sort by language, project version (Newest first)
#     src_sort=od()
#     keys=list(src_meta.keys())
#     keys.sort(key=lambda x: src_meta[x]['version'],reverse=True)
#     keys.sort(key=lambda x: src_meta[x]['id'])
#     keys.sort(key=lambda x: lang_id[lang_code['code'][src_meta[x]['language']]][1])
#     for k in keys:
#         src_sort[k] =  src_meta[k]
#     return render_template('omw_welcome.html',
#                            src_meta=src_sort,
#                            lang_id=lang_id,
#                            lang_code=lang_code)

# @app.route('/omw_wns', methods=['GET', 'POST'])
# def omw_wns(name=None):
#     src_meta=fetch_src_meta()
#     stats = []
#     lang_id, lang_code = fetch_langs()
#     ### sort by language name (1), id, version (FIXME -- reverse version)
#     for src_id in sorted(src_meta, key = lambda x: (                                                    lang_id[lang_code['code'][src_meta[x]['language']]][1],
#                                                                                                         src_meta[x]['id'],
#                                                                                                         src_meta[x]['version'])):
#         stats.append((src_meta[src_id], fetch_src_id_stats(src_id)))
#     return render_template('omw_wns.html',
#                            stats=stats,
#                            lang_id=lang_id,
#                            lang_code=lang_code)


@app.route("/useradmin",methods=["GET"])
@login_required(role=99, group='admin')
def useradmin():
    users = fetch_allusers()
    return render_template("useradmin.html", users=users)

@app.route("/langadmin",methods=["GET"])
@login_required(role=99, group='admin')
def langadmin():
    lang_id, lang_code = fetch_langs()
    return render_template("langadmin.html", langs=lang_id)

@app.route("/projectadmin",methods=["GET"])
@login_required(role=99, group='admin')
def projectadmin():
    projs = fetch_proj()
    return render_template("projectadmin.html", projs=projs)


sys_tag_dic = {}
sys_tag_dic["LongSentence"] = ""
sys_tag_dic["InformalWord"] = ""
sys_tag_dic["Contraction"] = ""
sys_tag_dic["NoParse"] = ""

def tag2text(tag):
    if tag in sys_tag_dic:
        return sys_tag_dic[tag]
    else:
        return "Another kinds of error"

@app.route("/check_gold",methods=["GET"])
def check_gold():
    maxgold=274
    error_sys_dic = {}
    for docid in range(1, maxgold):  # range(1, 274)
        error_sys_dic[docid] = check_doc(docid, "gold")

    annotated_docids = [did[0] for did in g.gold.execute("SELECT DISTINCT docid FROM sent WHERE comment IS NOT '' ORDER BY docid")]


    ''' extract "LongSentence" and "Informal" from error_sys_dic '''
    #sys_long_set = set()
    #sys_informal_set = set()
    sys_error2pstn = dd(set)
    for docid in annotated_docids:
        if not docid in error_sys_dic.keys():
            continue
        for sid in error_sys_dic[docid].keys():
            for eid in error_sys_dic[docid][sid].keys():
                if error_sys_dic[docid][sid][eid]["label"] == "LongSentence":
                    #sys_long_set.add((docid, sid))
                    sys_error2pstn["LongSentence"].add((docid, sid))
                elif error_sys_dic[docid][sid][eid]["label"] == "VeryLongSentence":
                    sys_error2pstn["LongSentence"].add((docid, sid))
                elif error_sys_dic[docid][sid][eid]["label"] == "Informal":
                    pstn = int(error_sys_dic[docid][sid][eid]["position"])
                    #sys_informal_set.add((docid, sid, pstn))
                    sys_error2pstn["Informal"].add((docid, sid, pstn))
                elif error_sys_dic[docid][sid][eid]["label"] == "Contraction":  # put "position" info if you have word id or something 
                    sys_error2pstn["Contraction"].add((docid, sid))
                elif error_sys_dic[docid][sid][eid]["label"] in set(["comm", "ques"]):
                    sys_error2pstn["commques"].add((docid, sid))
                else:
                    label = error_sys_dic[docid][sid][eid]["label"]
                    sys_error2pstn[label].add((docid, sid))


    ''' extract data from gold corpus '''
    at_label_dic = dd(lambda: dd(lambda: dd(set)))
    #at_long_set = set()
    #at_informal_set = set()
    at_error2pstn = dd(set)
    for docid, sid, label in g.gold.execute("SELECT sent.docid, sent.sid, error.label FROM sent INNER JOIN error ON sent.sid=error.sid").fetchall():
        if label == "SLong":
            at_label_dic[docid][sid][label].add("all")
            #at_long_set.add((docid, sid))
            at_error2pstn["SLong"].add((docid, sid))
        elif label == "StyWch":
            for eid, in g.gold.execute('''SELECT eid FROM error WHERE label='StyWch' AND sid=?''', (sid,)).fetchall():
                for wid, in g.gold.execute('''SELECT wid FROM ewl WHERE sid=? AND eid=?''', (sid, eid)).fetchall():
                    at_label_dic[docid][sid][label].add(wid)
                    at_error2pstn["StyWch"].add((docid, sid, wid))

                    # for lemma, in g.gold.execute('''SELECT lemma FROM word WHERE sid=? AND wid=?''', (sid, wid)).fetchall():
                    #     if lemma in ['hassle', 'tackle']:
                    #         at_label_dic[docid][sid][label].add(wid)
                    #         #at_informal_set.add((docid, sid, wid))
                    #         at_error2pstn["StyWch(hassle/tackle)"].add((docid, sid, wid))
                    #     else:
                    #         at_label_dic[docid][sid][label].add("all")

                            # at_error2pstn[label].add((docid, sid))
        elif label == "StyContr":
            at_label_dic[docid][sid][label].add(wid)
            at_error2pstn["StyContr"].add((docid, sid))
        elif label == "StyMood":
            at_label_dic[docid][sid][label].add("all")
            at_error2pstn["StyMood"].add((docid, sid))
        else:
            at_label_dic[docid][sid][label].add("all")
            
            at_error2pstn[label].add((docid, sid))

    #print(sys_informal_set)
    #print(at_informal_set)

    ''' create html '''
    check_gold_html = ""

    html_head = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">\n'
    html_head += '<html>\n<head>\n'
    html_head += '<!-- This file was created by "check_gold" -->\n'
    html_head += '    <title>System VS Annotators</title>\n'
    html_head += '    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=utf-8">\n'
    #html_head += '    <script src=".js" language="javascript"></script>\n'
    html_head += '</head>\n'

    check_gold_html += html_head
    check_gold_html += '''<hr>\n'''

    ''' show the tags from system and their frequency '''
    sys_tag_freq_heading = '''<h3>Numbers of tags from system</h3>\n'''
    check_gold_html += sys_tag_freq_heading
    system_tags = dd(int)
    for docid in error_sys_dic.keys():
        for sid in error_sys_dic[docid].keys():
            for eid in error_sys_dic[docid][sid].keys():
                tag = error_sys_dic[docid][sid][eid]["label"]
                system_tags[tag] += 1
    for tag, occ in sorted(system_tags.items(), key=lambda x:x[1], reverse=True):
        check_gold_html += '''<b>{0}</b>: {1}<br />\n'''.format(tag, occ)

    check_gold_html += '<br /><hr>\n'

    ''' long sentence and informal words static '''
    numbers_heading =  '''<h3>Numbers of long sentence and informal words (hastle/tackle)</h3>\n'''
    #allover_sents_number = g.gold.execute('''SELECT COUNT(sid) FROM sent WHERE docid IN ('{}')'''.format("', '".join(annotated_docids))).fetchone()[0]
    long_sub_heading = '''<h5>"LongSentence" by System  VS  "SLong" by Annotators</h5>\n'''
    allover_sents_number = g.gold.execute('''SELECT COUNT(sid) FROM sent WHERE docid IN {}'''.format(tuple(annotated_docids))).fetchone()[0]
    allover_sents_string = '''Allover sentences (in annotated documents): {}<br /><br />\n'''.format(allover_sents_number)
    S_and_A_string = '''System and Annotators agrees (long sentence): {}<br />\n'''.format(len(sys_error2pstn["LongSentence"] & at_error2pstn["SLong"]))
    S_only_string = '''System only: {}<br />\n'''.format(len(sys_error2pstn["LongSentence"] - at_error2pstn["SLong"]))
    A_only_string = '''Annotators only: {}<br />\n'''.format(len(at_error2pstn["SLong"] - sys_error2pstn["LongSentence"]))
    N_string = '''Non of them: {}<br /><br />\n\n'''.format(allover_sents_number - len(sys_error2pstn["LongSentence"] | at_error2pstn["SLong"]))
    
    
    long_sents = '''<h5>Actual sentences</h5>\n'''
    long_sents += '''<b>System and Annotators agree:</b><br /><br />\n''' 
    for lg in sorted(sys_error2pstn["LongSentence"]&at_error2pstn["SLong"]):
        lg_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (lg[1],)).fetchone()[0]
        long_sents += escape(lg_sent)
        long_sents += ''' (docid={})'''.format(lg[0])
        long_sents += '<br /><br />\n'
    long_sents += '''<b>System only:</b><br /><br />\n''' 
    for lg in sorted(sys_error2pstn["LongSentence"] - at_error2pstn["SLong"]):
        lg_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (lg[1],)).fetchone()[0]
        long_sents += escape(lg_sent)
        long_sents += ''' (docid={})'''.format(lg[0])
        long_sents += '<br /><br />\n'

    
    long_static_string = numbers_heading+long_sub_heading+allover_sents_string+S_and_A_string+S_only_string+A_only_string+N_string+long_sents+'''<br /><br />\n'''

    check_gold_html += long_static_string

    ''' hastle & tackle  '''
    informal_sub_heading = '''<h5>"Informal" by System  VS  "StyWch" by Annotators</h5>\n'''
    informal_sub_heading += '''<h6>(Target words: "hassle" and "tackle")</h6>\n'''
    allover_informal_number = g.gold.execute('''SELECT COUNT(word.lemma) FROM word INNER JOIN sent ON word.sid=sent.sid WHERE (word.lemma IN ('hassle', 'tackle')) AND (sent.docid IN {})'''.format(tuple(annotated_docids))).fetchone()[0]
    allover_informal_string = '''Allover 'hassle's and 'tackle's (in annotated documents): {}<br /><br />\n'''.format(allover_informal_number)
    S_and_A_string = '''System and Annotators agrees (informal): {}<br />\n'''.format(len(sys_error2pstn["Informal"] & at_error2pstn["StyWch"]))
    S_only_string = '''System only: {}<br />\n'''.format(len(sys_error2pstn["Informal"] - at_error2pstn["StyWch"]))
    A_only_string = '''Annotators only: {}<br />\n'''.format(len(at_error2pstn["StyWch"] - sys_error2pstn["Informal"]))
    N_string = '''Non of them: {}<br /><br />\n\n'''.format(allover_informal_number - len(sys_error2pstn["Informal"] | at_error2pstn["StyWch"]))

    informal_sents = '''<h5>Actual sentences</h5>\n'''
    informal_sents += '''<b>System and Annotators agree:</b><br /><br />\n''' 
    for ifr in sorted(sys_error2pstn["Informal"]&at_error2pstn["StyWch"]):
        ifr_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (ifr[1],)).fetchone()[0]
        informal_sents += escape(ifr_sent)
        informal_sents += ''' (docid={})'''.format(ifr[0])
        informal_sents += '<br /><br />\n'
    informal_sents += '''<b>System only:</b><br /><br />\n'''
    for ifr in sorted(sys_error2pstn["Informal"] - at_error2pstn["StyWch"]):
        ifr_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (ifr[1],)).fetchone()[0]
        informal_sents += escape(ifr_sent)
        informal_sents += ''' (docid={})'''.format(ifr[0])
        informal_sents += '<br /><br />\n'



    informal_static_string = informal_sub_heading+allover_informal_string+S_and_A_string+S_only_string+A_only_string+N_string+informal_sents+'''<br /><hr>\n\n'''
    check_gold_html += informal_static_string


    ''' Contractions '''
    contraction_sub_heading = '''<h5>"Contraction" by System  VS  "StyContr" by Annotators</h5>\n'''
    # allover_sents_string can be used here.
    S_and_A_string = '''System and Annotators agrees: {}<br />\n'''.format(len(sys_error2pstn["Contraction"] & at_error2pstn["StyContr"]))
    S_only_string = '''System only: {}<br />\n'''.format(len(sys_error2pstn["Contraction"] - at_error2pstn["StyContr"]))
    A_only_string = '''Annotators only: {}<br />\n'''.format(len(at_error2pstn["StyContr"] - sys_error2pstn["Contraction"]))
    N_string = '''Non of them: {}<br /><br />\n\n'''.format(allover_informal_number - len(sys_error2pstn["Contraction"] | at_error2pstn["StyContr"]))

    contraction_sents = '''<h5>Actual sentences</h5>\n'''
    contraction_sents += '''<b>System and Annotators agree:</b><br /><br />\n'''
    for cnt in sorted(sys_error2pstn["Contraction"]&at_error2pstn["StyContr"]):
        cnt_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (cnt[1],)).fetchone()[0]
        contraction_sents += escape(cnt_sent)
        contraction_sents += ''' (docid={})'''.format(cnt[0])
        contraction_sents += '<br /><br />\n'
    contraction_sents += '''<b>System only:</b><br /><br />\n'''
    for cnt in sorted(sys_error2pstn["Contraction"] - at_error2pstn["StyContr"]):
        cnt_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (cnt[1],)).fetchone()[0]
        contraction_sents += escape(cnt_sent)
        contraction_sents += ''' (docid={})'''.format(cnt[0])
        contraction_sents += '<br /><br />\n'
    contraction_sents += '''<b>Annotators only:</b><br /><br />\n'''
    for cnt in sorted(at_error2pstn["StyContr"] - sys_error2pstn["Contraction"]):
        cnt_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (cnt[1],)).fetchone()[0]
        contraction_sents += escape(cnt_sent)
        contraction_sents += ''' (docid={})'''.format(cnt[0])
        contraction_sents += '<br /><br />\n'
    contraction_sents += '''<b>None of them:</b><br /><br />\n'''
    for cnt in sorted(sys_error2pstn["Contraction"] | at_error2pstn["StyContr"]):
        cnt_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (cnt[1],)).fetchone()[0]
        contraction_sents += escape(cnt_sent)
        contraction_sents += ''' (docid={})'''.format(cnt[0])
        contraction_sents += '<br /><br />\n'

    contraction_static_string = contraction_sub_heading+allover_sents_string+S_and_A_string+S_only_string+A_only_string+N_string+contraction_sents+'''<br /><hr>\n\n'''
    check_gold_html += contraction_static_string

    ''' Mood '''
    mood_sub_heading = '''<h5>"comm" and "ques" by System  VS  "StyMood" by Annotators</h5>\n'''
    # allover_sents_string can be used here.
    S_and_A_string = '''System and Annotators agrees: {}<br />\n'''.format(len(sys_error2pstn["commques"] & at_error2pstn["StyMood"]))
    S_only_string = '''System only: {}<br />\n'''.format(len(sys_error2pstn["commques"] - at_error2pstn["StyMood"]))
    A_only_string = '''Annotators only: {}<br />\n'''.format(len(at_error2pstn["StyMood"] - sys_error2pstn["commques"]))
    N_string = '''Non of them: {}<br /><br />\n\n'''.format(allover_informal_number - len(sys_error2pstn["commques"] | at_error2pstn["StyMood"]))

    mood_sents = '''<h5>Actual sentences</h5>\n'''
    mood_sents += '''<b>System and Annotators agree:</b><br /><br />\n'''
    for md in sorted(sys_error2pstn["commques"]&at_error2pstn["StyMood"]):
        md_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (md[1],)).fetchone()[0]
        mood_sents += escape(md_sent)
        mood_sents += ''' (docid={})'''.format(md[0])
        mood_sents += '<br /><br />\n'
    mood_sents += '''<b>System only:</b><br /><br />\n'''
    for md in sorted(sys_error2pstn["commques"] - at_error2pstn["StyMood"]):
        md_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (md[1],)).fetchone()[0]
        mood_sents += escape(md_sent)
        mood_sents += ''' (docid={})'''.format(md[0])
        mood_sents += '<br /><br />\n'
    mood_sents += '''<b>Annotators only:</b><br /><br />\n'''
    for md in sorted(at_error2pstn["StyMood"] - sys_error2pstn["commques"]):
        md_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (md[1],)).fetchone()[0]
        mood_sents += escape(md_sent)
        mood_sents += ''' (docid={})'''.format(md[0])
        mood_sents += '<br />\n'
    mood_sents += '''<b>None of them:</b><br /><br />\n'''
    for md in sorted(sys_error2pstn["commques"] | at_error2pstn["StyMood"]):
        md_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (md[1],)).fetchone()[0]
        mood_sents += escape(md_sent)
        mood_sents += ''' (docid={})'''.format(md[0])
        mood_sents += '<br />\n'

    mood_static_string = mood_sub_heading+allover_sents_string+S_and_A_string+S_only_string+A_only_string+N_string+mood_sents+'''<br /><hr>\n\n'''
    check_gold_html += mood_static_string


    ''' Other labels (System)'''
    other_sub_heading = '''<h5>Other errors by System</h5>\n'''
    for label in sorted(sys_error2pstn.keys()):
        if label in set(["LongSentence", "Informal", "Contraction"]):
            continue
        label_heading = '''<h5><b>{}</b></h5>\n'''.format(label)
        oth_sents = ""
        for oth in sorted(sys_error2pstn[label]):
            oth_sent = g.gold.execute('''SELECT sent FROM sent WHERE sid=?''', (oth[1],)).fetchone()[0]
            oth_sents += escape(oth_sent)
            oth_sents += ''' (docid={0}, orig_sid={1})<br />\n'''.format(oth[0], oth[1])
            oth_sents += '''&nbsp;&nbsp;Annotator(s):  '''
            if len(at_label_dic[oth[0]][oth[1]].keys()) > 0:
                for at_label in at_label_dic[oth[0]][oth[1]].keys():
                    oth_sents += '''{}; '''.format(at_label)
            else:
                oth_sents += '''None'''
            oth_sents += '<br /><br />\n'

    oth_static_string = other_sub_heading+label_heading+oth_sents+'''<br /><hr>\n\n'''
    check_gold_html += oth_static_string

    ''' sents with error '''
    s_e_heading = '''<h3>Sentences with error</h3><br />\n'''
    check_gold_html += s_e_heading

    for docid in range(1, maxgold):    # range(1, 274)
        sys_docid = False
        at_docid = False
        if (not docid in error_sys_dic.keys()) and (not docid in at_label_dic.keys()):
            continue
        if docid in error_sys_dic.keys():
            sys_docid = True
        if docid in at_label_dic.keys():
            at_docid = True
        only_in_string = ""
        if not docid in annotated_docids:
            only_in_string = ' (not annotated)'
        doc_top = '''\n\n<b>DOCID= {0}</b>{1}<br /><br />\n'''.format(docid, only_in_string)

        check_gold_html += doc_top

        sents = fetch_sents_by_docid(docid, "gold")
        sid_min = min(sents.keys())
        sid_max = max(sents.keys())

        for sid in range(sid_min, sid_max+1):
            sys_sid = False
            at_sid = False
            #if ((sys_docid == False) or (not sid in error_sys_dic[docid].keys())) and \
            #   ((at_docid == False) or (not sid in at_label_dic[docid].keys())):
            #    continue
            #sent_string = escape(sents[sid][2])+'<br />\n'

            #check_gold_html += sent_string

            error_type_string = ""
            ''' errors from system '''
            if sys_docid == True:
                if sid in error_sys_dic[docid].keys():
                    sys_sid = True
                    error_type_string += "&nbsp;&nbsp;System:   "
                    sys_errors = []
                    for eid in error_sys_dic[docid][sid].keys():
                        sys_errors.append(error_sys_dic[docid][sid][eid]["label"])

                    if "LongSentence" in sys_errors:
                        error_type_string += '''<font color="red">LongSentence</font>; '''
                        sys_errors.remove("LongSentence")
                    if "VeryLongSentence" in sys_errors:
                        error_type_string += '''<font color="red">VeryLongSentence</font>; '''
                        sys_errors.remove("VeryLongSentence")
                    if "Informal" in sys_errors:
                        error_type_string += '''<font color="orange">Informal</font>; '''
                        sys_errors.remove("Informal")
                    if "Contraction" in sys_errors:
                        error_type_string += '''<font color="blue">Contraction</font>; '''
                        sys_errors.remove("Contraction")
                    if "NoParse" in sys_errors:
                        error_type_string += '''<font color="green">NoParse</font>; '''
                        sys_errors.remove("NoParse")
                    if "comm" in sys_errors:
                        error_type_string += '''<font color="pink">comm</font>; '''
                        sys_errors.remove("comm")
                    if "ques" in sys_errors:
                        error_type_string += '''<font color="pink">ques</font>; '''
                        sys_errors.remove("ques")
                    for sys_error in sorted(sys_errors):
                        error_type_string += '''{}; '''.format(sys_error)

                    error_type_string += '''<br />\n'''

            ''' errors from annotators '''
            if at_docid == True:
                if sid in at_label_dic[docid].keys():
                    at_sid = True
                    error_type_string += "&nbsp;&nbsp;Annotator(s): "
                    at_labels = [atl for atl in at_label_dic[docid][sid].keys()]
                    if "SLong" in at_labels:
                        error_type_string += '''<font color="red">SLong</font>; '''
                        at_labels.remove("SLong")
                    if "StyWch" in at_labels:
                        error_type_string += '''<font color="orange">StyWch</font>; '''
                        at_labels.remove("StyWch")
                    if "StyContr" in at_labels:
                        error_type_string += '''<font color="blue">StyContr</font>; '''
                        at_labels.remove("StyContr")
                    if "StyMood" in at_labels:
                        error_type_string += '''<font color="pink">StyMood</font>; '''
                        at_labels.remove("StyMood")
                    #if "ANY" in at_label_dic[docid][sid].keys():
                    #    any_labels = sorted([lb for lb in at_label_dic[docid][sid]["ANY"]])
                    #    for any_label in any_labels:
                    #        error_type_string += '''{}; '''.format(any_label)
                    for at_label in sorted(at_labels):
                        error_type_string += '''{}; '''.format(at_label)


                    error_type_string += '''<br />\n'''

                    #error_type_string += '''<br />\n'''

            if (sys_sid == True) or (at_sid == True):
                sent_string = escape(sents[sid][2])+'<br />\n'
                check_gold_html += sent_string
                check_gold_html += error_type_string
                check_gold_html += '<br />\n'

        check_gold_html += '''<hr>\n'''

    check_gold_html += '</html>'

    f = codecs.open("check_gold.html", "w", "utf-8")
    f.write(check_gold_html)

    return render_template("check_gold_result.html")



@app.route('/allconcepts', methods=['GET', 'POST'])
def allconcepts():
    ili, ili_defs = fetch_ili()
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)

@app.route('/temporary', methods=['GET', 'POST'])
def temporary():
    ili = fetch_ili_status(2)
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/deprecated', methods=['GET', 'POST'])
def deprecated():
    ili = fetch_ili_status(0)
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/ili/concepts/<c>', methods=['GET', 'POST'])
def concepts_ili(c=None):
    c = c.split(',')
    ili, ili_defs = fetch_ili(c)
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))

    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/ili/search', methods=['GET', 'POST'])
@app.route('/ili/search/<q>', methods=['GET', 'POST'])
def search_ili(q=None):

    if q:
        query = q
    else:
        query = request.form['query']

    src_id = fetch_src()
    kind_id = fetch_kind()
    status_id = fetch_status()

    ili = dict()
    for c in query_omw("""SELECT * FROM ili WHERE def GLOB ?
                         """, [query]):
        ili[c['id']] = (kind_id[c['kind_id']], c['def'],
                        src_id[c['origin_src_id']], c['src_key'],
                        status_id[c['status_id']], c['superseded_by_id'],
                             c['t'])


    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/upload', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def upload():
    return render_template('upload.html')


@app.route('/metadata', methods=['GET', 'POST'])
def metadata():
    return render_template('metadata.html')

@app.route('/join', methods=['GET', 'POST'])
def join():
    return render_template('join.html')


@app.route('/ili/validation-report', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def validationReport():

    vr, filename, wn, wn_dtls = validateFile(current_user.id)

    return render_template('validation-report.html',
                           vr=vr, wn=wn, wn_dtls=wn_dtls,
                           filename=filename)

@app.route('/report', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def report():
    passed, filename = uploadFile(current_user.id)
    return render_template('report.html',
                           passed=passed,
                           filename=filename)


@app.route('/omw/search', methods=['GET', 'POST'])
@app.route('/omw/search/<lang>,<lang2>/<q>', methods=['GET', 'POST'])
def search_omw(lang=None, q=None):

    if lang and q:
        lang_id = lang
        lang_id2 = lang2
        query = q
    else:
        lang_id = request.form['lang']
        lang_id2 = request.form['lang2']
        query = request.form['query']
    sense = dd(list)
    lang_sense = dd(lambda: dd(list))

    # GO FROM FORM TO SENSE
    for s in query_omw("""
        SELECT s.id as s_id, ss_id,  wid, fid, lang_id, pos_id, lemma
        FROM (SELECT w_id as wid, form.id as fid, lang_id, pos_id, lemma
              FROM (SELECT id, lang_id, pos_id, lemma
                    FROM f WHERE lemma GLOB ? AND lang_id in (?,?)) as form
              JOIN wf_link ON form.id = wf_link.f_id) word
        JOIN s ON wid=w_id
        """, [query,lang_id,lang_id2]):


        sense[s['ss_id']] = [s['s_id'], s['wid'], s['fid'],
                             s['lang_id'], s['pos_id'], s['lemma']]


        lang_sense[s['lang_id']][s['ss_id']] = [s['s_id'], s['wid'], s['fid'],
                                                s['pos_id'], s['lemma']]


    pos = fetch_pos()
    lang_dct, lang_code = fetch_langs()
    ss, senses, defs, exes, links = fetch_ss_basic(sense.keys())

    labels = fetch_labels(lang_id, set(senses.keys()))


    resp = make_response(render_template('omw_results.html',
                                         langsel = int(lang_id),
                                         langsel2 = int(lang_id2),
                                         pos = pos,
                                         lang_dct = lang_dct,
                                         sense=sense,
                                         senses=senses,
                                         ss=ss,
                                         links=links,
                                         defs=defs,
                                         exes=exes,
                                         labels=labels))

    resp.set_cookie('selected_lang', lang_id)
    resp.set_cookie('selected_lang2', lang_id2)
    return resp

@app.route('/omw/core', methods=['GET', 'POST'])
def omw_core():  ### FIXME add lang as a paramater?
    return render_template('omw_core.html')


@app.route('/omw/concepts/<ssID>', methods=['GET', 'POST'])
@app.route('/omw/concepts/ili/<iliID>', methods=['GET', 'POST'])
def concepts_omw(ssID=None, iliID=None):

    if iliID:
        ss_ids = f_ss_id_by_ili_id(iliID)
        ili, ilidefs = fetch_ili([iliID])
    else:
        ss_ids = [ssID]
        ili, ili_defs = dict(), dict()
    pos = fetch_pos()
    langs_id, langs_code = fetch_langs()
    
    ss, senses, defs, exes, links = fetch_ss_basic(ss_ids)
    if (not iliID) and int(ssID) in ss:
        iliID = ss[int(ssID)][0]
        ili, ilidefs = fetch_ili([iliID])
        
    sss = list(ss.keys())
    for s in links:
        for l in links[s]:
            sss.extend(links[s][l])
    selected_lang = request.cookies.get('selected_lang')
    labels = fetch_labels(selected_lang, set(sss))

    ssrels = fetch_ssrel()

    ss_srcs=fetch_src_for_ss_id(ss_ids)
    src_meta=fetch_src_meta()
    core_ss, core_ili = fetch_core()
    return render_template('omw_concept.html',
                           ssID=ssID,
                           iliID=iliID,
                           pos = pos,
                           langs = langs_id,
                           senses=senses,
                           ss=ss,
                           links=links,
                           ssrels=ssrels,
                           defs=defs,
                           exes=exes,
                           ili=ili,
                           selected_lang = selected_lang,
                           selected_lang2 = request.cookies.get('selected_lang2'),
                           labels=labels,
                           ss_srcs=ss_srcs,
                           src_meta=src_meta,
                           core=core_ss)


@app.route('/omw/senses/<sID>', methods=['GET', 'POST'])
def omw_sense(sID=None):
    langs_id, langs_code = fetch_langs()
    pos = fetch_pos()
    sense =  fetch_sense(sID)
    forms=fetch_forms(sense[3])
    selected_lang = request.cookies.get('selected_lang')
    labels= fetch_labels(selected_lang,[sense[4]])
    src_meta= fetch_src_meta()
    src_sid=fetch_src_for_s_id([sID])
    return render_template('omw_sense.html',
                           s_id = sID,
                           sense = sense,
                           forms=forms,
                           langs = langs_id,
                           pos = pos,
                           labels = labels,
                           src_sid = src_sid,
                           src_meta = src_meta)

    
# URIs FOR ORIGINAL CONCEPT KEYS, BY INDIVIDUAL SOURCES
@app.route('/omw/src/<src>/<originalkey>', methods=['GET', 'POST'])
def src_omw(src=None, originalkey=None):

    try:
        proj = src[:src.index('-')]
        ver  = src[src.index('-')+1:]
        src_id = f_src_id_by_proj_ver(proj, ver)
    except:
        src_id = None

    if src_id:
        ss = fetch_ss_id_by_src_orginalkey(src_id, originalkey)
    else:
        ss = None

    return concepts_omw(ss)


## show wn statistics
##
##
@app.route('/omw/src/<src>', methods=['GET', 'POST'])
def omw_wn(src=None):
    if src:
        try:
            proj = src[:src.index('-')]
            ver  = src[src.index('-')+1:]
            src_id = f_src_id_by_proj_ver(proj, ver)
        except:
            src_id = None
        srcs_meta = fetch_src_meta()
        src_info = srcs_meta[src_id]

    return render_template('omw_wn.html',
                           wn = src,
                           src_id=src_id,
                           src_info=src_info,
                           ssrel_stats=fetch_ssrel_stats(src_id),
                           pos_stats= fetch_src_id_pos_stats(src_id),
                           src_stats=fetch_src_id_stats(src_id))

@app.route('/omw/src-latex/<src>', methods=['GET', 'POST'])
def omw_wn_latex(src=None):
    if src:
        try:
            proj = src[:src.index('-')]
            ver  = src[src.index('-')+1:]
            src_id = f_src_id_by_proj_ver(proj, ver)
        except:
            src_id = None
        srcs_meta = fetch_src_meta()
        src_info = srcs_meta[src_id]

    return render_template('omw_wn_latex.html',
                           wn = src,
                           src_id=src_id,
                           src_info=src_info,
                           ssrel_stats=fetch_ssrel_stats(src_id),
                           pos_stats= fetch_src_id_pos_stats(src_id),
                           src_stats=fetch_src_id_stats(src_id))



@app.context_processor
def utility_processor():
    def scale_freq(f, maxfreq=1000):
        if f > 0:
            return 100 + 100 * log(f)/log(maxfreq)
        else:
            return 100
    return dict(scale_freq=scale_freq)



## show proj statistics
#for proj in fetch_proj/


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True)
