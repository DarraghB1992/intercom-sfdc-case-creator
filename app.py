from flask import Flask, request, json
from bs4 import BeautifulSoup
import requests
import datetime
import os

app = Flask(__name__)


def auth_salesforce():
    consumer_key = os.environ['SFDC_CONSUMER_KEY']
    consumer_secret = os.environ['SFDC_CONSUMER_SECRET']
    username = os.environ['SFDC_USERNAME']
    password = os.environ['SFDC_PASSWORD']
    security_token = os.environ['SFDC_SECURITY_TOKEN']

    payload = {
        'grant_type': 'password',
        'client_id': consumer_key,
        'client_secret': consumer_secret,
        'username': username,
        'password': password + security_token
    }

    r = requests.post("https://login.salesforce.com/services/oauth2/token",
                      headers={"Content-Type": "application/x-www-form-urlencoded"},
                      data=payload)

    response = json.loads(r.content)
    salesforce_access_token = response['access_token']

    return salesforce_access_token

salesforce_case_url = 'https://eu16.salesforce.com/services/data/v39.0/sobjects/Case'

salesforce_headers = {'Content-Type': 'application/json',
                      'Authorization': 'Bearer ' + str(auth_salesforce())}

intercom_base_url = 'https://api.intercom.io/'
intercom_headers = {'Authorization': 'Bearer ' + os.environ['INTERCOM_ACCESS_TOKEN'],
                    'Accept': 'application/json'}


@app.route('/')
def home():
    return "Hello, World"


@app.route('/listener', methods=['POST'])
def listener():
    conversation_closed_webhook = json.dumps(request.json)
    conversation_json = json.loads(conversation_closed_webhook)

    # Gather user information from webhook
    username = conversation_json['data']['item']['user']['name']
    user_email = conversation_json['data']['item']['user']['email']
    user_id = conversation_json['data']['item']['user']['user_id']

    # Gather Converastion information from webhook
    conversation_id = conversation_json['data']['item']['id']
    conversation_created_timestamp = conversation_json['data']['item']['created_at']
    conversation_closed_timestamp = conversation_json['created_at']

    human_readable_converastion_created_at = datetime.datetime.fromtimestamp(
        int(conversation_created_timestamp)).strftime('%Y-%m-%d %H:%M:%S')

    human_readable_converastion_closed_at = datetime.datetime.fromtimestamp(
        int(conversation_closed_timestamp)).strftime('%Y-%m-%d %H:%M:%S')

    # Make request to Intercom API to gather the entire converastion and format it
    conversation = get_conversation(conversation_id)
    json_convo = json.loads(conversation)
    converastion_parts = json_convo['conversation_parts']['conversation_parts']
    print(converastion_parts)

    current_conversation = []

    # The first message in a conversation is outside the conversation_parts object, format it and add
    # to current conversation array
    first_message_in_conversation = json_convo['conversation_message']['body']
    first_message_cleaned = BeautifulSoup(first_message_in_conversation, 'lxml').text

    current_conversation.append(username + '-' + human_readable_converastion_created_at + ': ' + first_message_cleaned)

    # Goes through the remaining converastion parts and adds them to the current conversation array
    for x in converastion_parts:
        # Remove conversation parts created by bots and removes assignment parts
        if x['author']['type'] != 'bot' and x['body'] != None:

            # Check if admin or user message
            if x['author']['type'] == 'user':
                conversation_part_author = username
            else:
                admin = get_admin(x['author']['id'])
                admin_json = json.loads(admin)
                conversation_part_author = admin_json['name']

            conversation_part = x['body']
            conversation_part_timestamp = datetime.datetime.fromtimestamp(
                int(x['created_at'])).strftime('%Y-%m-%d %H:%M:%S')

            remove_html_from_conversation_part = BeautifulSoup(conversation_part, 'lxml').text
            format_conversation_part = conversation_part_author + "-" + conversation_part_timestamp + ": " + remove_html_from_conversation_part
            current_conversation.append(format_conversation_part)

    # Adding spaces between messages
    formatted_conversation = '\n\n'.join(str(x) for x in current_conversation)

    # Case object for Salesforce
    case_object = {
        "Type": "Testing",
        "Origin": "Intercom",
        "Reason": "Integration testing",
        "Status": "New",
        "OwnerId": "0051t000001rMTY",
        "Subject": username,
        "Priority": "Low",
        "AccountId": "0011t000007dqBoAAI",
        "Conversation_Transcript__c": formatted_conversation,
        "SuppliedName": username,
        "SuppliedEmail": user_email,
        "SuppliedPhone": "0833333333",
        "SuppliedCompany": "Intercom",
        "Intercom_User_Id__c": user_id
    }

    # Create the case in Salesforce
    r = requests.post(salesforce_case_url, headers=salesforce_headers, json=case_object)
    print(r.status_code)
    print(r.raise_for_status())
    return "Ok"


# Gets the conversation from Intercoms REST API
def get_conversation(conversation_id):
    conversation = requests.get(intercom_base_url + 'conversations/' + conversation_id, headers=intercom_headers)
    return conversation.text


# Gets the admin for the converastion part from Intercoms REST API
def get_admin(admin_id):
    admin = requests.get(intercom_base_url + 'admins/' + admin_id, headers=intercom_headers)
    return admin.text


if __name__ == '__main__':
    app.run(debug=True)
