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

In order to get this working, navigate to the metrolink_advisories.py script and follow the instructions at the top. You will need to fill in 3 variables, along with your train numbers.


It is recommended to run this script on a linux server but if you want to set it up on a local machine, you can use the [Windows Task Scheduler](https://stackoverflow.com/questions/4249542/run-a-task-every-x-minutes-with-windows-task-scheduler) (keep in mind, your machine must be on and connected to the internet in order for you to receive email updates).

If you are running a linux server, just run this script with a [cronjob](https://askubuntu.com/questions/799023/how-to-set-up-a-cron-job-to-run-every-10-minutes) every 5 minutes or so.

Please note that the requests_html library used in this script doesn't support ARM devices (such as raspberry pi).

Note that this script is not endorsed, supported by, or affiliated with Metrolink.
