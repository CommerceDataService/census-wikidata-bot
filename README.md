# census-wikidata-bot

![Census-bot-logo](https://raw.githubusercontent.com/CommerceDataService/census-wikidata-bot/master/images/census_wiki_bot.jpg)

This suite of bots interact with [Wikidata](https://www.wikidata.org/wiki/Wikidata:Main_Page) and [Wikipedia](https://en.wikipedia.org/wiki/Main_Page) using the [Pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot) library.  These bots are designed specifically for pushing Census data to specified Wikis, and have been created in collaboration with the [U.S. Census Bureau](https://www.census.gov/).

## Setup

#### Accounts and Bot Approval
In order to use these bots, you must create an account for each Wiki and receive bot approval in order to operate as a bot.  More information for Wikidata can be found [here](https://www.wikidata.org/wiki/Wikidata:Bots) and for Wikipedia [here](https://en.wikipedia.org/wiki/Wikipedia:Bots).

#### Pywikibot User Configuration

###### user-config.py
This file should contain the information that Pywikibot uses to log a user into a specified wiki.  You will include your user account information in this file.  A sample file (`user-config.py.sample`) has been provided to use.

###### user-password.py
This file should contain passwords for your bots.  This is optional.  A sample file (`user-password.py.sample`) has been provided to use.

###### Logging in
After the above files have been set up, you may run the login script (`login.py`) to login in to all of your wiki accounts.  In order to do this, you may run the following:

`python login.py -all`

If the script was successful, you should see messages that you have been logged in to each wiki you specified in your configuration.

In order to log out of these wikis, you may run:

`python login.py -all -logout`

###### app-config.ini
This file should contain the API key that will be provided to you after registering with the Census Bureau.  In order to obtain a Census API key, refer to the following [page](http://api.census.gov/data/key_signup.html).  A sample file ('app_config.ini.sample') has been provided.

###### Data Configuration files
This application contains data configuration files that instruct bots on where and how to look for source data, as well as how to push that data to wikis.  These files are contained in the `/data` directory.  These files are split up into Wikidata production and test cases.  `data.json` is for the Wikidata production [site](https://www.wikidata.org/) and `data_test.json` is for the test [site](test.wikidata.org) (*Note, currently, these files are not used for Wikipedia since that bot is still in development*).  Currently, these files are populated with initial configurations used for these bots, but you may change or add to them as needed.  These files are in JSON format, and the schema is defined in `census_bot_data.schema.json`.  

Lastly, `reference.json` contains definitions of wiki property tags and what that property represents in order to make understanding of the tags defined in the main data files easier.

## Running The Bots
Once all setup has been completed, the Wikidata bot can be run by executing `census_bot.py` and the Wikipedia bot can be run by executing `wikipedia_test_bot.py`.

### Modes of execution
Currently, the wikipedia bot does not take any arguments (*still in development*).  The Wikidata bot can be run using different modes.  More information about argument usage is available by using  `--help`.  The following modes are available for running the Wikidata bot are available:

###### Test
The `-m t` argument can be passed to the script in order to run it in test mode.  This allows the bot to communicate with the [test site](test.wikidata.org) instead of the [production site](https://www.wikidata.org/).  In order to have pages to test against, you must create test pages and make sure you are referring to the proper values in your configuration file.

###### Production
The `-m p` argument can be passed to the script in order to run it in production mode (i.e., use the [main site](https://www.wikidata.org) ).

###### Debug
The `-d` argument can be passed to the script in order to run it in debug mode.  This will allow you to run the script on test or production without actually making any edits.

### Logging
Logs for bot actions are available in the '/logs' directory.  Log filenames are prefaced with `censusbot-log`+`YYYYMMDD`.

## How The Wikidata Bot Operates
The bot searches for values specified in the data configuration files (as explained above).  If the bot finds a single result for a particular wiki search, it will access that result page and check if the statement it is instructed to look for is present.  If so, it will check the claims for that statement.  If there is a claim with no `point in time` value, it will be deleted.  Subsequently, it will check for any entries referring to the specified point in time year.  If any entries are found they will be checked for completeness.  if any entry is incomplete, it will be deleted and a new complete entry will be created instead.  If no entries are present for the specified statement or point in time, the bot will create add one.





*This README contains a repository image which uses logos for the U.S. Census Bureau, Wikidata, and Wikipedia.*
