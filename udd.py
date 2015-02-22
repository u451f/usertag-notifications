#!/usr/bin/env python
####################################################
# Query the Debian Ultimate Database (UDD) for
# new usertags on bugs and send email notifications
# to the user.
# To install a cronjob on alioth run `crontab -e`
# Also see https://wiki.debian.org/AppArmor/Reportbug
# and https://wiki.debian.org/UltimateDebianDatabase
#####################################################
# Copyright 2015 u <u@451f.org>
# Released under the GPLv3
# Made during rd9 of the GNOME Outreach program
#####################################################

# configuration
state_filename = "usertags.state"
team_email_address = "pkg-apparmor-team@lists.alioth.debian.org"
bdo_url = "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug="
usertag_url = "https://udd.debian.org/cgi-bin/bts-usertags.cgi?user=%s" % team_email_address
sender = team_email_address
receiver = team_email_address
smtp_server = "localhost"

# connect to UDD
def udd_connect():
    import psycopg2
    conn = psycopg2.connect("service=udd")
    cursor = conn.cursor()
    return cursor

# select all usertagged bugs for our user
def get_bug_list(team_email_address):
    cursor = udd_connect()
    cursor.execute("SELECT bugs_usertags.id, bugs_usertags.tag, title FROM bugs_usertags JOIN bugs ON bugs_usertags.id = bugs.id WHERE email='%s' ORDER BY id" % team_email_address)
    items = cursor.fetchall()

    # construct the list using a dictionary so we can retrieve the keys later
    buglist = []
    for item in items:
        bug = {'id': item[0], 'tag': item[1], 'title': item[2]}
        buglist.append(bug)

    return buglist

# take a list of bugnumbers and usertags and save them to a file
def save_statefile(state_filename, data):
    import pickle
    try:
        f = open(state_filename, 'wb')
        # Pickle data dictionary using protocol 0.
        pickle.dump(data, f)
        f.close()
    except IOError as e:
        # send_error_mail("Could not save state file.")
        return False

    return True

# load old data string and convert it to a dictionary
# @returns dictionary with old state
def read_statefile(state_filename):
    import pprint, pickle
    try:
        f = open(state_filename, 'rb')
        old = pickle.load(f)
        f.close()
    except IOError as e:
        # send_error_mail("Could not read state file.")
        return False

    # pprint.pprint(old)
    return old

# compare two lists of dictionaries
def compare_state(old_state_data, new_state_data):
    deleted_usertags = []
    added_usertags = []

    # if there is no new data, exit
    if len(new_state_data) < 1:
    	return False

    # compare old state data and new state data for added usertags
    for item in new_state_data:
        if item in old_state_data:
            added_usertags.append(item)

    # compare old state data and new state data for deleted usertags
    for item in old_state_data:
        if item in new_state_data:
            deleted_usertags.append(item)

    return added_usertags, deleted_usertags

# send one email per bug to the team
# @diff = added | deleted
def send_team_notification(sender, receiver, bug_list, diff, bdo_url, usertag_url):
    notifications = []
    # construct notification text for each bug
    for bug in bug_list:
    	# print "usertag '%s' %s on bug #%s: %s" % (bug['tag'], diff, bug['id'], bug['title'])
    	notification_subject = "usertag '%s' %s on bug #%s: %s" % (bug['tag'], diff, bug['id'], bug['title'])
    	notification_msg = "%s%s\n\nSee all usertags: %s" % (bdo_url, bug['id'], usertag_url)
    	notifications.append([notification_subject, notification_msg])
    # send team notification
    if notifications:
    	for notification in notifications:
    		send_mail(sender, receiver, notification[0], notification[1])

# send an email.
def send_mail(sender, receiver, subject, text):
    # Import smtplib for the actual sending function and mail modules
    import smtplib
    from email.mime.text import MIMEText

    # configure smtp_server
    global smtp_server
    if not smtp_server:
    	smtp_server = "localhost"

    # create message
    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    # Send the message
    s = smtplib.SMTP(smtp_server)
    s.sendmail(receiver, [sender], msg.as_string())
    s.quit()

def send_error_mail(msg):
    global sender, receiver
    subject = "udd.py caused an error"
    send_mail(sender, receiver, subject, msg)

# __init__
# construct current buglist for team_email_address and compare it to the old saved state
current_buglist = get_bug_list(team_email_address)
old_buglist = read_statefile(state_filename)

# attempt to save the file if there is not yet an old_buglist
if current_buglist and not old_buglist:
    save_statefile(state_filename, current_buglist)

if current_buglist and old_buglist:
    # retrieve usertag diff
    added_usertags, deleted_usertags = compare_state(old_buglist, current_buglist)
    # send notification to the team
    send_team_notification(sender, receiver, added_usertags, "added", bdo_url, usertag_url)
    send_team_notification(sender, receiver, deleted_usertags, "deleted", bdo_url, usertag_url)
    # save the current state
    save_statefile(state_filename, current_buglist)
