#!/usr/bin/python3.5
 
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

def compare_page_items(api_values, page_values, year):
    print('api_values being passed to compare function: {}'.format(api_values))
    for key, val in page_values.items():
        pos = int(key.split(' - ')[1])
        comparison_val = val.split('=', 1)[1].strip()
        new_value = api_values[pos]
        if key == 'total_pop - 1':
            # format value correctly for comparison with page content
            new_value += ' ('+year+' est)'
            comparison_val = comparison_val[:comparison_val.find('<ref')].replace(',', '')
        print('value from api formatted: {}'.format(new_value))
        print('comparison_val: {}'.format(comparison_val))
        if comparison_val == new_value:
            print('value for {} is correct already - {}'.format(key.split(' - ')[0], new_value))
            page_values = removekey(page_values, key)
    return page_values

def update_page_items(page, text, api_values, page_values, year):
    for key, val in page_values.items(): 
        pos = int(key.split(' - ')[1])
        new_value = api_values[pos]
        if key == 'total_pop - 1':
            new_value = '{:,}'.format(int(new_value))+' ('+year+' est)<ref name=PopEstUS>{{cite web|'\
                        'url=https://www.census.gov/programs-surveys/popest.html |title=Population'\
                        ' and Housing Unit Estimates |date={} |accessdate={} |publisher=[[U.S. Census Bureau]]}}</ref>'\
                        .format(datetime.datetime.today().strftime('%B %d, %Y'), datetime.datetime.today().strftime('%B %d, %Y'))
        new_value = val.split('=', 1)[0] + '= ' + new_value + '\n'
        print('OLD:{}\nNEW:{}'.format(val, new_value))
        text = text.replace(val, new_value)
        page.text = text
        page.save(u'Updating population estimate and associated population rank (when applicable)'\
                    'with latest value from Census Bureau')

if __name__ == '__main__':
    get_var = 'GEONAME,POP'
    for_var = 'state:*'
    api_url = 'http://api.census.gov/data/XXXX/pep/population'
    api_key = config_funcs.getAppConfigParam('API', 'key')
    # the keys in this dict represent the 'property - position of corresponding value in api response
    # and the values represent the possible keys in which this property is listed under in the template
    infobox_keys = {'total_pop - 1': ['population_total', '2010Pop', '2000Pop', 'population_estimate'],
            'rank - 3': ['PopRank']
            }
    site = pywikibot.Site('en', 'wikipedia') 
    repo = site.data_repository()
    
    metric_values, year = get_census_values(api_url, get_var, for_var, api_key)
    if metric_values:
        #remove header
        metric_values.pop(0)
        metric_values = population_rank_sort(metric_values)
        print('Number of items in API Response: {}'.format(len(metric_values)))
        #for testing purposes of writing to my sandbox
        #metric_values = [['User:Sasan-CDS/sandbox', '624594', '50', '49th']]
        for i, api_val in enumerate(metric_values):
            key = api_val[0].split(',')[0]
            print('[STATE: {}]'.format(key))
            if key in ['Kansas', 'North Carolina', 'Georgia']:
                key = key + ', United States'
            elif key == 'Washington':
                key = 'Washington (state)'
            # remove DC and PR from Census API Response
            if api_val[2] in ['11', '72']:
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
                    print('template_values left over: {}'.format(template_values))
                    if template_values:
                        update_page_items(page, text, api_val, template_values, year)
                    else:
                        print('Nothing to update')
                else:
                    print('No items were found in this page!!!')
            else:
                print('NO RESULTS FOR: {}'.format(key))
    else:
        sys.exit('NO RESULTS FROM THE CENSUS API FOR ANY YEARS.  EXAMINE FOR OTHER ISSUES!')
