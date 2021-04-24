# Imports
import click
from requests_html import HTMLSession
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import sys
import pathlib
import datetime
import smtplib
import ssl
import pyppeteer
import json


@click.command()
@click.option(
    "--sender_email",
    type=click.STRING,
    help="Email address of the sender. You'll also need the google app password for this email address.",
    default=None
)
@click.option(
    "--app_password",
    type=click.STRING,
    help="Google app password for sender_email account. More information here - https://support.google.com/accounts/answer/185833. This should be 16 characters without spaces.",
    default=None
)
@click.option(
    "--reciever_email",
    type=click.STRING,
    default=None,
    help="Email address to send the email to. Will default to sender_email if left unset."
)
@click.option(
    '-t',
    type=click.STRING,
    help="Train number to get advisories from, multiple of these may be passed, for example, --t 101 --t 201",
    multiple=True,
    default=None
)
@click.option(
    "--config_file",
    type=click.STRING,
    help="Above arguments are all required, or you can instead put the name of a file here to load config from. See config_example.json for an example config file.",
    default=None
)
def cli_runner(sender_email: str, app_password: str, reciever_email: str, t: list[str], config_file: str):
    """Reads from CLI and runs the rest of the script.

    Parameters
    ----------
    sender_email: string
        Email address used to send emails, also requires app_password
    app_password: string
        Google app password used for sending emails via the sender_email account.
    reciever_email: string
        Destinaton email address for the advisories, if left as None, sender_email will be used.
    t: list[string]
       List of trains to get advisories for.
    config_file: string
        Path to the config file, if using one, otherwise leave empty.
    """
    if config_file is None and None in [sender_email, app_password, t]:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()

    if config_file is not None:
        read_config_file(config_file)
        sys.exit(0)
    elif reciever_email is None:
        reciever_email = sender_email

    TrainConfig(sender_email, app_password, reciever_email, t)


def read_config_file(config_filename: str):
    """ Read the local config file and extract variables
    
    Parameters
    ----------
    config_filename: string
        Name of the json file to open to read parameters from.
    """

    file_path = pathlib.Path(__file__).parent.absolute() / config_filename
    f = open(file_path)
    data = json.load(f)

    # Determining if there are any missing values from the config file.
    if set(["sender_email", "app_password", "trains"]).issubset(data.keys()):
        if "reciever_email" in data.keys():
            reciever_email = data["reciever_email"]
        else:
            reciever_email = data["sender_email"]
        sender_email = data["sender_email"]
        app_password = data["app_password"]
        trains = data["trains"]

        TrainConfig(sender_email, app_password, reciever_email, trains)
    else:
        print("Your config file isn't set up correctly, please verify the formatting is the same as the config_file.json")
        sys.exit(1)


class TrainConfig:
    """ Handles nearly everything relating to advisories """

    def __init__(self, sender_email: str, app_password: str, reciever_email: str, trains: list[str]):
        """
        Parameters
        ----------
        sender_email: string
            Email address used to send emails, also requires app_password
        app_password: string
            Google app password used for sending emails via the sender_email account.
        reciever_email: string
            Destinaton email address for the advisories, if left as None, sender_email will be used.
        trains: list[string]
            List of trains to get advisories for.       
        """
        self.sender_email = sender_email
        self.app_password = app_password
        self.reciever_email = reciever_email
        self.trains = trains

        self.retrieve_advisories()
        self.handle_notifications()

    def retrieve_advisories(self):
        """Retrieve all relevant advisories from the Metrolink website.

        This is done primarily via JavaScript. 
        If there are any major redesigns for the metrolinktrains.com website, this code will need to be updated.
        """

        session = HTMLSession()
        response = session.get('https://metrolinktrains.com')
        script = f"""
            () => {{

                // You'll really need to look at the HTML layout for the metrolinktrains.com website if you want to understand this fully.
                // There's multiple div elements on the page with class "accordionAdvisories__service-advisory". This is where all of the service advisories are.
                // The accordian_array is composed of all HTML div elements with that class.
                // This script doesn't handle planned advisories, as I assume you will know about these already if you take the same train regularly.
                // Also note the join(trains) is python which injects the trains as a javascript-compatable array.

                var accordian_array = Array.from(document.getElementsByClassName("accordionAdvisories__service-advisory"))
                var advisory_array = []
                var rtn_array = []
                var train_array = [{', '.join(self.trains)}]

                // This loops through the accordian array and retrieves the actual advisory text.
                Array.prototype.forEach.call(accordian_array, function(el) {{
                    advisory_array.push(el.children.item(1).innerHTML);
                }});

                // Finally, this filters out the advisories for ones that contain your train numbers, then will return those.
                Array.prototype.forEach.call(advisory_array, function(el) {{
                    if(train_array.some(item => el.includes(item))){{
                            rtn_array.push(el)
                    }}
                }});

                return rtn_array
            }}
        """
        print("Rendering Metro advisory website. This will take a while (they're slow and will rate-limit you if you go faster).")
        try:
            # The site is sloooowwwwww.
            self.advisories = response.html.render(
                script=script,
                timeout=60,
                retries=1,
                wait=30.0,
            )
        except (pyppeteer.errors.TimeoutError, ConnectionResetError):
            print("Request timed out, please wait a bit then try again.")
            sys.exit(1)

        self._format_advisories()

    def _format_advisories(self):
        """ Format advisories into more readable strings """

        # strftime doesn't work properly with single digit months and days, so using orignal formatting here.
        unformatted_today = datetime.datetime.now()
        self.today = f"{unformatted_today.month}/{unformatted_today.day}/{unformatted_today.year}"

        updated_advisories = []

       
        for advisory in self.advisories:
            # Ignore old advisories that could be retrieved from the site.
            if self.today in advisory:
                # This is used for formatting the HTML as text. I was previously using regex for this which was less than ideal.
                advisory = BeautifulSoup(
                    advisory, 
                    features="html.parser"
                ).get_text().replace("\xa0", " ").strip()
                updated_advisories.append(advisory)

        self.advisories = updated_advisories

    def handle_notifications(self):
        """Uses the metro_advisories_notified file to determine if a user has already been notified about an advisory, then call the email sender."""

        # Check if file exists.
        filename = ".metro_advisories_notified.txt"
        file_path = pathlib.Path(__file__).parent.absolute() / filename
        temp_advisories = self.advisories

        # Creating the file if it doesn't exist.
        open(file_path, "a+").close()

        # Delete any old entries from the file.
        self._cleanup_temp_file(file_path)

        # Checking for each advisory in the tempfile if the user has been notified.
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line in temp_advisories:
                    temp_advisories.remove(line)

        # If a user hasn't been alerted about an advisory...
        if len(temp_advisories) > 0:
            date_stripped_advisories = []
            for advisory in temp_advisories:
                # Removing the date at the start of the advisory and adding it to the email.
                date_stripped_advisories.append(
                    advisory.split(self.today)[1].strip())
            
            # Finally sending out the email
            self.send_mail(date_stripped_advisories)
        else:
            print("No advisories to report.")

        # Writing new advisories to file. 
        # Note that the date is getting written to this file.
        with open(file_path, "a") as file:
            for remaining_advisory in temp_advisories:
                file.write(remaining_advisory+"\n")

    def _cleanup_temp_file(self, file_path: pathlib.Path):
        """ Clean the metro_advisories_notified file"""

        with open(file_path, "r+") as f:
            # Creating a clone of the original file here, then seeking back to 0 so we can read it again.
            clone_file = f.readlines()
            f.seek(0)
            f.truncate(0)
            
            # Looping through the clone, not the original.
            for line in clone_file:
                if line.startswith(self.today):
                    # Rewriting the original file with only entries from today.
                    f.write(line)

    def send_mail(self, date_stripped_advisories: list):
        """Sending an email when an advisory occurs.

        This script is currently only set up to work with gmail, but you can modify it
        to use a different provider.

        Parameters
        ----------
        date_stripped_advisories: list
            Advisories to send with the date removed. The date appears in the email subject, we don't want to print it again for each line.
        """
        print("Sending Advisory Email.")

        port = 465
        smtp_server = "smtp.gmail.com"

        subject = f"Metro Advisory Report - {self.today}"
        body = "\n\n".join(date_stripped_advisories)

        # MIME is required to get the "Subject" to appear correctly.
        message = MIMEText(body, "plain")
        message['Subject'] = subject
        message['From'] = self.sender_email
        message['To'] = self.reciever_email

        # Using SSL to sign in.
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(self.sender_email, self.app_password)
            server.sendmail(message['From'],
                            message['To'], message.as_string())
            server.quit()


if __name__ == '__main__':
    cli_runner()
