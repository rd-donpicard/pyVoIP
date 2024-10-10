# test_sip_message.py

import email
import sys
from pyVoIP.SIP.message.message import SIPMessage, SIPResponse, SIPRequest, SIPMethod
from email import policy
from email.parser import BytesParser

def test_sip_message_from_bytes(invite_data):
    # Use the SIPMessage.from_bytes() static method
    try:
        sip_message = SIPMessage.from_bytes(invite_data)
        print(sip_message.summary())

    except Exception as e:
        logger.exception("Error parsing SIP message")

if __name__ == "__main__":

    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    try:
        # Read the file in binary mode to handle raw byte content
        filepath = '../tmp/invite.txt'
        with open(filepath, 'rb') as file:
            data = file.read()
            test_sip_message_from_bytes(data)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Error parsing SIP message")

