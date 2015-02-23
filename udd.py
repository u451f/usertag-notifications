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
# Released under GPLv3
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
# @params: none
# @returns: db cursor
def udd_connect():
    import psycopg2
    conn = psycopg2.connect("service=udd")
    cursor = conn.cursor()
    return cursor

# select all usertagged bugs for our user. query the bug title at the same time. construct a bug list
# @params: str(Debian BTS maintainer / team email address)
# @returns: list of dictionaries
def get_bug_list(team_email_address):
    cursor = udd_connect()
    cursor.execute("SELECT bugs_usertags.id, bugs_usertags.tag, title FROM bugs_usertags JOIN bugs ON bugs_usertags.id = bugs.id WHERE email='%s' ORDER BY id" % team_email_address)
    items = cursor.fetchall()

    # construct the bug list: a list of dictionaries for each bug.
    buglist = []
    for item in items:
        bug = {'id': item[0], 'tag': item[1], 'title': item[2]}
        buglist.append(bug)

    return buglist

# use pickle to save the list of bugs to a file
# @params: str(state_filename), data = list of dictionaries
# @returns: True on success, False on failure
def save_statefile(state_filename, data):
    import pickle
    try:
        f = open(state_filename, 'wb')
        pickle.dump(data, f)
        f.close()
    except IOError as e:
        # send_error_mail("Could not save state file.")
        return False

    return True

# use pickle to read the list of bugs from a file
# for debugging the data, use pprint
# @params: str(state_filename)
# @returns: list of dictionaries, False on read failure
def read_statefile(state_filename):
    # import pprint
    import pickle
    try:
        f = open(state_filename, 'rb')
        data = pickle.load(f)
        f.close()
    except IOError as e:
        # send_error_mail("Could not read state file.")
        return False

    # pprint.pprint(old)
    return data

# compare two lists of dictionaries
# @params: two lists of dictionaries ({'id': '123', 'tag': 'the_tag', 'title': 'The Title'})
# @returns: two lists of dictionaries
def compare_state(old_state_data, new_state_data):
    deleted_usertags = []
    added_usertags = []

    # if there is no new data, exit
    if len(new_state_data) < 1:
    	return False

    # compare old state data and new state data for added usertags
    for item in new_state_data:
        if item not in old_state_data:
            added_usertags.append(item)

    # compare old state data and new state data for deleted usertags
    for item in old_state_data:
        if item not in new_state_data:
            deleted_usertags.append(item)

    return added_usertags, deleted_usertags

# send one email per bug to the team
# @params: operation = str "added" | "deleted"
#          sender = email address
#          receiver = email address
#          bug_list = list of dictionaries ({'id': '123', 'tag': 'the_tag', 'title': 'The Title'})
#          bdo_url = str
#          usertag_url = str
def send_team_notification(sender, receiver, bug_list, operation, bdo_url, usertag_url):
    # construct notification text for each bug and send email
    for bug in bug_list:
    	# print "usertag '%s' %s on bug #%s: %s" % (bug['tag'], operation, bug['id'], bug['title'])
        notification_subject = "usertag '%s' %s on bug #%s: %s" % (bug['tag'], operation, bug['id'], bug['title'])
        notification_msg = "%s%s\n\nSee all usertags: %s" % (bdo_url, bug['id'], usertag_url)
        send_mail(sender, receiver, notification_subject, notification_msg)

# send an email.
# @params: str(sender) = email address
#          str(receiver) = email address
#          str(subject) = email body
#          str(text) = email test
# @returns: void
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

# send error email
# @params: str(msg) = message text
# @global: str(sender), str(receiver)
# @returns: void
def send_error_mail(msg):
    global sender, receiver
    subject = "udd.py caused an error"
    send_mail(sender, receiver, subject, msg)

# __init__
# construct current buglist for team_email_address and compare it to the old saved state
current_buglist = get_bug_list(team_email_address)
old_buglist = read_statefile(state_filename)

# attempt to save the file if there is not yet an old_buglist
if not old_buglist:
    save_statefile(state_filename, current_buglist)

# retrieve usertag diff, then send notifications to the team and re-save the current state
if current_buglist and old_buglist:
    added_usertags, deleted_usertags = compare_state(old_buglist, current_buglist)
    send_team_notification(sender, receiver, added_usertags, "added", bdo_url, usertag_url)
    send_team_notification(sender, receiver, deleted_usertags, "deleted", bdo_url, usertag_url)
    save_statefile(state_filename, current_buglist)
