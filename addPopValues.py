#!/usr/bin/python3.5

#Author:        Sasan Bahadaran
#Date:          12/16/16
#Organization:  Commerce Data Service
#Description:   This is a bot script for getting Census data from the Census
#Bureau API's and writing it to Wikidata.

import pywikibot, json, os, requests
from pywikibot.data import api


def get_census_values():
    try:
        payload = {'get': 'POP,GEONAME','for': 'state:*'}
        url = api_url
        r = requests.get(api_url, params = payload)
        return r.json()
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)

def find_wiki_items(site, item_title):
    params = {'action': 'wbsearchentities',
              'format': 'json',
              'language': 'en',
              'type': 'item',
              'search': item_title}
    request = api.Request(site = site, **params)
    return request.submit()

def check_claim(claim, val):
    try:
        #0 - claim matches
        #1 - remove claim
        #2 - skip claim
        claim_status = 0
        p_in_time = qualifiers[0][0]
        det_method = qualifiers[1][0]
        print('Entry Value: {}'.format(claim.getTarget().amount))
        if p_in_time in claim.qualifiers:
            print('Entry Year: {}'.format(claim.qualifiers[p_in_time][0].getTarget().year))
            if claim.qualifiers[p_in_time][0].getTarget().year == qualifiers[0][1][1]:
                if claim.getTarget().amount == val:
                    if det_method in claim.qualifiers:
                        if claim.qualifiers[det_method][0].getTarget().id != qualifiers[1][1][1]:
                            print('Qualifier {} value incorrect'.format(qualifiers[1][0]))
                            claim_status = 1
                    else:
                        print('Qualifier determination method missing')
                        claim_status = 1
                else:
                    print('Statement claim value incorrect')
                    claim_status = 1
            else:
                print('value should be skipped')
                claim_status = 2
        else:
            print('Qualifier point in time missing')
            claim_status = 1
        print('Status of Claim: {}'.format(claim_status))
        return claim_status
    except:
        raise

def check_references(claim):
    source_claims = claim.getSources()
    if len(source_claims) != 1:
        print('Incorrect number of references')
        return False
    else:
        if len(source_claims[0]) != 2:
            print('Incorrect number of items in reference')
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
                        print('Value incorrect for key: {}'.format(k))
                        return False
                else:
                    print('Wrong item contained in reference')
                    return False
    return True

def remove_claim(claim, prop):
    try:
        item.removeClaims(claim)
        print('Claim removed')
        return True
    except:
        return False

def create_claim(prop, prop_val):
    newclaim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(prop_val)
    newclaim.setTarget(wb_quant)
    #need to change to True once flag is received
    item.addClaim(newclaim, bot = False, summary = claim_add_summary)
    print('New claim created')
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
        print('Qualifier: {} added'.format(q[0]))
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
        print('References added')
        return True
    except:
        return False

def add_full_claim():
    try:
        newclaim = create_claim(p_population, pop_val)
        create_qualifiers(newclaim)
        create_references(newclaim)
        print('Full claim added')
    except:
        raise

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    mode = 'test'
    #mode = 'wikidata'
    site = pywikibot.Site(mode, 'wikidata')
    repo = site.data_repository()
    api_url = 'http://api.census.gov/data/2015/pep/population'
    ref_url = 'http://www.census.gov/data/developers/data-sets/popest-popproj/popest.html'
    claim_add_summary = 'Adding 2015 state population claim'
    #qualifiers - point in time, determination method
    #references - ref url, stated in
    if mode == 'test':
        p_population = 'P63'
        qualifiers = [('P66',['time', 2015]), ('P144', ['item', 'Q32616'])]
        references = {'P149': ['id', 'Q32615'], 'P93': ['url', ref_url]}
    elif mode == 'wikidata':
        p_population = 'P1082'
        qualifiers = [('P585',['time', 2015]), ('P459', ['item', 'Q637413'])]
        references = {'P248': ['id','Q463769'], 'P854': ['url', ref_url]}

    pop_values = get_census_values()
    for val in pop_values[1:]:
        key = val[1].split(',')[0]+', United States'
        pop_val = int(val[0])
        print('State: {} - {}'.format(key, pop_val))
        search_results = find_wiki_items(site, key)
        #if only single search result
        num_of_results = len(search_results['search'])
        if num_of_results == 1:
            item = pywikibot.ItemPage(repo, search_results['search'][0]['id'])
            item_dict = item.get()
            claim_present = False
            if p_population in item.claims:
                claims = item_dict['claims'][p_population]
                if len(claims) > 0:
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
                try:
                    add_full_claim()
                except:
                    raise
        elif num_of_results == 0:
            print('0 wiki items found')
            #create method for adding new page for item
        elif num_of_results > 1:
            print('more than 1 wiki item found')
