from requests_html import HTMLSession
from time import strftime
from email.mime.text import MIMEText
import datetime, smtplib, ssl, hashlib, os

"""
Requires - requests_html (pip install requests_html).

SENDER_EMAIL - email address that will send the email. Requres a Google App Key.

GOOGLE_APP_KEY -
Go to your Google Account, click "Security",
then click "App passwords" in the "Signing in to Google" section, then generate
an app password for the Mail app.
https://support.google.com/accounts/answer/185833

Use this 16 character password as the "GOOGLE_APP_KEY" variable below.

TO_EMAIL - email address to send the email to. It is recommended to use a different
email address, as it will guarantee you will be notified whenever you recieve an email alert.
(On some Android versions of Gmail, you won't be notified about an email you send to yourself).

FILENAME - name of the file to store past advisories in.
This file should be cleaned out semi-regularly, but this is not required.

WEEKEND_NOTIFY - set to True if you want to be emailed about advisories on weekends.

Also note that if you are on a linux OS, change:
    today = strftime("%#m/%#d/%Y") to
    today = strftime("%-m/%-d/%Y")
in the handle_advisories() method.

Set your train numbers in the retrieve_advisories method where it says //Modify array with your train numbers
"""

SENDER_EMAIL = ""
GOOGLE_APP_KEY = ""
TO_EMAIL = ""
FILENAME = "sent_advisories.txt"
WEEKEND_NOTIFY = False

class ServiceAdvisory:
    """Class used for any service advisories.

    Attibutes:
    metro_response / response   - string, this is the raw response, passed when creating the class.
    advisory_time               - string, time the advisory was put onto the website.
    advisory_message            - string, the actual advisory message i.e. "AV Line 225 to Lancaster will use track 4B at LA Union Station".
    line                        - string, line and train number the advisory is occuring for. i.e. "AV Line 225"
    """
    def __init__(self, metro_response):
        self.response = metro_response
        self.advisory_time = self.response.split("<p>")[1].replace("</p>", "").replace("&nbsp", " ").replace(";", "")
        self.advisory_message = self.response.split("<p>")[2].replace("</p>", "").strip()
        self.line = self.advisory_message.split("to")[0]

def retrieve_advisories():
    """Retrieves advisories from the metrolinktrains.com website.

    Using requests_html library to get a session from the website.
    We can render the page and run a Javascript script after the website is rendered.
    This script retrieves all of the service advisories, then checks which ones are on the specified trains.

    Note - this Javascript will need to be updated if the website changes, but as long as the
    service advisories use the same class name and structure, and aren't moved to another domain, this should work.

    Returns - List of all advisories for your specified train numbers.
    """
    session = HTMLSession()
    response = session.get('https://www.metrolinktrains.com')
    script = """
        () => {
            var array = Array.from(document.getElementsByClassName("accordionAdvisories__service-advisory"))
            var array2 = []
            var rtn_array = []

            // Modify array with your train numbers:
            var train_array = ["123", "456", "789"]

            Array.prototype.forEach.call(array, function(el) {
                array2.push(el.children.item(1).innerHTML);
            });

	        Array.prototype.forEach.call(array2, function(el) {
		          if(train_array.some(item => el.includes(item))){
			               rtn_array.push(el)
        	       }
            });
            return rtn_array
        }
    """

    print("Rendering Metro advisory website. This may take a few seconds.")
    return response.html.render(script=script)

def send_mail(service_advisory, to_email, sender_email, password):
    """Sending an email when an advisory occurs.

    Arguments:
    service_advisory    - ServiceAdvisory object.
    to_email            - string, email address to send the mail to.
    sender_email        - string, email address the mail will come from.
    password            - string, Google App Key for the sender_email account.

    This script is currently only set up to work with gmail, but you can modify it
    to use a different provider.
    """
    print("ADVISORY - Sending Email.")

    port = 465
    smtp_server = "smtp.gmail.com"

    subject = "Metro Advisory - " + service_advisory.line
    body = service_advisory.advisory_message

    # MIME is required to get the "Subject" to appear correctly.
    message = MIMEText(body, "plain")
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to_email

    # Using SSL to sign in.
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(message['From'], message['To'], message.as_string())
        server.quit()

def update_advisory_file(filename, advisory):
    """ Updates the advisories file so you aren't notified of the same advisory multiple times.

    The raw response is stored on file as it's not possible to be a duplicate of a previous advisory.

    Arguments:
    filename - string, name of the sent advisories file.
    advisory - ServiceAdvisory object.
    """

    advisory_file = open(filename, "a+")
    advisory_file.write(advisory.response + "\n")
    advisory_file.close()

def been_notified(filename, advisory):
    """Uses the advisory file to determine if a user has already been notified about an advisory.

    Arguments:
    filename - string, name of the advisory file.
    advisory - ServiceAdvisory object.

    Returns:
    Boolean, True if the user has already been notified (if advisory's date and time appears in the file).
    """

    if not os.path.exists(filename):
        open(filename,"a+").close()

    advisory_response = advisory.response
    advisory_file = open(filename, "r")

    for line in advisory_file:
        if line.strip() == advisory_response.strip():
            print("User has already been notified of this advisory.")
            return True

    return False

def handle_advisories(response_list, reciever_email, sender_email, filename, password, weekend_notify):
    """ Handles advisories, acts as a main method.
    Will not notify a user about advisories on weekends by default.

    Arguments:
    response_list   - list, list of responses (advisories) from the metro website
    reciever_email  - string, email address to send the email to if there is a new advisory
    sender_email    - string, email address that sends the email
    filename        - string, name of the previous advisories file
    password        - string, Google App Key with Mail permissions.
    weekend_notify  - boolean, true to notify on weekends.
    """
    # Change # to - if on linux, in the following variable:
    today = strftime("%#m/%#d/%Y")

    # Looping through each advisory for your trains.
    for metro_response in response_list:
        # If it isn't a weekend, and the advisory occured today:
        if(datetime.datetime.today().weekday() < 5 or weekend_notify):
            if(today in metro_response):
                # If you haven't been notified already, then notify you
                # and add the response to the advisory file.
                if(not been_notified(filename, ServiceAdvisory(metro_response))):
                    send_mail(ServiceAdvisory(metro_response), reciever_email, sender_email, password)
                    update_advisory_file(filename, ServiceAdvisory(metro_response))

# Arguments and method included if you want to attempt to get this working with AWS Lambda.
def main(event,context):
    response_list = retrieve_advisories()
    handle_advisories(response_list, TO_EMAIL, SENDER_EMAIL, FILENAME, GOOGLE_APP_KEY, WEEKEND_NOTIFY)

main("","")
