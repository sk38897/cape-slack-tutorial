#!/usr/bin/env python3
# Copyright (c) 2017 Blemundsbury AI Limited
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys, time
from slackclient import SlackClient
from cape.client import CapeClient


CAPE_TOKEN = 'myusertoken' # Your Cape user token
CAPE_ADMIN_TOKEN = 'myadmintoken' # Your Cape admin token
SLACK_KEY = 'myslackkey' # Your bot's Slack key
BOT_ID = 'mybotid' # Your bot's Slack ID
READ_WEBSOCKET_DELAY = 1 # Delay in seconds between reading from firehose



def handle_question(question, channel, slack_client, cape_client):
    # Retrieve a list of answers to the user's question
    answers = cape_client.answer(question, CAPE_TOKEN)
    if len(answers) > 0:
        # Respond with the highest confidence answer
        slack_client.api_call("chat.postMessage", channel=channel,
                              text=answers[0]['answerText'],
                              as_user=True)
    else:
        # No answer was found above the current confidence threshold
        slack_client.api_call("chat.postMessage", channel=channel,
                              text="Sorry! I don't know the answer to that.",
                              as_user=True)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            at_bot = "<@%s>" % BOT_ID
            if output and 'text' in output and at_bot in output['text'] and 'channel' in output:
                # return text after the @ mention, whitespace removed
                return output['text'].split(at_bot)[1].strip(), \
                       output['channel']
    return None, None


def add_saved_reply(message, channel, slack_client, cape_client):
    try:
	# Split the message up into its component parts
        message = message.split(".add-saved-reply")[1]
        question, answer = message.split('|', 1)
    except Exception as e:
	# Let the user know the correct formatting if we couldn't parse what they sent
        slack_client.api_call("chat.postMessage", channel=channel,
                              text="Sorry, I didn't understand that. The usage for " \
				   ".add-saved-reply is: .add-saved-reply " \
				   "question | answer",
			      as_user=True)
        return

    try:
	# Create a new saved reply
        cape_client.add_saved_reply(question, answer)
        slack_client.api_call("chat.postMessage", channel=channel,
                              text="Thanks, I'll remember that!", as_user=True)
    except CapeException as e:
	# Inform the user of any errors encountered when adding their saved reply
        slack_client.api_call("chat.postMessage", channel=channel,
                              text=e.message, as_user=True)


if __name__ == "__main__":
    slack_client = SlackClient(SLACK_KEY)
    cape_client = CapeClient(admin_token=CAPE_ADMIN_TOKEN)

    if slack_client.rtm_connect():
        print("Connected")
    else:
        print("Failed to connect")
        sys.exit()

    while True:
        message, channel = parse_slack_output(slack_client.rtm_read())
        if message and channel:
            if message.lower().startswith(".add-saved-reply"):
                add_saved_reply(message, channel, slack_client, cape_client)
            else:
                handle_question(message, channel, slack_client, cape_client)
        time.sleep(READ_WEBSOCKET_DELAY)
