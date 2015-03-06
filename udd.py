#!/usr/bin/env python
""" Query the Debian Ultimate Database (UDD) for
new usertags on bugs and send email notifications
to the user.
To install a cronjob on alioth run `crontab -e`
Also see https://wiki.debian.org/AppArmor/Reportbug
and https://wiki.debian.org/UltimateDebianDatabase
....................................................
Copyright 2015 u <u@451f.org>
Released under GPLv3
Made during rd9 of the GNOME Outreach program
....................................................
"""
smtp_server = "localhost"

def udd_connect():
    """
    Connect to UDD.
    @params: none
    @returns: db cursor
    """
    import psycopg2
    conn = psycopg2.connect("service=udd")
    cursor = conn.cursor()
    return cursor

def get_current_buglist(team_email_address):
    """
    Select all usertagged bugs for our user. query the bug title at the
    same time. construct a bug list of one dictionary per bug.
    @params: str(Debian BTS maintainer / team email address)
    @returns: list of dictionaries
    """
    cursor = udd_connect()
    cursor.execute("SELECT bugs_usertags.id, bugs_usertags.tag, title \
                    FROM bugs_usertags JOIN bugs ON bugs_usertags.id = bugs.id \
                    WHERE email='%s' ORDER BY id" % team_email_address)

    return [{'id': item[0], 'tag': item[1], 'title': item[2]} \
	       for item in cursor.fetchall()]

def compare_state(old_state_data, new_state_data):
    """
    Compare two lists of dictionaries.
    @params: two lists of dictionaries
             ({'id': '123', 'tag': 'the_tag', 'title': 'The Title'})
    @returns: two lists of dictionaries
    """
    deleted_usertags = []
    added_usertags = []

    # If there is no new data, exit.
    if len(new_state_data) > 0:
        # Compare old state data and new state data for added usertags
        for item in new_state_data:
            if item not in old_state_data:
                added_usertags.append(item)
        # Compare old state data and new state data for deleted usertags
        for item in old_state_data:
            if item not in new_state_data:
                deleted_usertags.append(item)

    return added_usertags, deleted_usertags

def read_statefile(state_filename):
    """
    Use pickle to read the list of bugs from a file.
    For debugging the data, use pprint.
    @params: str(state_filename)
    @returns: list of dictionaries, False on read failure
    """
    #import pprint
    import pickle
    try:
        state_file = open(state_filename, 'rb')
        data = pickle.load(state_file)
        state_file.close()
    except IOError:
        return False

    #pprint.pprint(data)
    return data

def save_statefile(state_filename, data):
    """
    Use pickle to save the list of bugs to a file.
    @params: str(state_filename), data = list of dictionaries
    @returns: True on success, False on failure
    """
    import pickle
    try:
        state_file = open(state_filename, 'wb')
        pickle.dump(data, state_file)
        state_file.close()
    except IOError:
        return False

    return True

def send_notification(sender, receiver, bug_list, operation, bdo_url, usertag_url):
    """
    Send one email per bug to the team.
    @params:
            sender = str(email address)
            receiver = str(email address)
            bug_list = ({'id': '123', 'tag': 'the_tag', 'title': 'The Title'})
	        operation = str ("added" or "deleted")
            bdo_url = str(url)
            usertag_url = str(url)
    @returns: void
    """
    for bug in bug_list:
        notification_subject = "usertag '%s' %s on bug #%s: %s" \
                               % (bug['tag'], operation, bug['id'], bug['title'])
        notification_msg = "%s%s\n\nSee all usertags: %s" \
                           % (bdo_url, bug['id'], usertag_url)
        send_mail(sender, receiver, notification_subject, notification_msg)

def send_mail(sender, receiver, subject, text):
    """
    Send an email.
    @params: str(sender) = email address
            str(receiver) = email address
            str(subject) = email body
            str(text) = email test
    @returns: void
    """
    # Import smtplib for the actual sending function and mail modules
    import smtplib
    from email.mime.text import MIMEText
    global smtp_server
    if not smtp_server:
        smtp_server = "localhost"

    # Create message
    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    # Send the message
    smtp_mail = smtplib.SMTP(smtp_server)
    smtp_mail.sendmail(receiver, [sender], msg.as_string())
    smtp_mail.quit()

def main():
    """
    Construct current buglist for team_email_address and compare it to
    the old saved state. Attempt to save the file if there is not yet
    an old_buglist. Retrieve usertag diff, then send notifications to
    the team and re-save the current state.
    @params: none
    @returns: False on failure
    """
    # Configuration
    state_filename = "usertags.state"
    team_email_address = "pkg-apparmor-team@lists.alioth.debian.org"
    bdo_url = "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug="
    usertag_url = "https://udd.debian.org/cgi-bin/bts-usertags.cgi?user=%s" % team_email_address
    sender = team_email_address
    receiver = team_email_address

    current_buglist = get_current_buglist(team_email_address)
    old_buglist = read_statefile(state_filename)

    if current_buglist:
        if old_buglist:
            added_usertags, deleted_usertags = compare_state(old_buglist, current_buglist)
            send_notification(sender, receiver, added_usertags, "added", bdo_url, usertag_url)
            send_notification(sender, receiver, deleted_usertags, "deleted", bdo_url, usertag_url)
        else:
            send_notification(sender, receiver, current_buglist, "added", bdo_url, usertag_url)
        save_statefile(state_filename, current_buglist)
    else:
        return False

main()
