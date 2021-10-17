"""
Simple function for texting from an unsecure gmail account...
I made this to send myself updates on the progress of programs
with long runtimes (simulations in my audit research).

Oliver Broadrick 2021
"""

from smtplib import SMTP

VERIZON = '@vtext.com'
ATT = '@mms.att.net'
TMOBL = '@tmomail.net'
OLIVER_BROADRICK = '2073515208'

def txtme(msg_contents, phone_number=OLIVER_BROADRICK, carrier=VERIZON):
    """
    msg_contents is the body of the message
    phone_number is the number to which the message will be sent 
        (defaults to Oliver Broadrick's number)
    carrier is the carrier for the number
        (defaults to verizon which is Oliver Broadrick's carrier)

    Sends an SMS message with msg_contents to phone_number with 
    carrier as the carrier from my sendmessages27@gmail.com account.
    """

    # Log into gmail account
    server = SMTP("smtp.gmail.com")
    server.starttls()
    username = 'sendmessages27@gmail.com'
    password = 'E*80GD*fJGw!RI'
    server.login(username, password)

    # Construct message
    subject = ' ' # Subject doesn't show up in text (just in emails)
    fr = username
    to = phone_number + carrier
    msg = 'From: '+fr+'\r\n % from'\
          + 'Too: '+to+'\r\n % to'\
          + 'Subject: '+subject+'\r\n % subject'\
          + '\r\n'\
          + msg_contents

    # Send message
    server.sendmail(fr, to, msg)
