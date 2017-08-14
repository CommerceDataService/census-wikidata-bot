#!/usr/bin/python3.5

#Author:        Sasan Bahadaran
#Date:          5/1/17
#Organization:  Commerce Data Service
#Description:   This is a bot script for getting Census data from the Census
#Bureau API's and writing it to Wikipedia.

import pywikibot, json, os, requests, argparse, logging, time, json, sys
import mwparserfromhell, datetime, math
from pywikibot.data import api
from util import config_funcs
from difflib import unified_diff

#get values from CENSUS API.  Return response from first year with valid response starting with
#current year and ending with 2013
def get_census_values(api_url, get_var, for_var, api_key, year=datetime.datetime.today().year):
    try:
        while year >= 2013:
            payload = {'get': get_var, 'for': for_var, 'key': api_key}
            r = requests.get(api_url.replace('XXXX', str(year)), params=payload)
            if r.status_code == 200:
                return r.json(), str(year)
            else:
                logging.info('No API Results for year: {}'.format(year))
                year = year - 1
        else:
            return
    except requests.exceptions.RequestException as e:
        logging.error('General Exception: {}'.format(e))
    except IOError as err:
        logging.error('IOError: {}'.format(err))

#sort items by population
def population_rank_sort(pop_list):
    non_states = []
    for i, val in enumerate(pop_list):
        # PR and DC should not be counted within the 50 states for rank
        if val[2] in ['11', '72']:
            non_states.append(pop_list.pop(i))
    pop_list = sorted(pop_list, key=lambda x: int(x[1]), reverse=True)

    # via https://stackoverflow.com/a/20007730
    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
    for i, val in enumerate(pop_list):
        val.append(ordinal(i+1))
    return pop_list

# Determine if the provided template name matches a given list of
# potential matches
def template_name_matches(name, targets):
    if type(targets) is not list: targets = [targets]
    targets = [x.lower() for x in targets]

    # Some of the template names returned by the parser contain comments,
    # but these occur after the Infobox name. So we need to check if the
    # beginning of the template name matches one of our targets
    #
    # Note: WikiCode objects have a 'matches' method, but in testing this
    # returns inconsistent results with our template names
    # https://mwparserfromhell.readthedocs.io/en/latest/api/mwparserfromhell.html#mwparserfromhell.wikicode.Wikicode.matches
    return name.lower().startswith(tuple(targets))

# Given a template, update the properties to provide the current
# Census values. This involves determining if the values need
# to be updated and if properties need to be added/removed.
def update_template(template, api_val, year, reference):
    # The changes that need to be made are very specific to
    # the template being used, so we'll address each of those
    # cases specifically
    #
    # Template API:
    # https://mwparserfromhell.readthedocs.io/en/latest/api/mwparserfromhell.nodes.html#module-mwparserfromhell.nodes.template
    made_edit = False
    if template_name_matches(template.name, ['Infobox settlement']):
        # https://en.wikipedia.org/wiki/Template:Infobox_settlement
        if(
            not template.has('population_est') or
            clean_wiki_param(template.get('population_est').value) != api_val[1]
        ):
            # population_total doesn't impact the display of population_est
            template.add('population_est', api_val[1], before='population_total')
            template.add('pop_est_as_of', year, before='population_est')
            template.add('pop_est_footnotes', reference, before='population_est')
            made_edit = True
    elif template_name_matches(template.name, ['Infobox U.S. County', 'US County infobox']):
        # https://en.wikipedia.org/wiki/Template:Infobox_U.S._county
        # 'census est yr' is only used as long as 'census yr' is not present
        current = clean_wiki_param(template.get('pop').value)
        if current != api_val[1]:
            template.add('pop', api_val[1] + reference)
            template.add('census estimate yr', year, before='pop')
            if template.has('census yr'):
                template.remove('census yr')
            if template.has('census_estimate_yr'):
                template.remove('census_estimate_yr')
            made_edit = True
    elif template_name_matches(template.name, ['Infobox U.S. state', 'US state']):
        # https://en.wikipedia.org/wiki/Template:Infobox_U.S._state
        # Each of these properties is used inconsistently but accopmlishes
        # the same thing
        for prop in ['population_total', '2010Pop', '2000Pop', 'population_estimate']:
            if template.has(prop):
                current = clean_wiki_param(template.get(prop).value)
                new_pop = api_val[1] + ' (' + year + ' est.)'
                if current != new_pop or str(template.get('PopRank').value.strip()) != api_val[3]:
                    template.add(prop, new_pop + reference)
                    template.add('PopRank', api_val[3], before=prop)
                    made_edit = True
                break
    else:
        logging.warning('Template name match not found!!!')

    return str(template), made_edit

# Translate the wiki parameter into a raw value that we can compare against
def clean_wiki_param(param):
    return str(param).split('<ref', 1)[0].replace(',', '').replace('<br>', ' ').strip()

# Generate a git-style diff to compare changes in the wikicode
def generate_diff(old_text, new_text):
    diff = unified_diff(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True))
    diff = list(diff)
    return ''.join(diff)

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))

    #logging configuration
    logging.basicConfig(
                        filename='logs/wikipedia_bot-log-'+time.strftime('%Y%m%d'),
                        level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s -%(message)s',
                        datefmt='%Y%m%d %H:%M:%S'
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
                        '-m',
                        '--mode',
                        required=True,
                        type=str,
                        choices=['t', 'p'],
                        help='Pass a t flag for test mode or a p flag for production mode'
    )
    parser.add_argument(
                        '-d',
                        '--debug',
                        required=False,
                        action='store_true',
                        default=False,
                        help='Pass this flag to set mode of bot to debug (means there will be no actual changes to the Wiki)'
    )
    parser.add_argument(
                        '-n',
                        '--numedits',
                        required=False,
                        type=int,
                        help='Pass this flag to control the number of edits that the bot makes.'
    )
    args = parser.parse_args()
    logging.info("-------- [SCRIPT ARGUMENTS] --------")
    if args.mode == 't':
        logging.info('      BOT MODE: TEST')
    elif args.mode == 'p':
        logging.info('      BOT MODE: PROD')
    if args.debug:
        logging.info('      !RUNNING IN DEBUG MODE!')
    else:
        print("**** THIS WILL UPDATE WIKIPEDIA ****")
    if args.numedits:
        logging.info('      NUMBER OF EDITS:{}'.format(args.numedits))
    logging.info("----------- [JOB START] -----------")

    # state set of configs
    #get_var = 'GEONAME,POP'
    #for_var = 'state:*'
    #api_url = 'http://api.census.gov/data/XXXX/pep/population'
    #api_key = config_funcs.getAppConfigParam('API', 'key')

    #reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
    #                    ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
    #                    .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    ## position of state code in API response
    #code_check_pos = 2
    ##DC and PR
    #exceptions = ['11', '72']
    #relevant_templates = ['Infobox U.S. state', 'US state']
    #key_exceptions = {'Kansas': 'Kansas, United States', 'North Carolina': 'North Carolina, United States',
    #        'Georgia': 'Georgia, United States', 'Washington': 'Washington (state)'}
    #test_data = [['User:Sasan-CDS/sandbox', '555555', '50', '11th']]

    #county parameters
    get_var = 'GEONAME,POP'
    for_var = 'county:*'
    api_url = 'http://api.census.gov/data/XXXX/pep/population'
    api_key = config_funcs.getAppConfigParam('API', 'key')

    reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
                        ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
                        .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    # position of value in API response to check for exceptions
    code_check_pos = 2
    #DC and PR
    exceptions = ['11', '72']
    # 'Geobox Settlement' and 'Geobox Region' would match, but are deprecated and we'll ignore for now
    relevant_templates = ['Infobox settlement', 'Infobox U.S. County', 'US County infobox']
    key_exceptions = {'Winchester city, Virginia': 'Winchester, Virginia', 'Waynesboro city, Virginia': 'Waynesboro, Virginia',
            'Virginia Beach city, Virginia': 'Virginia Beach, Virginia', 'Suffolk city, Virginia': 'Suffolk, Virginia',
            'St. Louis city, Missouri': 'St. Louis, Missouri','Salem city, Virginia': 'Salem, Virginia', 
            'Roanoke city, Virginia': 'Roanoke, Virginia', 'Radford city, Virginia': 'Radford, Virginia', 
            'Portsmouth city, Virginia': 'Portsmouth, Virginia', 'Poquoson city, Virginia': 'Poquoson, Virginia', 
            'Newport News city, Virginia': 'Newport News, Virginia', 'Manassas city, Virginia': 'Manassas, Virginia', 
            'Lynchburg city, Virginia': 'Lynchburg, Virginia', 'Lexington city, Virginia': 'Lexington, Virginia', 
            'Franklin city, Virginia': 'Franklin, Virginia', 'Emporia city, Virginia': 'Emporia, Virginia', 
            'Covington city, Virginia': 'Covington, Virginia', 'Buena Vista city, Virginia': 'Buena Vista, Virginia', 
            'Baltimore city, Maryland': 'Baltimore, Maryland', 'Alexandria city, Virginia': 'Alexandria, Virginia'
            } 
    test_data = [['User:Sasan-CDS/sandbox', '555555', '50']]

    num_of_pages_not_found = 0
    num_of_not_founds = 0
    num_of_edits = 0
    site = pywikibot.Site('en', 'wikipedia') 
    repo = site.data_repository()
    
    if args.mode == 'p':
        metric_values, year = get_census_values(api_url, get_var, for_var, api_key)
        #remove header
        metric_values.pop(0)
        if 'state' in for_var:
            metric_values = population_rank_sort(metric_values)
    else:
        metric_values = test_data
        year = '2016'
    if metric_values:
        logging.info('Number of items in API Response: {}'.format(len(metric_values)))
        for i, api_val in enumerate(metric_values):
            logging.info('API item: {}'.format(api_val))
            #key = api_val[0].split(',')[0]
            key = api_val[0]
            logging.info('[ITEM: {}]'.format(key))
            if key in key_exceptions:
                key = key_exceptions[key]
                logging.info('Key exception found. new key: {}'.format(key))
            if api_val[code_check_pos] in exceptions:
                logging.info('Item being skipped due to configuration settings')
                continue
            if not api_val[1].isdecimal():
                logging.info('Skipping item. Element is not a population value: {}'.format(api_val[1]))
                continue

            page = pywikibot.Page(site, key)
            if page.exists():
                if page.isRedirectPage():
                    page = page.getRedirectTarget()
                text = page.get(get_redirect=True)
                code = mwparserfromhell.parse(text)

                infobox_template = {}
                for template in code.filter_templates():
                    if template_name_matches(template.name, relevant_templates):
                        infobox_template = template
                        break
                if infobox_template:
                    old_text = str(infobox_template)
                    new_text, made_edit = update_template(infobox_template, api_val, year, reference)
                    if made_edit:
                        num_of_edits += 1
                        logging.info('CHANGES TO SAVE:\n' + generate_diff(old_text, new_text))
                        if not args.debug:
                            page.text = text.replace(old_text, new_text)
                            page.save('Updating population estimate with latest data from US Census Bureau.')
                            logging.info('Page Successfully Updated')
                        else:
                            logging.info('DEBUG - Page value will be updated')
                        logging.info('Number of edits: {}'.format(num_of_edits))
                        if args.numedits and num_of_edits >= args.numedits:
                            logging.info('Number of maximum edits({}) has been reached and bot will not perform any further updates'.format(args.numedits))
                            break
                    else:
                        logging.info('POPULATION MATCHES. No edit made.')
                else:
                    logging.warning('None of the relevant templates were found on this page!!!')
                    num_of_not_founds += 1
            else:
                logging.warning('NO PAGE FOUND FOR: {}'.format(key))
                num_of_pages_not_found += 1
        logging.info('TOTAL NUMBER OF EDITS: {}'.format(num_of_edits))
        logging.info('TOTAL NUMBER OF PAGES WHERE NOTHING FOUND: {}'.format(num_of_not_founds))
        logging.info('TOTAL NUMBER OF PAGES NOT FOUND: {}'.format(num_of_pages_not_found))
    else:
        sys.exit('NO RESULTS FROM THE CENSUS API FOR ANY YEARS.  EXAMINE FOR OTHER ISSUES!')
