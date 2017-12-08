#!/usr/bin/python

import feedparser
import subprocess
import ConfigParser
import re
import datetime
import smtplib
import datetime
from instapush import Instapush, App

Config = ConfigParser.ConfigParser()
Config.read("config.ini")

log_file = open(Config.get('Logging','path') + "/pytorrent" + str(datetime.datetime.now().date().year) + "-" + str(datetime.datetime.now().date().month) + ".log","a")
log_level = int(Config.get('Logging','level'))	#0 = no log, 1 = normal, 2 = verbose, 3 = super
app = App(appid=Config.get('PushNotification','appid'), secret=Config.get('PushNotification','secret'))

def loG(level,s):
	if level <= log_level:
		msg = '[' + str(datetime.datetime.now()) + '][L' + str(level) + '] ' + str(s)
		log_file.write(msg + '\n')
		print msg
	return

def dim(s,toMatch,noMatch,needed):     #DoesItMatch?
	if toMatch not in s:
                loG(3,"[DiM] __" + s + "__")
                loG(3,"[Dim] nope! title doesn't match: " + toMatch)
                return False
	if any(x in s for x in noMatch):
		loG(3,"[DiM] __" + s + "__")
		loG(3,"[Dim] nope! Found one of following noMatch: " + str(noMatch))
		return False
	if not all(x in s for x in needed):
		loG(3,"[DiM] __" + s + "__")
		loG(3,"[Dim] nope! Cant find some of the following: " + str(needed))
		return False
	loG(3,"[DiM] __" + s + "__")
	loG(3,"[Dim] yepe! found it!")
	return True

def send_email(subject, body):
    recipient = Config.get('Mail','toRecipient')
    gmail_user = Config.get('Mail','fromGmailUser')
    gmail_pwd = Config.get('Mail','fromGmailPwd')
    FROM = Config.get('Mail','fromGmailUser')
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nMIME-Version: 1.0\nContent-Type: text/html\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print 'successfully sent the mail'
    except:
        print "failed to send mail"

loG(1,'------------------------------------------------------------------------------------------')
d = feedparser.parse(Config.get('Feed','url'))

Series = ConfigParser.ConfigParser()
Series.read("series.ini")
utili = Series.sections()
a = 0
b = 0
output_file = open(".added_history","r+")
added_history = output_file.read()
turl = Config.get('Transmission','url')
tusr = Config.get('Transmission','usr')
tpwd = Config.get('Transmission','pwd')
SESSID = subprocess.check_output("curl --silent --anyauth --user " + tusr +":" + tpwd + " " + turl + " | sed 's/.*<code>//g;s/<\/code>.*//g'", shell=True)
loG(1,SESSID)
if "X-Transmission-Session-Id:" not in SESSID:
	loG(1,"ERROR - SESSID non valido!!")
	app.notify(event_name='error', trackers={ 'message': 'SESSID non valido!!'})
	quit()
emailsub = '[pyTorrent] Torrent aggiunto!'
emailmsg = '<h1>pyTorrent</h1>'
#loG(1,d.entries)
for ee in d.entries:
	loG(2,'__Valutando__ ' + ee.title)
	for serie in utili:
		path = Series.get(serie,'path')
		ignorez = Series.get(serie, 'ignore')
		nyd = Series.get(serie, 'needed')
		if dim(ee.title,serie,ignorez.split(','),nyd):
			a += 1
			loG(1,'    Published: ' + ee.published)
			loG(1,'    Title:     ' + ee.title)
			loG(1,'    Filename:  ' + ee.torrent_filename)
			loG(1,'    HASH:      ' + ee.torrent_infohash)
			if ee.torrent_infohash not in added_history:
				loG(1,"    ** aggiungo **")
				m = re.search(r"(?<=S)\d\d(?=E)", ee.title)
				dl_dir = path + '/s' + m.group(0)
				loG(1,'    ' + dl_dir)
				cmd = "curl --silent --anyauth --user "+tusr+":"+tpwd+" --header \""+SESSID+"\" "+turl+" -d \"{\\\"method\\\":\\\"torrent-add\\\",\\\"arguments\\\":{\\\"paused\\\":false,\\\"filename\\\":\\\"" + ee.torrent_magneturi + "\\\",\\\"download-dir\\\":\\\""+dl_dir+"\\\"}}\""
#				AAA = subprocess.call(cmd, shell=True)
				AAA = subprocess.check_output(cmd, shell=True)
				loG(2,AAA)
				if '"result":"success"' in AAA:
					output_file.write(ee.torrent_infohash + '\t' + ee.title + '\n')
					b += 1
					app.notify(event_name='added-torrent', trackers={ 'filename': ee.torrent_filename})
					emailmsg += '<p>Titolo: <strong>'+ee.title+'</strong></p><p>Filename: <strong>'+ee.torrent_filename+'</strong></p><hr>'

loG(1,'considerati: ' + str(a))
loG(1,'aggiunti: ' + str(b))
loG(1,'')

if b > 0:
#	send_email(emailsub,emailmsg)

log_file.close()
output_file.close()
