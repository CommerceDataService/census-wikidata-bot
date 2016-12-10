#!/usr/bin/python3.5

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
        claim_matches, remove_claim, add_claim = False, False, False
        p_in_time = qualifiers[0][0]
        det_method = qualifiers[1][0]
        if p_in_time in claim.qualifiers:
            if claim.qualifiers[p_in_time][0].getTarget().year == qualifiers[0][1][1]:
                if claim.getTarget().amount == val:
                    if det_method in claim.qualifiers:
                        if claim.qualifiers[det_method][0].getTarget().id == qualifiers[1][1][1]:
                            claim_matches = True
                        else:
                            print('Qualifier {} value incorrect'.format(qualifiers[1][0]))
                            remove_claim = True
                            add_claim = True
                    else:
                        print('Qualifier determination method missing')
                        remove_claim = True
                        add_claim = True
                else:
                    print('Statement claim value incorrect')
                    remove_claim = True
                    add_claim = True
        else:
            print('Qualifier point in time missing')
            remove_claim = True
        claim_status = (claim_matches, remove_claim, add_claim)
        print('claim_matches: {},remove_claim: {},add_claim: {}'\
        .format(claim_status[0], claim_status[1], claim_status[2]))
        return claim_status
    except:
        raise

def check_source_set(claim):
    source_claims = claim.getSources()
    print('length of source_claim: {}'.format(len(source_claims)))
    if len(source_claims) != 1:
        print('Not 1 item')
        return False
    else:
        print('source_claims: {}'.format(source_claims))
        print(len(source_claims[0]))
        if len(source_claims[0]) != 2:
            print('Not 2 items in reference')
            return False
        else:
            for k, v in source_claims[0].items():
                print('key: {}, val: {}'.format(k,v))
                if k in references:
                    prop_type = references[k][0]
                    source_val = None
                    if prop_type == 'id':
                        source_val = v[0].getTarget().id
                    elif prop_type == 'url':
                        source_val = v[0].getTarget()
                    print('source_val: {}'.format(source_val))
                    if source_val != references[k][1]:
                        print('False')
                        return False
                else:
                    print('False')
                    return False
    print('True')
    return True

def create_source_claim(claim):
    try:
        source_claim_list = []
        for k, v in references.items():
            print('Reference: {}'.format(k))
            source_claim = pywikibot.Claim(repo, k, isReference=True)
            trgt_item = None
            if v[0] == 'id':
                trgt_item = pywikibot.ItemPage(repo, v[1])
            elif v[0] == 'url':
                trgt_item = v[1]
            source_claim.setTarget(trgt_item)
            source_claim_list.append(source_claim)
        claim.addSources(source_claim_list)
        return True
    except:
        return False

def remove_claim(item, claim, prop):
    try:
        item.removeClaims(claim)
        print('Claim removed')
        return True
    except:
        return False

def create_claim(item, prop, prop_val):
    print('Adding new claim')
    claim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(prop_val)
    claim.setTarget(wb_quant)
    #need to change to True once flag is received
    item.addClaim(claim, bot = False, summary = claim_add_summary)
    print('New claim added')
    return claim

def create_qualifier_claim(claim):
    for q in qualifiers:
        qualifier = pywikibot.Claim(repo, q[0])
        if q[1][0] == 'time':
            trgt_item = pywikibot.WbTime(q[1][1])
        elif q[1][0] == 'item':
            trgt_item = pywikibot.ItemPage(repo, q[1][1])
        qualifier.setTarget(trgt_item)
        newclaim.addQualifier(qualifier)
        print('Qualifier: {}'.format(q[1][0]))
    return True

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    mode = 'test'
    site = pywikibot.Site(mode, 'wikidata')
    repo = site.data_repository()
    api_url = 'http://api.census.gov/data/2015/pep/population'
    ref_url = 'http://www.census.gov/data/developers/data-sets/popest-popproj/popest.html'
    claim_add_summary = 'Adding 2015 state population claim'

    #test values
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
        print('State: {}, Pop Val: {}'.format(key, pop_val))
        search_results = find_wiki_items(site, key)
        #if only single search result
        num_of_results = len(search_results['search'])
        if num_of_results == 1:
            item = pywikibot.ItemPage(repo, search_results['search'][0]['id'])
            item_dict = item.get()
            claim_present = False
            add_claim = False
            if p_population in item.claims:
                claims = item_dict['claims'][p_population]
                if len(claims) > 0:
                    for claim in claims:
                        claim_status = check_claim(claim, pop_val)
                        if claim_status[0]:
                            print('check sources')
                            source = check_source_set(claim)
                            if source:
                                claim_present = True
                            else:
                                remove_claim(item, claim, p_population)
                                add_claim = True
                        elif claim_status[1]:
                            if claim_status[2]:
                                remove_claim(item, claim, p_population)
                                add_claim = True
                            else:
                                remove_claim(item, claim, p_population)
                else:
                    add_claim = True
            else:
                add_claim = True
            if add_claim or not claim_present:
                newclaim = create_claim(item, p_population, pop_val)
                create_qualifier_claim(newclaim)
                create_source_claim(newclaim)
            else:
                print('no claim has been added')
        elif num_of_results == 0:
            print('0 wiki items found')
        elif num_of_results > 1:
            print('more than 1 wiki item found')
