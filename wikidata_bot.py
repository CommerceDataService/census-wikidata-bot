#!/usr/bin/python3.5

#Author:        Sasan Bahadaran
#Date:          12/16/16
#Organization:  Commerce Data Service
#Description:   This is a bot script for getting Census data from the Census
#Bureau API's and writing it to Wikidata.

import pywikibot, json, os, requests, argparse, logging, time, json, sys
from pywikibot.data import api
from util import config_funcs

def get_census_values(api_url, get_var, for_var, api_key):
    try:
        payload = {'get': get_var, 'for': for_var, 'key': api_key}
        r = requests.get(api_url, params=payload)
        return r.json()
    except requests.exceptions.RequestException as e:
        logging.error('General Exception: {}'.format(e))
        sys.exit(1)
    except IOError as err:
        logging.error('IOError: {}'.format(err))

def find_wiki_items(sparql, item_key):
    try:
        sparql_url = 'https://query.wikidata.org/sparql'
        payload = {'query': sparql.replace('XXX', '\"'+item_key+'\"', 1),\
            'format': 'JSON'}
        r = requests.get(sparql_url, params = payload)
        return r.json()
    except requests.exceptions.RequestException as e:
        logging.error(e)
        sys.exit(1)

#SPARQL Queries do not work on test site
def find_test_wiki_items(site, item_title):
    params = {'action': 'wbsearchentities',
              'format': 'json',
              'language': 'en',
              'type': 'item',
              'search': item_title}
    request = api.Request(site = site, **params)
    return request.submit()

def get_claims(item):
    try:
        item_dict = item.get(force=True)
        if statement in item.claims:
            claims = item_dict['claims'][statement]
            if len(claims) > 0:
                return claims
            else:
                return None
        else:
            return None
    except:
        raise

def check_claim(claim, val, qualifiers, year):
    try:
        #0 - claim matches
        #1 - remove claim
        #2 - skip claim
        claim_status = 0
        p_in_time = qualifiers[0][0]
        det_method = qualifiers[1][0]

        amt = claim.getTarget().amount
        if p_in_time in claim.qualifiers:
            clm_yr = claim.qualifiers[p_in_time][0].getTarget().year
            if clm_yr == int(year):
                if amt == val:
                    if det_method in claim.qualifiers:
                        if claim.qualifiers[det_method][0].getTarget().id != qualifiers[1][1][1]:
                            logging.info('Status [1] - Qualifier [{}] value incorrect'.format(qualifiers[1][0]))
                            claim_status = 1
                    else:
                        logging.info('Status [1] - Qualifier [{}] missing'.format(qualifiers[1][0]))
                        claim_status = 1
                else:
                    logging.info('Year: {}, Value: {:,}'.format(clm_yr, amt))
                    logging.info('Status [1] - Value incorrect')
                    claim_status = 1
            else:
                logging.info('Status [2] - Skipping Claim')
                claim_status = 2
        else:
            logging.info('Status [1] - Qualifier [point in time] missing')
            claim_status = 1
        return claim_status
    except:
        raise

def check_references(claim, references):
    source_claims = claim.getSources()
    if len(source_claims) != 1:
        logging.info('Claim contains incorrect number of references')
        return False
    else:
        if len(source_claims[0]) != len(references):
            logging.info('Claim contains incorrect number of items in reference')
            return False
        else:
            for k, v in source_claims[0].items():
                if k in references:
                    prop_type = references[k][0]
                    source_val = None
                    if prop_type == 'id':
                        source_val = v[0].getTarget().id
                    elif prop_type == 'url':
                        source_val = v[0].getTarget()
                    if source_val != references[k][1]:
                        logging.info('Reference value [{}] incorrect for key: {}'.format(v[0].getTarget(), k))
                        return False
                else:
                    logging.info('Reference contained incorrect property')
                    return False
    return True

def remove_claim(item, claim, prop):
    try:
        item.removeClaims(claim)
        logging.info('Claim removed')
        return True
    except:
        return False

def create_claim(item, prop, prop_val, summary):
    newclaim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(prop_val)
    newclaim.setTarget(wb_quant)
    item.addClaim(newclaim, bot=True, summary=summary)
    logging.info('New claim created')
    return newclaim

def create_qualifiers(claim, qualifiers, year):
    for q in qualifiers:
        qualifier = pywikibot.Claim(repo, q[0])
        if q[1][0] == 'time':
            trgt_item = pywikibot.WbTime(int(year))
        elif q[1][0] == 'item':
            trgt_item = pywikibot.ItemPage(repo, q[1][1])
        qualifier.setTarget(trgt_item)
        claim.addQualifier(qualifier)
        logging.info('Qualifier: {} added to claim'.format(q[0]))
    return True

def create_references(claim, references):
    try:
        source_claim_list = []
        for k, v in references.items():
            source_claim = pywikibot.Claim(repo, k, isReference=True)
            trgt_item = None
            if v[0] == 'id':
                trgt_item = pywikibot.ItemPage(repo, v[1])
            elif v[0] == 'url':
                trgt_item = v[1]
            source_claim.setTarget(trgt_item)
            source_claim_list.append(source_claim)
        claim.addSources(source_claim_list)
        logging.info('{} References added to claim'.format(len(source_claim_list)))
        return True
    except:
        return False

def add_full_claim(item, statement, metric_val, qualifiers, references, summary, year):
    try:
        newclaim = create_claim(item, statement, metric_val, summary)
        create_qualifiers(newclaim, qualifiers, year)
        create_references(newclaim, references)
        logging.info('Full claim successfully added')
    except:
        raise

def load_config(data_file):
    try:
        with open(data_file) as df:
            jsondata = json.load(df)
            return jsondata
    except:
        raise
    
# construct page search key from config file params
#def get_key_vals(wiki_lookup_key, val):
#    val_key = ''
#    for item in wiki_lookup_key['api_cols']:
#        val_key += val[item]
#    key = wiki_lookup_key['beg_val']+val_key+wiki_lookup_key['end_val']
#    logging.info('Search Key: {}'.format(key))
#    return key

def insertYearValue(value, year):
    return value.replace('XXXX', year)

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    data = []

    #logging configuration
    logging.basicConfig(
                        filename='logs/wikidata_bot-log-'+time.strftime('%Y%m%d'),
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
    args = parser.parse_args()
    logging.info("-------- [SCRIPT ARGUMENTS] --------")
    if args.mode == 't':
        logging.info('      BOT MODE: TEST')
    elif args.mode == 'p':
        logging.info('      BOT MODE: PROD')
    if args.debug:
        logging.info('      !RUNNING IN DEBUG MODE!')
    logging.info("----------- [JOB START] -----------")

    if args.mode == 't':
        site = pywikibot.Site('test', 'wikidata')
        data_file = os.path.join(scriptpath, "data", "data_test.json")
    else:
        site = pywikibot.Site('wikidata', 'wikidata')
        data_file = os.path.join(scriptpath, "data", "data.json")
    api_key = config_funcs.getAppConfigParam('API', 'key')
    data = load_config(data_file)
    repo = site.data_repository()
    if data:
        for i, api_item in enumerate(data):
            if api_item['enabled']:
                    logging.info('***************NEW API ITEM***************')
                    api_url = api_item['api_url']
                    logging.info('[api_url]: {}'.format(api_url))
                    get_var = api_item['get']
                    logging.info('[get_var]: {}'.format(get_var))
                    for_var = api_item['for']
                    logging.info('[for_var]: {}'.format(for_var))
                    response = api_item['response']
                    logging.info('[Expected response]: {}'.format(response))
                    summary = api_item['summary']
                    logging.info('[summary]: {}'.format(summary))
                    if args.mode == 'p':
                        sparql = api_item['sparql']
                        logging.info('[sparql]: {}'.format(sparql))
                    for year in api_item['year']:
                        logging.info('**********NEW SEARCH YEAR: {}**********'.format(year))
                        summary = insertYearValue(summary, year)
                        api_url = insertYearValue(api_url, year)
                        for item in api_item['items']:
                            logging.info('*****NEW ITEM*****')
                            wiki_lookup_key = item['wiki_lookup_key']
                            logging.info('[wiki_lookup_key]: {}'.format(wiki_lookup_key))
                            api_value_column = item['api_value_column']
                            logging.info('[api_value_column]: {}'.format(api_value_column))
                            statement = item['statement']
                            logging.info('[statement]: {}'.format(statement))
                            content = item['content']
                            references = item['content']['references']
                            logging.info('[references]: {}'.format(references))
                            qualifiers = item['content']['qualifiers']
                            logging.info('[qualifiers]: {}'.format(qualifiers))

                            #process each item
                            metric_values = get_census_values(api_url, get_var, for_var, api_key)
                            logging.info('Number of items in API Response: {}'.format(len(metric_values[1:])))
                            for i, val in enumerate(metric_values[1:]):
                                logging.info('[ITEM {}]: {}'.format(i, val))
                                metric_val = int(val[api_value_column])
                                if args.mode == 't':
                                    #this code is specific to state and county right now
                                    if for_var == 'state:*':
                                        key = val[0].split(',')[0]+', United States'
                                    elif for_var == 'county:*':
                                        vals = val[0].split(',')
                                        key = vals[0]+','+vals[1]
                                    logging.info('Searching for ID: {}'.format(key))
                                    search_results = find_test_wiki_items(site, key)
                                    num_of_results = len(search_results['search'])
                                elif args.mode == 'p':
                                    key = config_funcs.get_key_vals(wiki_lookup_key, val)
                                    logging.info('Search Key: {}'.format(key))
                                    search_results = find_wiki_items(sparql, key)
                                    num_of_results = len(search_results['results']['bindings'])
                                #if only single search result
                                if num_of_results == 1:
                                    if args.mode == 't':
                                        item_id = search_results['search'][0]['id']
                                    elif args.mode == 'p':
                                        item_url = search_results['results']['bindings'][0]['wd']['value']
                                        item_id = item_url.split('/')[-1]
                                    logging.info('1 Item found [ID] - {}'.format(item_id))
                                    item = pywikibot.ItemPage(repo, item_id)
                                    claims = get_claims(item)
                                    claim_present = False
                                    if claims:
                                        for i, claim in enumerate(claims):
                                            logging.info('CLAIM #{}'.format(i+1))
                                            claim_status = check_claim(claim, metric_val, qualifiers, year)
                                            if claim_status == 0:
                                                source = check_references(claim, references)
                                                if not source:
                                                    if args.debug:
                                                        logging.info('DEBUG - Claim will be removed')
                                                    else:
                                                        remove_claim(item, claim, statement)
                                                        #add code to add to watch list after alteration
                                                else:
                                                    claim_present = True
                                            elif claim_status == 1:
                                                if args.debug:
                                                    logging.info('DEBUG - Claim will be removed')
                                                else:
                                                    remove_claim(item, claim, statement)
                                                    #add code to add to watch list after alteration
                                    if not claim_present:
                                        if args.debug:
                                            logging.info('DEBUG - Add new claim')
                                        if not args.debug:
                                            add_full_claim(item, statement, metric_val, qualifiers, references, summary, year)
                                            #add code to add to watch list after alteration
                                elif num_of_results == 0:
                                    logging.info('0 ITEMS FOUND')
                                    #create method for adding new page for item
                                elif num_of_results > 1:
                                    logging.info('MORE THAN 1 ITEM FOUND')
            else:
                logging.info('[DATA CONFIGURATION FILE ITEM #{} NOT ENABLED]'.format(i))
    else:
        logging.error('Data file did not load any claims to iterate over')
