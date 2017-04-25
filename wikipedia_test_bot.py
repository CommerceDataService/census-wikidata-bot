import pywikibot, json, os, requests, argparse, logging, time, json, sys
import mwparserfromhell, datetime
from pywikibot.data import api
from pywikibot import pagegenerators

#get values from CENSUS API.  Return response from first year with valid response starting with
#current year and ending with 2013
def get_census_values(api_url, get_var, for_var, api_key, year=datetime.datetime.today().year):
    try:
        year = datetime.datetime.today().year
        while year >= 2013:
            payload = {'get': get_var, 'for': for_var, 'key': api_key}
            r = requests.get(api_url.replace('XXXX', str(year)), params=payload)
            if r.status_code == 200:
                return r.json()
            else:
                logging.info('No API Results for year: {}'.format(year))
                year = year - 1
        else:
            return
    except requests.exceptions.RequestException as e:
        logging.error('General Exception: {}'.format(e))
    except IOError as err:
        logging.error('IOError: {}'.format(err))

#sort items by population (exluding PR and DC)
def population_rank_sort(pop_list):
    non_states = []
    for i, val in enumerate(pop_list):
        if val[2] in ['11', '72']:
            non_states.append(pop_list.pop(i))
    pop_list = sorted(pop_list, key=lambda x: int(x[1]), reverse=True)
    for i,val in enumerate(pop_list):
        val.append(i+1)
    pop_list.extend(non_states)
    return pop_list

def update_page_value(val, new_val):
    print('val: {}, new val: {}'.format(val, new_val))
    #page.text = text.replace(val, new_val)
    #page.save(u'Updating Population estimate with latest value from Census Bureau')

if __name__ == '__main__':
    get_var = 'GEONAME,POP'
    for_var = 'state:*'
    api_url = 'http://api.census.gov/data/XXXX/pep/population'
    api_key = os.environ['CENSUS']
    pop_total = ['population_total', '2010Pop', '2000Pop', 'population_estimate']
    pop_rank = 'PopRank'
    
    site = pywikibot.Site('en', 'wikipedia') 
    repo = site.data_repository()
    
    metric_values = get_census_values(api_url, get_var, for_var, api_key)
    #metric_values.append(['User:Sasan-CDS/sandbox', '2302030'])
    #metric_values = [['User:Sasan-CDS/sandbox', '2302030']]
    #get list of pages from template, for each item in 
    if metric_values:
        #remove header
        metric_values.pop(0)
        metric_values = population_rank_sort(metric_values)
        print('Number of items in API Response: {}'.format(len(metric_values)))
        for i, val in enumerate(metric_values):
            metric_val = int(val[1])
            key = val[0].split(',')[0]
            print('State: {}'.format(key))
            if key in ['Kansas', 'North Carolina', 'Georgia']:
                key = key + ', United States'
            elif key == 'Washington':
                key = 'Washington (state)'
            page = pywikibot.Page(site, key)
            if page.exists():
                #if page.isRedirectPage():
                #    page = page.getRedirectTarget()
                text = page.get(get_redirect=True)
                code = mwparserfromhell.parse(text)
                template_val = None
                for template in code.filter_templates():
                    if template_val:
                        break
                    else:
                        for param in pop_total:
                            if template.has(param):
                                template_val = str(template.get(param).value)
                                print('CONTENTS: {}'.format(val))
                                print(template_val.replace('\n',''))
                                if template.has(pop_rank):
                                    print('OLD RANK: {}, NEW RANK: {}'.format(template.get(pop_rank).value,val[3]))
                                else:
                                    print('NO POP RANK FOUND FOR THIS PAGE!!!!')
                                break
                if template_val:        
                    if key == 'User:Sasan-CDS/sandbox':
                        update_page_value(template_val, '333333333 (2017 est)')
                    else:
                        update_page_value(template_val, metric_val)
                else:
                    print('No value found for this page!!!')
            else:
                print('NO RESULTS FOR: {}'.format(key))
    else:
        sys.exit('NO RESULTS FROM THE CENSUS API FOR ANY YEARS.  EXAMINE FOR OTHER ISSUES!')
