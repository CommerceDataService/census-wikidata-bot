#!/usr/bin/python3.5

import pywikibot, json, os, requests, argparse, logging, time
from pywikibot.data import api


def get_census_values():
    try:
        payload = {'get': 'POP,GEONAME','for': 'state:*'}
        url = api_url
        r = requests.get(api_url, params = payload)
        return r.json()
    except requests.exceptions.RequestException as e:
        logging.error(e)
        sys.exit(1)

def find_wiki_items(site, item_title):
    params = {'action': 'wbsearchentities',
              'format': 'json',
              'language': 'en',
              'type': 'item',
              'search': item_title}
    request = api.Request(site = site, **params)
    return request.submit()

def get_claims(item):
    try:
        item_dict = item.get()
        if p_population in item.claims:
            claims = item_dict['claims'][p_population]
            if len(claims) > 0:
                return claims
            else:
                return None
        else:
            return None
    except:
        raise

def check_claim(claim, val):
    try:
        #0 - claim matches
        #1 - remove claim
        #2 - skip claim
        claim_status = 0
        p_in_time = qualifiers[0][0]
        det_method = qualifiers[1][0]
        logging.info('Entry Value: {}'.format(claim.getTarget().amount))
        if p_in_time in claim.qualifiers:
            logging.info('Entry Year: {}'.format(claim.qualifiers[p_in_time][0].getTarget().year))
            if claim.qualifiers[p_in_time][0].getTarget().year == qualifiers[0][1][1]:
                logging.info('claim val: {}, val: {}'.format(claim.getTarget().amount, val))
                if claim.getTarget().amount == val:
                    if det_method in claim.qualifiers:
                        if claim.qualifiers[det_method][0].getTarget().id != qualifiers[1][1][1]:
                            logging.info('Qualifier {} value incorrect'.format(qualifiers[1][0]))
                            claim_status = 1
                    else:
                        logging.info('Qualifier determination method missing')
                        claim_status = 1
                else:
                    logging.info('Statement claim value incorrect')
                    claim_status = 1
            else:
                logging.info('value should be skipped')
                claim_status = 2
        else:
            logging.info('Qualifier point in time missing')
            claim_status = 1
        logging.info('Status of Claim: {}'.format(claim_status))
        return claim_status
    except:
        raise

def check_references(claim):
    source_claims = claim.getSources()
    if len(source_claims) != 1:
        logging.info('Incorrect number of references')
        return False
    else:
        if len(source_claims[0]) != 2:
            logging.info('Incorrect number of items in reference')
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
                        logging.info('Value incorrect for key: {}'.format(k))
                        return False
                else:
                    logging.info('Wrong item contained in reference')
                    return False
    return True

def remove_claim(claim, prop):
    try:
        item.removeClaims(claim)
        logging.info('Claim removed')
        return True
    except:
        return False

def create_claim(prop, prop_val):
    newclaim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(prop_val)
    newclaim.setTarget(wb_quant)
    #need to change to True once flag is received
    item.addClaim(newclaim, bot = False, summary = claim_add_summary)
    logging.info('New claim created')

    return newclaim

def create_qualifiers(claim):
    for q in qualifiers:
        qualifier = pywikibot.Claim(repo, q[0])
        if q[1][0] == 'time':
            trgt_item = pywikibot.WbTime(q[1][1])
        elif q[1][0] == 'item':
            trgt_item = pywikibot.ItemPage(repo, q[1][1])
        qualifier.setTarget(trgt_item)
        claim.addQualifier(qualifier)
        logging.info('Qualifier: {} added'.format(q[0]))
    return True

def create_references(claim):
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
        logging.info('References added')
        return True
    except:
        return False

def add_full_claim():
    try:
        newclaim = create_claim(p_population, pop_val)
        create_qualifiers(newclaim)
        create_references(newclaim)
        logging.info('Full claim added')
    except:
        raise

def loadConfig(data_file):
    try:

    except:
        raise

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    api_url = 'http://api.census.gov/data/2015/pep/population'
    ref_url = 'http://www.census.gov/data/developers/data-sets/popest-popproj/popest.html'
    claim_add_summary = 'Adding 2015 state population claim'
    #logging configuration
    logging.basicConfig(
                        filename='logs/censusbot-log-'+time.strftime('%Y%m%d'),
                        level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s -%(message)s',
                        datefmt='%Y%m%d %H:%M:%S'
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
                        '-t',
                        '--testmode',
                        required=False,
                        help='Pass this flag to use the test Wikidata instance',
                        action="store_true",
                        default = False
    )
    args = parser.parse_args()
    logging.info("--SCRIPT ARGUMENTS--------------")
    logging.info('-- Test Mode flag set to: {}'.format(args.testmode))
    logging.info("-- [JOB START]  ----------------")

    #qualifiers - point in time, determination method
    #references - ref url, stated in
    #if mode == 'test':
    # if args.testmode:
    #     site = pywikibot.Site('test', 'wikidata')
    #     p_population = 'P63'
    #     qualifiers = [('P66',['time', 2015]), ('P144', ['item', 'Q32616'])]
    #     references = {'P149': ['id', 'Q32615'], 'P93': ['url', ref_url]}
    #     pop_claim = {'P63': {'qualfiers': [('P66',['time', 2015]), ('P144', ['item', 'Q32616'])],
    #                          'references': {'P149': ['id', 'Q32615'], 'P93': ['url', ref_url]}
    #                         }
    #                 }
    # else:
    #     site = pywikibot.Site('wikidata', 'wikidata')
    #     p_population = 'P1082'
    #     qualifiers = [('P585',['time', 2015]), ('P459', ['item', 'Q637413'])]
    #     references = {'P248': ['id','Q463769'], 'P854': ['url', ref_url]}
    #     pop_claim = {'P1082': {'qualifiers': [('P585',['time', 2015]), ('P459', ['item', 'Q637413'])],
    #                            'references': {'P248': ['id','Q463769'], 'P854': ['url', ref_url]}
    #                           }
    #                 }
    if args.testmode:
        site = pywikibot.Site('test', 'wikidata')
        data_file = os.path.join(scriptpath, "fixtures", "data_test.json")
        loadConfig(data_file)
    else:
        site = pywikibot.Site('wikidata', 'wikidata')
        data_file = os.path.join(scriptpath, "fixtures", "data.json")

    repo = site.data_repository()
    pop_values = get_census_values()
    for val in pop_values[1:]:
        key = val[1].split(',')[0]+', United States'
        pop_val = int(val[0])
        logging.info('State: {} - {}'.format(key, pop_val))
        search_results = find_wiki_items(site, key)
        #if only single search result
        num_of_results = len(search_results['search'])
        if num_of_results == 1:
            item = pywikibot.ItemPage(repo, search_results['search'][0]['id'])
            claims = get_claims(item)
            claim_present = False
            if claims:
                for claim in claims:
                    claim_status = check_claim(claim, pop_val)
                    if claim_status == 0:
                        source = check_references(claim)
                        if not source:
                            remove_claim(claim, p_population)
                        else:
                            claim_present = True
                    elif claim_status == 1:
                        remove_claim(claim, p_population)
            if not claim_present:
                add_full_claim()
        elif num_of_results == 0:
            logging.info('0 wiki items found')
            #create method for adding new page for item
        elif num_of_results > 1:
            logging.info('more than 1 wiki item found')
