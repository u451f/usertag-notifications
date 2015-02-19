#!/usr/bin/env python
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
def get_bug_list(team_email_address):
	cursor = udd_connect()
	cursor.execute("SELECT id,tag from bugs_usertags WHERE email='%s' ORDER BY id" % team_email_address)
	buglist = []
	for bug in cursor.fetchall():
		buglist.append(bug)
	return buglist

# get bug title
def get_bug_title(bugid) :
	cursor = udd_connect()
	cursor.execute("SELECT title from bugs WHERE id='%s'" % bugid)
	for bug in cursor.fetchall():
		return bug[0]

# take a list of bugnumbers and usertags and save them to a file
def save_statefile(state_filename, data):
	try:
		with open(state_filename, 'w') as f:
			f.write(str(data))
		f.closed
	except IOError as e:
		send_error_mail("Could not save state file.")
        	return False

	return True

# load old data string and convert it to a dictionary
# @returns dictionary with old state
def read_statefile(state_filename):
	try:
		with open(state_filename, 'r') as f:
			old = f.read()
		f.closed
		return old
	except IOError as e:
		send_error_mail("Could not read state file.")
		# attempt to create an empty file
		save_statefile("")
		return false

# compare two datasets
def compare_state(old_state, new_state):
	import ast
	global bdo_url, usertag_url
	old_state_data = {}
	notifications = []

	# convert old state string to dictionary
	if len(old_state) > 0:
		old_state_data = set(ast.literal_eval(old_state))

	# convert new state string to dictionary, so we can compare old and new
	if len(new_state) > 0:
		new_state_data = set(new_state)
	else:
		new_state_data = {}

	if len(new_state_data) < 1:
		print "Could not retrieve new data."
		return false
	else:
		# compare old state data and new state data 
		for bug in new_state_data:
			if not bug in old_state_data:
				title = get_bug_title(bug[0])
				print "usertag '%s' added on bug #%s: %s" % (bug[1], bug[0], title)
				# construct notification list
				notification_subject = "usertag '%s' added on bug #%s: %s" % (bug[1], bug[0], title)
				notification_msg = "%s%s\n\nSee all usertags: %s" % (bdo_url, bug[0], usertag_url)
				notifications.append([notification_subject, notification_msg])
		return notifications

def send_team_notification(notification_subject, notification_msg):
	global sender, receiver
	for notification in notifications:
		send_mail(sender, receiver, notification_subject, notification_title)

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
	subject = "udd.py caused an error"
	send_mail(sender, receiver, subject, msg)

# __init__
# construct current buglist for team_email_address and compare it to the old saved state
current_buglist = get_bug_list(team_email_address)
old_buglist = read_statefile(state_filename)
if old_buglist and current_buglist:
	notifications = compare_state(old_buglist, current_buglist)
	if notifications:
		for notification in notifications:
			print notification
			#send_team_notification(notification[0], notification[1])
	# save the current state
	save_statefile(state_filename, current_buglist)
