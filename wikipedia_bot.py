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

def search_for_page_items(template, infobox_keys):
    template_values = {}
    for key, wiki_properties in infobox_keys.items():
        for prop_name in wiki_properties:
            if template.has(prop_name):
                template_values[key] = str(template.get(prop_name))
                logging.info('KEY - {} Found'.format(prop_name))
                break
    return template_values

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

#remove value from dict and return copy rather than mutated dict
def removekey(d, key):
    r = dict(d)
    del r[key]
    return r

# compare value from page to value from API to check for discrepancies
# *note - this function does not compare references, only values
def compare_page_items(api_values, page_values, year):
    for key, val in page_values.items():
        # extact value and normalize whitespace
        current_val = ' '.join(val.split('=', 1)[1].split())
        if key.startswith('pop'):
            api_value = api_values[1]
        elif key.startswith('rank'):
            api_value = api_values[3]
        elif key.startswith('year'):
            api_value = year
        elif key.startswith('ref'):
            continue # don't compare ref property

        # standardize text to compare statistics
        if 'state' in for_var and key.startswith('pop'):
            api_value += ' ('+year+' est.)'
        if '<ref' in current_val:
            current_val = current_val[:current_val.find('<ref')]
        current_val = current_val.replace(',', '').replace('<br>', ' ')

        logging.info('KEY: {} | EXISTING VALUE: {} | NEW VALUE: {}'.format(key, current_val, api_value))
        if current_val == api_value:
            logging.info('VALUES MATCH')
            page_values = removekey(page_values, key)
        else:
            logging.info('VALUES DO NOT MATCH')
    # empty dict if only the ref property is left
    if len(page_values) == 1 and next(iter(page_values)).startswith('ref'):
        page_values.clear()
    return page_values

def create_comment(comment_vals):
    comment = ''
    beg = 'Updating'
    end = 'with latest data from US Census Bureau.'
    comment = beg + 'and'.join(comment_vals) + end
    return comment

def update_page_items(page, text, api_values, page_values, year, reference):
    global num_of_edits
    comment_vals = []
    for key, val in page_values.items():
        if key.startswith('pop'):
            new_value = api_values[1]
        elif key.startswith('rank'):
            new_value = api_values[3]
        elif key.startswith('year'):
            new_value = year
        elif key.startswith('ref'):
            new_value = reference

        # format text to match wiki conventions
        if 'state' in for_var and key.startswith('pop'):
            new_value += ' (' + year + ' est.)'
        if key.endswith('with_ref'):
            new_value += reference

        if key.startswith('rank'):
            comment_vals.append(' population rank ')
        elif key.startswith('pop'):
            comment_vals.append(' total population ')

        # add property tag
        new_value = val.split('=', 1)[0] + '= ' + new_value
        # add new line tag
        new_value += '\n'
        logging.info('FULL EXISTING VALUE: {}\nFULL REPLACEMENT VALUE: {}'.format(val, new_value))
        text = text.replace(val, new_value)
    comment = create_comment(comment_vals)
    if not args.debug:
        page.text = text
        page.save(comment)
        logging.info('Page Successfully Updated')
    else:
        logging.info('DEBUG - Page value will be updated')
    num_of_edits += 1

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
    if args.numedits:
        logging.info('      NUMBER OF EDITS:{}'.format(args.numedits))
    logging.info("----------- [JOB START] -----------")

    # state set of configs
    #get_var = 'GEONAME,POP'
    #for_var = 'state:*'
    #api_url = 'http://api.census.gov/data/XXXX/pep/population'
    #api_key = config_funcs.getAppConfigParam('API', 'key')

    ## This dict represents the properties we will be searching for within the infoboxes. Some
    ## properties are represented by multiple infobox keys. An entry in the dict is formatted as:
    ## {prop_description} : [{list of infobox key names}]
    ## 'with_ref' indicates the value should be appeneded with a wiki-style citation
    ## 'alt' indicates these keys should be ignored if a non-alt version is also found
    # infobox_keys = {
    #     'pop_with_ref': ['population_total', '2010Pop', '2000Pop', 'population_estimate'],
    #     'rank': ['PopRank']
    # }
    #reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
    #                    ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
    #                    .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    ## position of state code in API response
    #code_check_pos = 2
    ##DC and PR
    #exceptions = ['11', '72']
    #relevant_templates = [x.lower() for x in ['Infobox U.S. state', 'US state']]
    #key_exceptions = {'Kansas': 'Kansas, United States', 'North Carolina': 'North Carolina, United States',
    #        'Georgia': 'Georgia, United States', 'Washington': 'Washington (state)'}
    #test_data = [['User:Sasan-CDS/sandbox', '555555', '50', '11th']]

    #county parameters
    get_var = 'GEONAME,POP'
    for_var = 'county:*'
    api_url = 'http://api.census.gov/data/XXXX/pep/population'
    api_key = config_funcs.getAppConfigParam('API', 'key')

    # This dict represents the properties we will be searching for within the infoboxes. Some
    # properties are represented by multiple infobox keys. An entry in the dict is formatted as:
    # {prop_description} : [{list of infobox key names}]
    # 'with_ref' indicates the value should be appeneded with a wiki-style citation
    # 'alt' indicates these keys should be ignored if a non-alt version is also found
    infobox_keys = {
        'pop': ['population_est'],
        'pop_with_ref': ['pop'],
        'pop_alt': ['population_total'],
        'year': ['pop_est_as_of', 'census_estimate_yr', 'census estimate yr'],
        'year_alt': ['population_as_of', 'census yr'],
        'ref': ['pop_est_footnotes'],
        'ref_alt': ['population_footnotes']
    }
    reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
                        ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
                        .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    # position of value in API response to check for exceptions
    code_check_pos = 2
    #DC and PR
    exceptions = ['11', '72']
    # 'Geobox Settlement' and 'Geobox Region' would match, but are deprecated and we'll ignore for now
    relevant_templates = [x.lower() for x in ['Infobox settlement', 'Infobox U.S. County', 'US County infobox']]
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
            page = pywikibot.Page(site, key)
            if page.exists():
                if page.isRedirectPage():
                    page = page.getRedirectTarget()
                text = page.get(get_redirect=True)
                code = mwparserfromhell.parse(text)

                template_values = {}
                template_found = False
                for template in code.filter_templates():
                    # Some of the template names returned by the parser contain comments,
                    # but these occur after the Infobox name. So we need to check if the
                    # beginning of the template name matches one of our targets
                    if template.name.lower().startswith(tuple(relevant_templates)):
                        template_found = True
                        template_values = search_for_page_items(template, infobox_keys)
                        break
                if template_values:
                    # Given the Wiki keys found, determine which we will update
                    if 'pop' in template_values or 'pop_with_ref' in template_values:
                        logging.info('Ignoring population_total and population_as_of properties due to presence of population_estimate property')
                        template_values.pop('pop_alt', None)
                        template_values.pop('year_alt', None)
                    if 'pop_with_ref' in template_values:
                        logging.info('Ignoring reference properties because reference will be included with population')
                        template_values.pop('ref', None)
                        template_values.pop('ref_alt', None)
                    else:
                        if 'pop' in template_values:
                            logging.info('Ignoring population_footnotes')
                            template_values.pop('ref_alt', None)
                        elif 'pop_alt' in template_values:
                            logging.info('Ignoring pop_est_footnotes')
                            template_values.pop('ref', None)
                        else:
                            logging.warning('Unexpected combination of Wiki keys found. Unsure how to add wiki reference citation.')

                    # Compare and update page items
                    template_values = compare_page_items(api_val, template_values, year)
                    if template_values:
                        update_page_items(page, text, api_val, template_values, year, reference)
                        logging.info('Number of edits: {}'.format(num_of_edits))
                        if args.numedits and num_of_edits >= args.numedits:
                            logging.info('Number of maximum edits({}) has been reached and bot will not perform any further updates'.format(args.numedits))
                            break
                    else:
                        logging.info('Nothing to update')
                else:
                    num_of_not_founds += 1
                    if template_found:
                        logging.warning('No items were found in this page!!!')
                    else:
                        logging.warning('None of the relevant templates were found on this page!!!')
            else:
                logging.warning('NO PAGE FOUND FOR: {}'.format(key))
                num_of_pages_not_found += 1
        logging.info('TOTAL NUMBER OF EDITS: {}'.format(num_of_edits))
        logging.info('TOTAL NUMBER OF PAGES WHERE NOTHING FOUND: {}'.format(num_of_not_founds))
        logging.info('TOTAL NUMBER OF PAGES NOT FOUND: {}'.format(num_of_pages_not_found))
    else:
        sys.exit('NO RESULTS FROM THE CENSUS API FOR ANY YEARS.  EXAMINE FOR OTHER ISSUES!')
