# MetrolinkAdvisoryEmailer
Python 3.7.2 script that emails you about MetroLink advisories for your trains.

This is set up to work with the following MetroLink lines:
* Antelope Valley
* Inland Empire-Orange County
* Orange County
* Riverside
* San Bernardino
* Ventura County
* 91/Perris Valley

Currently, this is one of the only ways to get email updates from Metrolink about specific train advisories (which is why I created it.)

In order to get this working, navigate to the metrolink_advisories.py script and follow the instructions at the top. You will need to fill in a handful of variables along with your train numbers.

It is recommended to run this on a Linux server.

Please note that the requests_html library used in this script doesn't support ARM devices (such as raspberry pi), and is complex to set up with a Docker container.

Note that this script is not endorsed, supported by, or affiliated with Metrolink.
