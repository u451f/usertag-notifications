####################################################
# Query the Debian Ultimate Database (UDD) for
# new usertags on bugs and send email notifications
# to the user.
# To install a cronjob on alioth run `crontab -e`
# Also see https://wiki.debian.org/AppArmor/Reportbug
#####################################################
# Copyright 2015 u <u@451f.org>
# Released under the GPLv3
# Made during rd9 of the GNOME Outreach program
#####################################################

# global configuration
state_filename = "usertags.state"
team_email_address = "pkg-apparmor-team@lists.alioth.debian.org"
bdo_url = "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug="
usertag_url = "https://udd.debian.org/cgi-bin/bts-usertags.cgi?user=%s" % team_email_address
sender = team_email_address
receiver = team_email_address

# connect to UDD
def udd_connect():
	import psycopg2
	conn = psycopg2.connect("service=udd")
	cursor = conn.cursor()
	return cursor

# select all usertagged bugs for our user
def bug_list():
	global team_email_address
	cursor = udd_connect()
	cursor.execute("SELECT id,tag from bugs_usertags WHERE email='%s' ORDER BY id" % team_email_address)
	buglist = []
	for bug in cursor.fetchall():
		buglist.append(bug)
	return buglist

# get bug title
def bugInfo(bugid) :
	cursor = udd_connect()
	cursor.execute("SELECT title from bugs WHERE id='%s'" % bugid)
	for bug in cursor.fetchall():
		return bug[0]

# take a list of bugnumbers and usertags and save them to a file
def save_state(data):
	global state_filename
	state_filename = "./%s" % state_filename
	try:
		with open(state_filename, 'w') as f:
			f.write(str(data))
		f.closed
	except IOError as e:
		send_error_mail("Could not save state file.")
        	return False

	return True

# compare two datasets
def compareState(new):
	import ast
	global bdo_url, usertag_url, state_filename, sender, receiver
	state_filename = "./%s" % state_filename
	old = ""
	data = {}

	# load old data string and convert it to a dictionary
	try:
		with open(state_filename, 'r') as f:
			old = f.read()
		f.closed
	except IOError as e:
		send_error_mail("Could not read state file.")
		# attempt to create an empty file
		save_state("")

	if len(old) > 0:
		# if no error, convert old state string to dictionary
		data = set(ast.literal_eval(old))

	# convert new data to dictionary, so we can compare old and new
	if len(new) > 0:
		newdata = set(new)
	else:
		newdata = {}

	if len(newdata) < 1:
		send_error_mail("Could not retrieve new data.")
	else:
		# compare the dictionaries
		for bug in newdata:
			if not bug in data:
				title = bugInfo(bug[0])
				subject = "usertag '%s' added on bug #%s: %s" % (bug[1], bug[0], title)
				body = "%s%s\n\nSee all usertags: %s" % (bdo_url, bug[0], usertag_url)
				send_mail(sender, receiver, subject, body)
	# in any case, we need to resave the current state
	save_state(new)

# send an email.
def send_mail(sender, receiver, subject, text):
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
	s.send_mail(receiver, [sender], msg.as_string())
	s.quit()

def send_error_mail(msg):
	global sender, receiver
	subject = "uddy.py caused an error"
	send_mail(sender, receiver, subject, msg)

# __init__
# construct current buglist for team_email_address and compare this to the current state
buglist = bug_list()
compareState(buglist)
