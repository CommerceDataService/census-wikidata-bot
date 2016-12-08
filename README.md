# census-wikidata-bot

![U.S. Census Bureau logo](https://upload.wikimedia.org/wikipedia/commons/8/85/Seal_of_the_United_States_Census_Bureau.svg)

This project contains code for a bot.  This bot is made to interact with [Wikidata] (https://www.wikidata.org/wiki/Wikidata:Main_Page).  This bot is designed to use Census data specifically and push it to wikidata if a page exists for the subject matter.

## Setup
In order to set up this bot to run, a wikidata account with a bot flag approval is necessary.  This bot uses python 3.5 and the main library for interaction with the Wikidata API is [Pywikibot] (https://www.mediawiki.org/wiki/Manual:Pywikibot).  The configuration file for this bot is contained in *user-config.py*.

In the this file, insert your user account in the following line:<br>
`usernames['sitename']['en'] = u'ExampleBot'`

The `mylang` and `family` parameters will also need to be set accordingly.  Please refer to the documentation for Pywikibot for additional information regarding this.

Lastly, for testing purposes, there is a `mode` parameter contained in the `addPopValues.py` file.  This can be set to either `test` or `wikidata`.  This determines whether the test site or production property tags will be used.

## Scope
Currently, this bot is only set up to use a static file containing U.S. state population values for 2015.  The bot will use these values to search and see if a page exists for that state.  If a single result is found, it will access the page and check if the population statement is present.  If so, it will check the claims.  If there is a claim with no `point in time` value, it will be deleted.  Subsequently, it will check for any entries referring to a `2015` point in time.  If it finds any it will check them for completeness.  if anything is off, it will delete that entry and make a new complete entry.  If no population statement is present or if no 2015 entry for population is present it will add that to the page.  Currently, there is a page for Arizona, Oregon, California, and Virginia on the test site which this bot will find.

## Future Scope
Going forward, there will be changes to the functionality of this bot and the range of data that it accesses and inserts into Wikidata.  This page will be periodically accordingly.
