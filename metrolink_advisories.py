from requests_html import HTMLSession
from email.mime.text import MIMEText
import datetime, smtplib, ssl, hashlib, os, tempfile, time

"""
First, install these requirements.
  - pyhton3-pip3
  - python3-lxml
  - requests       (via pip3 install requests)
  - requests-html  (via pip3 install requests_html)

Then, modify the below variables.
  - SENDER_EMAIL   - email address that will send the email.
  - GOOGLE_APP_KEY - google app key for the above google account.
      - https://support.google.com/accounts/answer/185833
      - Should be 16 characters, don't enter spaces.
  - TO_EMAIL       - email address that will recieve the email.
      - It is reccomended to use a different email address to ensure you get the notification.
  - FILENAME       - name of the temporary file to generate. Don't need to change this normally.
  - WINDOWS        - set to "False" if on a linux machine or docker container.
  - WEEKEND_NOTIFY - set to "True" if you want to be notified of train delays on weekends.

Next, put your train numbers in retrieve_advisories() method where it says "//Modify array with your train numbers".

Finally, go to the very bottom.
  - Uncomment "main("","")" if you want this script to run once.
  - or uncomment "runon_schedule(300.00)" to keep this script running, and check every 300 seconds.
    - You can also change the number of seconds (e.g. 500.0)
    - Do not do this if you are using GCP cloud functions or AWS Lambda functions to run this.
    - Add this python script to your startup.

Remember to add execution permissions to this script on linux.
"""

SENDER_EMAIL   = ""
GOOGLE_APP_KEY = ""
TO_EMAIL       = ""
FILENAME       = "sent_advisories.txt"
WINDOWS        = True
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

    advisory_file = open(tempfile.gettempdir() + "/" + filename, "a+")
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

    if not os.path.exists(tempfile.gettempdir() + "/" + filename):
        open(tempfile.gettempdir() + "/" + filename,"a+").close()

    advisory_response = advisory.response
    advisory_file = open(tempfile.gettempdir()+ "/" + filename, "r")

    for line in advisory_file:
        if line.strip() == advisory_response.strip():
            print("User has already been notified of this advisory.")
            advisory_file.close()
            return True

    advisory_file.close()
    return False

def handle_advisories(response_list, reciever_email, sender_email, filename, password, weekend_notify, windows):
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
    # Adding linux compatability for the datetime string.
    if(windows):
        today = time.strftime("%#m/%#d/%Y")
    else:
        today = time.strftime("%-m/%-d/%Y")

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
    print("Finished.")

# Arguments and method included if you want to attempt to get this working with AWS Lambda.
def main(context, response):
    print("Starting execution.")
    response_list = retrieve_advisories()
    handle_advisories(response_list, TO_EMAIL, SENDER_EMAIL, FILENAME, GOOGLE_APP_KEY, WEEKEND_NOTIFY, WINDOWS)

# Running continuously to avoid cron (for docker and linux).
def runon_schedule(delay_seconds):
    starttime = time.time()
    while True:
        main("","")
        print("Waiting " +str(delay_seconds)+ " seconds.")
        time.sleep(delay_seconds - ((time.time() - starttime) % delay_seconds))
        print("Running again.\n")

# To just run once:
# main("", "")

# To run on schedule:
# runon_schedule(300.00)
