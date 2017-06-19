#!pi_values/usr/bin/python3.5
 
#Author:        Sasan Bahadaran
#Date:          5/1/17
#Organization:  Commerce Data Service
#Description:   This is a bot script for getting Census data from the Census
#Bureau API's and writing it to Wikipedia.

import pywikibot, json, os, requests, argparse, logging, time, json, sys
import mwparserfromhell, datetime, math
from pywikibot.data import api
from pywikibot import pagegenerators
from util import config_funcs


#get values from CENSUS API.  Return response from first year with valid response starting with
#current year and ending with 2013
def get_census_values(api_url, get_var, for_var, api_key, year=datetime.datetime.today().year):
    try:
        year = datetime.datetime.today().year
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
    for item, item_keys in infobox_keys.items():
        for key in item_keys:
            if template.has(key):
                template_values[item] = str(template.get(key))
                print('KEY - {} Found'.format(key))
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
    for i,val in enumerate(pop_list):
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
        api_value = api_values[pos]
        if key == 'total_pop - 1':
            # format value correctly for comparison with page content
            api_value += ' ('+year+' est)'
            # remove reference, commas, and any <br> tags
            current_val = current_val[:current_val.find('<ref')].replace(',', '').replace('<br>', ' ')
        print('KEY: {} | EXISTING VALUE: {} | NEW VALUE: {}'.format(key.split(' - ')[0], current_val, api_value))
        if current_val == api_value:
            print('VALUES MATCH')
            page_values = removekey(page_values, key)
        else:
            print('VALUES DO NOT MATCH')
    return page_values

def update_page_items(page, text, api_values, page_values, year, reference, comment):
    for key, val in page_values.items(): 
        pos = int(key.split(' - ')[1])
        new_value = api_values[pos]
        # add reference for total population
        if key == 'total_pop - 1':
            new_value = '{:,}'.format(int(new_value))+' ('+year+' est)'+reference
        else:
            index = comment.find('with')
            comment = comment[:index]+' and associated population rank '+comment[index:]
        # add property tag
        new_value = ' '.join(val.split('=', 1)[0].split())+' = '+new_value
        # add new line tag
        new_value += '\n'
        print('FULL EXISTING VALUE: {}\nFULL REPLACEMENT VALUE: {}'.format(val, new_value))
        if not args.debug:
            text = text.replace(val, new_value)
            page.text = text
            page.save(comment)
            print('Page Successfully Updated')
            num_of_edits += 1
        else:
            print('DEBUG - Page value will be updated')
            num_of_edits += 1

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
   
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
    opt = parser.add_argument(
                              '-s',
                              '--sandbox'
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

    # can be used later for config file
    #data_file = os.path.join(scriptpath, "data", "data.json")

    get_var = 'GEONAME,POP'
    for_var = 'state:*'
    api_url = 'http://api.census.gov/data/XXXX/pep/population'
    api_key = config_funcs.getAppConfigParam('API', 'key')
    # the keys in this dict represent the 'property - position of corresponding value in api response
    # and the values represent the possible keys in which this property is listed under in the template
    infobox_keys = {'total_pop - 1': ['population_total', '2010Pop', '2000Pop', 'population_estimate'],
            'rank - 3': ['PopRank']
            }
    reference = '<ref name=PopHousingEst>{{{{cite web|url=https://www.census.gov/programs-surveys/popest.html|title=Population'\
                        ' and Housing Unit Estimates |date={} |accessdate={}|publisher=[[U.S. Census Bureau]]}}}}</ref>'\
                        .format(datetime.datetime.today().strftime('%B %-d, %Y'), datetime.datetime.today().strftime('%B %-d, %Y'))
    comment = 'Updating population estimate with latest data from Census Bureau'
    # position of state code in API response
    code_check_pos = 2
    #DC and PR
    exceptions = ['11', '72']
    key_exceptions = {'Kansas': 'Kansas, United States', 'North Carolina': 'North Carolina, United States',
            'Georgia': 'Georgia, United States', 'Washington': 'Washington (state)'}
    # add conditional argument to argparse to make required to add sandbox user if test mode
    #test_data = [['User:'+args.sandbox+'/sandbox', '555555', '50', '11th']]
    # to be used for testing
    num_of_edits = 0
    site = pywikibot.Site('en', 'wikipedia') 
    repo = site.data_repository()
    
    if args.mode == 'p':
        metric_values, year = get_census_values(api_url, get_var, for_var, api_key)
        #remove header
        metric_values.pop(0)
        metric_values = population_rank_sort(metric_values)
    else:
        metric_values = test_data
        year = '2016'
    if metric_values:
        print('Number of items in API Response: {}'.format(len(metric_values)))
        for i, api_val in enumerate(metric_values):
            print('API item: {}'.format(api_val))
            key = api_val[0].split(',')[0]
            print('[STATE: {}]'.format(key))
            if key in key_exceptions:
                key = key_exceptions[key]
                print('Key exception found. new key: {}'.format(key))
            if api_val[code_check_pos] in exceptions:
                metric_values.pop(i)
            page = pywikibot.Page(site, key)
            if page.exists():
                if page.isRedirectPage():
                    page = page.getRedirectTarget()
                text = page.get(get_redirect=True)
                code = mwparserfromhell.parse(text)
                template_values = {}
                for template in code.filter_templates():
                    # if correct template is found, break out of loop
                    if template_values:
                        break
                    else:
                        template_values = search_for_page_items(template, infobox_keys)
                if template_values:
                    #compare page items
                    template_values = compare_page_items(api_val, template_values, year)
                    if template_values:
                        if args.numedits: 
                            if num_of_edits < args.numedits:
                                update_page_items(page, text, api_val, template_values, year, reference, comment)
                                logging.info('Number of edits: {}'.format(num_of_edits))
                            else:
                                logging.info('Number of maximum edits({}) has been reached and bot will not perform any further updates') 
                        else:
                            update_page_items(page, text, api_val, template_values, year, reference, comment)
                    else:
                        print('Nothing to update')
                else:
                    print('No items were found in this page!!!')
            else:
                print('NO RESULTS FOR: {}'.format(key))
    else:
        sys.exit('NO RESULTS FROM THE CENSUS API FOR ANY YEARS.  EXAMINE FOR OTHER ISSUES!')
