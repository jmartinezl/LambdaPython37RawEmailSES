import re
import logging
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import os.path
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('ses')


def get_mime_content_type(filename):
    """Get mime type.

    :param filename: str
    :type filename: str
    :rtype: str.
    """
    mime_types = dict(
        txt='text/plain',
        htm='text/html',
        html='text/html',
        php='text/html',
        css='text/css',
        js='application/javascript',
        json='application/json',
        xml='application/xml',
        swf='application/x-shockwave-flash',
        flv='video/x-flv',

        # images
        png='image/png',
        jpe='image/jpeg',
        jpeg='image/jpeg',
        jpg='image/jpeg',
        gif='image/gif',
        bmp='image/bmp',
        ico='image/vnd.microsoft.icon',
        tiff='image/tiff',
        tif='image/tiff',
        svg='image/svg+xml',
        svgz='image/svg+xml',

        # archives
        zip='application/zip',
        rar='application/x-rar-compressed',
        exe='application/x-msdownload',
        msi='application/x-msdownload',
        cab='application/vnd.ms-cab-compressed',

        # audio/video
        mp3='audio/mpeg',
        ogg='audio/ogg',
        qt='video/quicktime',
        mov='video/quicktime',

        # adobe
        pdf='application/pdf',
        psd='image/vnd.adobe.photoshop',
        ai='application/postscript',
        eps='application/postscript',
        ps='application/postscript',

        # ms office
        doc='application/msword',
        rtf='application/rtf',
        xls='application/vnd.ms-excel',
        ppt='application/vnd.ms-powerpoint',

        # open office
        odt='application/vnd.oasis.opendocument.text',
        ods='application/vnd.oasis.opendocument.spreadsheet',
    )

    ext = os.path.splitext(filename)[1][1:].lower()
    if ext in mime_types:
        return mime_types[ext]
    else:
        return 'application/octet-stream'


def lambda_handler(event, context):
    """Validar body y conseguir el objeto data."""
    if 'body' in event and event['body']:
        body = event['body']
    else:
        return json_response("ERROR")

    if 'data' in body and body['data'] and isinstance(body['data'], (list, dict)):

        data = body['data']
        """validar los emails"""
        if 'ToAddresses' in data and data['ToAddresses'] and isinstance(data['ToAddresses'], (list, dict)):
            to_addresses = data['ToAddresses']
            for item in to_addresses:
                if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", item):
                    return json_response("ERROR")
        else:
            return json_response("ERROR")
        if 'CcAddresses' in data and data['CcAddresses'] and isinstance(data['CcAddresses'], (list, dict)):
            cc_addresses = data['CcAddresses']
            for item in cc_addresses:
                if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", item):
                    return json_response("ERROR")
        else:
            cc_addresses = []
        if 'BccAddresses' in data and data['BccAddresses'] and isinstance(data['BccAddresses'], (list, dict)):
            bcc_addresses = data['BccAddresses']
            for item in bcc_addresses:
                if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", item):
                    return json_response("ERROR")
        else:
            bcc_addresses = []
        if 'ReplyToAddresses' in data and data['ReplyToAddresses']:
            reply_to_addresses = data['ReplyToAddresses']
            if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", reply_to_addresses):
                return json_response("ERROR")
        else:
            reply_to_addresses = 'no-reply@ses-verified-domain-com'
        if 'sender_email' in data and data['sender_email']:
            sender_email = data['sender_email']
            if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", sender_email):
                return json_response("ERROR")
        else:
            sender_email = 'no-reply@ses-verified-domain-com'
        """validar que los parametros no estan vacios"""
        for item in ("Subject", "Body"):
            if not data[item]:
                return json_response("ERROR")
        if "@ses-verified-domain-com" not in sender_email:
            sender_email = 'no-reply@ses-verified-domain-com'
        if 'sender' in data and data['sender']:
            sender_email = data['sender']+'<'+sender_email+'>'
        try:

            # Build an email
            msg = MIMEMultipart()
            msg['Subject'] = data['Subject']
            msg['From'] = sender_email
            msg['To'] = ', '.join(to_addresses)
            msg['Cc'] = ', '.join(cc_addresses)
            msg['Bcc'] = ', '.join(bcc_addresses)
            # What a recipient sees if they don't use an email reader
            msg.preamble = 'Multipart message.\n'

            part = MIMEText(data['Body'], 'html')
            msg.attach(part)

            if 'attachments' in data and data['attachments'] and isinstance(data['attachments'], (list, dict)):

                attachments = data['attachments']

                print(attachments)

                for attachment in attachments:
                    if 'Filename' in attachment and attachment['Filename'] and 'FileData' in attachment and attachment['FileData']:
                        # The attachment
                        mime_content_type = get_mime_content_type(attachment['Filename'])
                        part = MIMEApplication(base64.b64decode(attachment['FileData']))
                        part.add_header('Content-Disposition', 'attachment', filename=attachment['Filename'])
                        part.add_header('Content-Type', mime_content_type+'; Content-Transfer-Encoding: base64')
                        msg.attach(part)

            response = client.send_raw_email(
                Destinations=to_addresses,
                FromArn='',
                RawMessage={
                    'Data': msg.as_string(),
                },
            )

            if(response['ResponseMetadata']['HTTPStatusCode'] == 200):
                return json_response("OK")
            else:
                logger.error(response)
                return json_response("ERROR")
        except Exception as e:
            logger.error(e)
            return 0
    else:
        return json_response("ERROR")


def json_response(message):
    return {
        "message": message
    }
