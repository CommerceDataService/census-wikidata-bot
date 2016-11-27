#!/usr/bin/python3.5

import pywikibot, json, pprint, os
from pywikibot.data import api


def get_items(site, item_title):
    """
    Requires a site and search term (item_title) and returns the results.
    """
    params = {'action': 'wbsearchentities',
              'format': 'json',
              'language': 'en',
              'type': 'item',
              'search': item_title}
    request = api.Request(site=site, **params)
    return request.submit()

def get_census_values(fname):
    with open(fname) as data_file:
        data = json.load(data_file)
        return data

def replace_claim_value(claim, newval, reference):
    wb_quant = pywikibot.WbQuantity(newval)
    claim.changeTarget(wb_quant)

    #add reference
    ref_url = pywikibot.Link(reference, source=reference, defaultNamespace=claim.namespace)
    claim.addSource(ref_url)

def set_new_claim_value(repo, prop, qualifier, reference):
    newclaim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(newval)
    newclaim.setTarget(wb_quant)
    item.addClaim(newclaim, bot=False)

    #set qualifier value
    qualifier = pywikibot.Claim(repo, qualifier)
    wb_time = pywikibot.WbTime(year)
    qualifier.setTarget(wb_time)
    newclaim.addQualifier(qualifier)

    #add reference
    ref_url = pywikibot.Link(reference)
    newclaim.addSource(ref_url)

def add_new_claim(repo, item, prop, val, qualifier, reference):
    claim = pywikibot.Claim(repo, prop)
    wb_quant = pywikibot.WbQuantity(val)
    claim.setTarget(wb_quant)
    item.addClaim(claim)

    #set qualifier value
    qualifier = pywikibot.Claim(repo, qualifier)
    wb_time = pywikibot.WbTime(year)
    qualifier.setTarget(wb_time)
    claim.addQualifier(qualifier)

    #add reference
    ref_url = reference
    ref_url = pywikibot.Link(reference)
    claim.addSource(ref_url)

if __name__ == '__main__':
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    prop = 'P1082' #population
    qualifier = 'P585' #point in time
    year = 2015
    reference = 'http://api.census.gov/data/2015/pep/population?get=POP,GEONAME&for=state:*'
    site = pywikibot.Site('wikidata', 'wikidata')
    repo = site.data_repository()

    # if mode == 'wikidata':
    #     key = 'Alaska, United States'
    #     prop = 'P1082' #population
    #     qualifier = 'P585' #point in time
    #     year = 2015
    #     newval = 7384321
    #     reference = 'http://api.census.gov/data/2015/pep/population?get=POP,GEONAME&for=state:*'
    # else:
    #     #test values
    #     key = 'Arizona, United States'
    #     prop = 'P63'
    #     qualifier = 'P66'
    #     year = '2015'

    fname = os.path.join(scriptpath, 'fixtures', '2015_state_population.json')
    pop_values = get_census_values(fname)
    for val in pop_values[1:]:
        key = val[1].split(',')[0]+', United States'
        print('State: ' +key)
        newval = val[0]
        search_results = get_items(site, key)
        #if only single search result
        if len(search_results['search']) == 1:
            item = pywikibot.ItemPage(repo, search_results['search'][0]['id'])
            item.get()
            if item.claims:
                if prop in item.claims:
                    for claim in item.claims[prop]:
                        if claim.qualifiers[qualifier]:
                            print(claim.qualifiers[qualifier][0].getTarget().year)
                            if claim.qualifiers[qualifier][0].getTarget().year == year:
                                if claim.getTarget().amount != newval:
                                    print('replace value')
                                    #replace_claim_value(claim, newval, reference)
                                    break
                                else:
                                    print('value already correct')
                                    break
                        else:
                            print('no point in time qualifier')
                    else:
                        print('add new 2015 value')
                        #set_new_claim_value(repo, prop, qualifier, reference)
                else:
                    print('no population claim. add new claim')
                    #add_new_claim(repo, item, prop, newval, qualifier, reference)
