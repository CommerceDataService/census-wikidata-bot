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

#sort items by population (exluding PR and DC)
def population_rank_sort(pop_list):
    non_states = []
    for i, val in enumerate(pop_list):
        #11 and 72 are the FIPS 5-2 codes for PR and DC
        if val[2] in ['11', '72']:
            non_states.append(pop_list.pop(i))
    pop_list = sorted(pop_list, key=lambda x: int(x[1]), reverse=True)
    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
    for i, val in enumerate(pop_list):
        val.append(ordinal(i+1))
    #leaving this commented out for now because we decided to exclude these from
    #state processing
    #pop_list.extend(non_states)
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
        pos = int(key.split(' - ')[1])
        # extact value and normalize whitespace
        current_val = ' '.join(val.split('=', 1)[1].split())
        if pos == 99:
            api_value = year
        else:
            api_value = api_values[pos]
        if 'state' in for_var:
            if key == 'total_pop - 1':
                # format value correctly for comparison with page content
                api_value += ' ('+year+' est.)'
        if '<ref' in current_val:
            current_val = current_val[:current_val.find('<ref')]
        current_val = current_val.replace(',', '').replace('<br>', ' ')
        logging.info('KEY: {} | EXISTING VALUE: {} | NEW VALUE: {}'.format(key.split(' - ')[0], current_val, api_value))
        if current_val == api_value:
            logging.info('VALUES MATCH')
            page_values = removekey(page_values, key)
        else:
            logging.info('VALUES DO NOT MATCH')
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
        pos = int(key.split(' - ')[1])
        if pos == 99:
            new_value = year
        else:
            #new_value = api_values[pos]
            new_value = '{:,}'.format(int(api_values[pos]))
        # add reference and create comment
        if key == 'total_pop - 1':
            new_value = '{:,}'.format(int(new_value))+' ('+year+' est.)'+reference
            comment_vals.append(' total population ')
        else:
            comment_vals.append(' population rank ')
        # add property tag
        new_value = ' '.join(val.split('=', 1)[0].split())+' = '+new_value
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
    ## {prop_description} - {value position within api_values}: [{list of infobox key names}]
    # infobox_keys = {
    #     'total_pop - 1': ['population_total', '2010Pop', '2000Pop', 'population_estimate'],
    #     'rank - 3': ['PopRank']
    # }
    #reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
    #                    ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
    #                    .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    ## position of state code in API response
    #code_check_pos = 2
    ##DC and PR
    #exceptions = ['11', '72']
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
    # {prop_description} - {value position within api_values}: [{list of infobox key names}]
    infobox_keys = {
        'population - 1': ['pop', 'population_total', 'population'],
        'population_estimate - 1': ['population_est'],
        'population_as_of - 99': ['population_as_of'],
        'population_est_as_of - 99': ['pop_est_as_of', 'census_estimate_yr', 'census estimate yr',
                                      'population_date', 'census yr']
    }
    reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
                        ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
                        .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    # position of value in API response to check for exceptions
    code_check_pos = 2
    #DC and PR
    exceptions = ['11', '72']
    relevant_templates = ['Infobox settlement', 'Infobox U.S. county']
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
        #metric_values = population_rank_sort(metric_values)
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
                    if template.name in relevant_templates:
                        template_found = True
                    # if correct template is found, break out of loop
                    if template_values:
                        break
                    else:
                        template_values = search_for_page_items(template, infobox_keys)
                if template_values:
                    if 'population_estimate - 1' in template_values:
                        logging.info('Ignoring population_total and population_as_of properties due to presence of population_estimate property')
                        del template_values['population - 1']
                        if 'population_as_of - 99' in template_values:
                            del template_values['population_as_of - 99']
                        elif 'population_est_as_of - 99' in template_values:
                            del template_values['population_est_as_of - 99']
                    #compare page items
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
                    if template_found:
                        logging.warning('No items were found in this page!!!')
                    else:
                        logging.warning('None of the relevant templates were found on this page!!!')
                    num_of_not_founds += 1
            else:
                logging.warning('NO RESULTS FOR: {}'.format(key))
                num_of_pages_not_found += 1
        logging.info('TOTAL NUMBER OF EDITS: {}'.format(num_of_edits))
        logging.info('TOTAL NUMBER OF PAGES WHERE NOTHING FOUND: {}'.format(num_of_not_founds))
        logging.info('TOTAL NUMBER OF PAGES NOT FOUND: {}'.format(num_of_pages_not_found))
    else:
        sys.exit('NO RESULTS FROM THE CENSUS API FOR ANY YEARS.  EXAMINE FOR OTHER ISSUES!')
