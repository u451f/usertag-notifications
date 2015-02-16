####################################################
# Query the Debian Ultimate Database (UDD) for
# new usertags on bugs and send email notifications
# to the user.
# To install a cronjob on alioth run `crontab -e`
# Also see https://wiki.debian.org/AppArmor/Reportbug
#####################################################
# Copyright 2015 u <u@451f.org>
# Released under the GPLv=3
# Made during rd9 of the GNOME Outreach program
#####################################################

# global configuration
filename = "usertags.state"
user = "pkg-apparmor-team@lists.alioth.debian.org"
bdourl = "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug="
usertagurl = "https://udd.debian.org/cgi-bin/bts-usertags.cgi?user=%s" % user
sender = user
receiver = user

# connect to UDD and get all bugs for a certain user
def uddConnect():
	global user
	import psycopg2
	conn = psycopg2.connect("service=udd")
	cursor = conn.cursor()
	return cursor

# select all usertagged bugs for our user
def bugList():
	global user
	cursor = uddConnect()
	cursor.execute("SELECT id,tag from bugs_usertags WHERE email='%s' ORDER BY id" % user)
	buglist = []
	for bug in cursor.fetchall():
		buglist.append(bug)
	return buglist

# get bug title
def bugInfo(bugid) :
	cursor = uddConnect()
	cursor.execute("SELECT title from bugs WHERE id='%s'" % bugid)
	for bug in cursor.fetchall():
		return bug[0]

# take a list of bugnumbers and usertags and save them to a file
def saveState(data):
	global filename
	filename = "./%s" % filename
	try:
		with open(filename, 'w') as f:
			f.write(str(data))
		f.closed
	except IOError as e:
		errorHandler("Could not save state")
        	return False

	return True

# compare two datasets
def compareState(new):
	import ast
	global bdourl, usertagurl, filename, sender, receiver
	filename = "./%s" % filename
	old = ""
	data = {}

	# load old data string and convert it to a dictionary
	try:
		with open(filename, 'r') as f:
			old = f.read()
		f.closed
	except IOError as e:
		errorHandler("Could not read state")
		# attempt to create an empty file
		saveState("")

	if len(old) > 0:
		# if no error, convert old state string to dictionary
		data = set(ast.literal_eval(old))

	# convert new data to dictionary, so we can compare old and new
	if len(new) > 0:
		newdata = set(new)
	else:
		newdata = {}

	if len(newdata) < 1:
		errorHandler("Could not retrieve new data")
	else:
		# compare the dictionaries
		for bug in newdata:
			if not bug in data:
				title = bugInfo(bug[0])
				#print "New usertag '%s' on bug #%s: %s" % (bug[1], bug[0], title)
				subject = "New usertag '%s' on bug #%s: %s" % (bug[1], bug[0], title)
				body = "%s%s\n\nSee all usertags: %s" % (bdourl, bug[0], usertagurl)
				sendMail(sender, receiver, subject, body)
	# in any case, we need to resave the current state
	saveState(new)

# send an email.
def sendMail(sender, receiver, subject, text):
	# Import smtplib for the actual sending function and mail modules
	import smtplib
	from email.mime.text import MIMEText

	# create message
	msg = MIMEText(text)
	msg['Subject'] = subject
	msg['From'] = sender
	msg['To'] = receiver

	# Send the message via our local SMTP server
	s = smtplib.SMTP('localhost')
	s.sendmail(receiver, [sender], msg.as_string())
	s.quit()

def errorHandler(msg):
	global sender, receiver
	subject = "Error"
	body = "Could not process UDD query: %s" % msg
	sendMail(sender, receiver, subject, body)

# __init__
buglist = bugList()
# construct current buglist for user and compare this to the current state
compareState(buglist)
