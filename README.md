# MetrolinkAdvisoryEmailer
Recieve emails when your trains are delayed.

This is set up to work with the following MetroLink lines:
* Antelope Valley
* Inland Empire-Orange County
* Orange County
* Riverside
* San Bernardino
* Ventura County
* 91/Perris Valley

# Setup
You'll need python3 and pip. Instructions are [here](https://pip.pypa.io/en/stable/installing/) and [here](https://www.python.org/downloads/). Ensure python is added to path.

Then run `pip install -r requirements.txt` in the project folder.

You can now run the script with `python .\advisories.py`.

The script will install headless chromium on first run, which is required for the JS to runs against the website.

# Running
There are two ways to run the script, one via passing arguments over command line, and the other using a config file.

Here's an example for passing cli arguments - `python .\advisories.py --sender_email tklusz@gmail.com --app_password abcdefghijklmnop --reciever_email tklusz@gmail.com -t 806 -t 101 -t 201`

And an example for using a config file - `python .\advisories.py --config_file config_example.json`

For an example of the config file, see `config_example.json`.

If you pass both CLI arguments and a config file, only the config file will be used.

The reciever_email is optional for both the config file and command line arguments, if unset it will use the sender_email as the reciever_email.

The script will also create a `.metro_advisories_notified.txt` file to avoid sending repeat advisories. It will clean itself up automatically over time.

# Automation
You can run this on a linux server with cron which is probably the most simple way.
Note that the requests_html library doesn't support ARM devices like raspbery pi and can be complex to set up with Docker.

This script is not endorsed, supported by, or affiliated with Metrolink.
