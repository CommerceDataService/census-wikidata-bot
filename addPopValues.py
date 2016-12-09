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

def check_claim(item, claim, prop, val):
    try:
        claim_matches, remove_claim, add_claim = False, False, False
        if qualifiers[0][0] in claim.qualifiers:
            if claim.qualifiers[qualifiers[0][0]][0].getTarget().year == qualifiers[0][1][1]:
                if claim.getTarget().amount == val:
                    print('val matches')
                    if qualifiers[1][0] in claim.qualifiers:
                        if claim.qualifiers[qualifiers[1][0]][0].getTarget().id == qualifiers[1][1][1]:
                            print('det_method item matches')
                            claim_matches = True
                        else:
                            print('det method value does not match')
                            remove_claim = True
                            add_claim = True
                    else:
                        print('no det method qualifier')
                        remove_claim = True
                        add_claim = True
                else:
                    print('pop value does not match')
                    remove_claim = True
                    add_claim = True
        else:
            print('no point in time qualifier, delete claim!!!!')
            remove_claim = True
        claim_status = (claim_matches, remove_claim, add_claim)
        print(claim_status)
        return claim_status
    except:
        raise

def check_source_set(claim, source_claims):
    print(source_claims)
    for source in source_claims:
        print(source)
        for k, v in source.items():
            if k in references:
                prop_type = references[k][0]
                source_val = None
                if prop_type == 'id':
                    source_val = v[0].getTarget().id
                    print('id')
                elif prop_type == 'url':
                    source_val = v[0].getTarget()
                    print('url')
                if source_val == references[k][1]:
                    print('val matches')
                else:
                    print('val does not match')
                    return None
            else:
                print('not in references, break')
                return None
    return source

def create_source_claim(claim):
    try:
        for k, v in references.items():
            print(k)
            source_claim = pywikibot.Claim(repo, k, isReference=True)
            if v[0] == 'id':
                trgt_item = v[1]
                trgt_itempage = pywikibot.ItemPage(repo, trgt_item)
                source_claim.setTarget(trgt_itempage)
                claim.addSources([source_claim])
            elif v[0] == 'url':
                trgt_item = v[1]
                source_claim.setTarget(trgt_item)
                claim.addSources([source_claim])
        return True
    except:
        return False

def remove_claim(item, claim, prop):
    try:
        item.removeClaims(claim)
        return True
    except:
        return False

def create_claim(item, prop, prop_val):
    claim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(prop_val)
    claim.setTarget(wb_quant)
    #need to change to True once flag is received
    item.addClaim(claim, bot = False, summary = claim_add_summary)
    return claim

def create_qualifier_claim(claim):
    for q in qualifiers:
        qualifier = pywikibot.Claim(repo, q[0])
        if q[1][0] == 'time':
            trgt_item = pywikibot.WbTime(q[1][1])
            qualifier.setTarget(trgt_item)
            newclaim.addQualifier(qualifier)
            print('added qualifier ' + q[1][0])
        elif q[1][0] == 'item':
            trgt_item = q[1][1]
            trgt_itempage = pywikibot.ItemPage(repo, trgt_item)
            qualifier.setTarget(trgt_itempage)
            newclaim.addQualifier(qualifier)
            print('added qualifier ' + q[1][0])
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
    if mode == 'test':
        p_population = 'P63'
        #qualifiers - point in time, determination method
        qualifiers = [('P66',['time', 2015]), ('P144', ['item', 'Q32616'])]
        #references - ref url, stated in
        references = {'P149': ['id', 'Q32615'], 'P93': ['url', ref_url]}
    elif mode == 'wikidata':
        p_population = 'P1082'
        #qualifiers - point in time, determination method
        qualifiers = [('P585',['time', 2015]), ('P459', ['item', 'Q637413'])]
        #references - ref url, stated in
        references = {'P248': 'Q463769', 'P854': ref_url}

    pop_values = get_census_values()

    for val in pop_values[1:]:
        key = val[1].split(',')[0]+', United States'
        print('State: ' + key)
        pop_val = int(val[0])
        print('Pop Val: ' + str(pop_val))
        search_results = find_wiki_items(site, key)
        #if only single search result
        num_of_results = len(search_results['search'])
        if num_of_results == 1:
            item = pywikibot.ItemPage(repo, search_results['search'][0]['id'])
            item_dict = item.get()
            claim_present = False
            add_claim = False
            if len(item.claims) > 0:
                print('add_claim is False')
                if p_population in item.claims:
                    claims = item_dict['claims'][p_population]
                    if len(claims) > 0:
                        for claim in claims:
                            claim_status = check_claim(item, claim, p_population, pop_val)
                            if claim_status[0]:
                                print('claim matches, check sources')
                                source_claims = claim.getSources()
                                if len(source_claims) == 0:
                                    print('no references, add sources')
                                    source_claim = create_source_claim(claim)
                                    if source_claim:
                                        claim_present = True
                                else:
                                    source = check_source_set(claim, source_claims)
                                    if source:
                                        print('entire claim is okay, continue')
                                        claim_present = True
                                    else:
                                        print('remove claim and add proper version')
                                        remove_claim(item, claim, p_population)
                                        add_claim = True
                            elif claim_status[1]:
                                if claim_status[2]:
                                    print('remove claim and add proper version')
                                    remove_claim(item, claim, p_population)
                                    add_claim = True
                                else:
                                    print('remove claim')
                                    remove_claim(item, claim, p_population)
                    else:
                        print('no claims for statement')
                        add_claim = True
                else:
                    print('no pop statement, add statement and claim')
                    add_claim = True
            else:
                print('no statements. add population statement and claim')
                add_claim = True
                print('add_claim is True')
            print('add_claim,claim_present: {},{}'.format(add_claim, claim_present))
            if add_claim or not claim_present:
                print('add claim')
                newclaim = create_claim(item, p_population, pop_val)
                print('add qualifier')
                create_qualifier_claim(newclaim)
                print('add source')
                create_source_claim(newclaim)
            else:
                print('no claim has been added')
        elif num_of_results == 0:
            print('cannot find item')
        elif num_of_results > 1:
            print('too many results for item')
