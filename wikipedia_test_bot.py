import pywikibot, json, os, requests, argparse, logging, time, json, sys
from pywikibot.data import api
import mwparserfromhell

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

if __name__ == '__main__':
    get_var = 'GEONAME,POP'
    for_var = 'state:*'
    api_url = 'http://api.census.gov/data/2015/pep/population'
    api_key = os.environ['CENSUS']

    metric_values = get_census_values(api_url, get_var, for_var, api_key)
    print('Number of items in API Response: {}'.format(len(metric_values[1:])))
    for i, val in enumerate(metric_values[1:]):
        metric_val = int(val[1])
        key = val[0].split(',')[0]
        if key == 'Kansas':
            key = 'Kansas, United States'
        elif key == 'Washington':
            key = 'Washington (state)'
        elif key == 'North Carolina':
            key = 'North Carolina, United States'
        site = pywikibot.Site('en', 'wikipedia')  # any site will work, this is just an example
        repo = site.data_repository()
        print('site: {}, key: {}'.format(site, key)) 
        #search_results = find_wiki_items(site, key)
        #num_of_results = len(search_results['search'])
        #item_id = search_results['search'][0]['id']
        page = pywikibot.Page(site, key)
        if page.exists():
            if page.isRedirectPage():
                print('redirect true!!!!')
                page = page.getRedirectTarget()
            item = pywikibot.ItemPage.fromPage(page)  # this can be used for any page object
            #item.get()  # you need to call it to access any data.
            # you can also define an item like this
            #repo = site.data_repository()  # this is a DataSite object
            #item = pywikibot.ItemPage(repo, 'Q42')  # This will be functionally the same as the other item we defined
            #sitelinks = item.sitelinks
            #aliases = item.aliases
            text = page.get(get_redirect=True)
            code = mwparserfromhell.parse(text)
            for template in code.filter_templates():
                if key == 'District of Columbia':
                    if template.name.matches('Infobox settlement'):
                        print('settlement match')
                        if template.has('population_total'):
                            print('population total present')
                            print(template.get('population_total').value)
                else:        
                    if template.name.matches('Infobox U.S. state'):
                        if template.has('2010Pop'):
                            print(template.get('2010Pop').value)
                    elif template.has('2010Pop'):
                        print('Pop present but not in typical templates?')
                        print(template.get('2010Pop').value)
                    elif template.has('population_estimate'):
                        print('population_estimate present but not in typical template')
                        print(template.get('population_estimate').value)
                    elif template.has('2000Pop'):
                        print('2000Pop present')
                        print(template.get('2000Pop').value)
            #code for templates (first draft) 
            #templates = code.filter_templates()
            #for template in templates:
            #    if template.name == 'Infobox U.S. state':
            #        print('HEYYYY!')
            #infobox = templates[3]
            #print(infobox.get('2010Pop').value)
            

            # Edit an existing item
            #item.editLabels(labels={'en': 'Douglas Adams'}, summary=u'Edit label')
            #item.editDescriptions(descriptions={'en': 'English writer'}, summary=u'Edit description')
            #item.editAliases(aliases={'en':['An alias', 'Another alias']}, summary=u'Set aliases')
            #item.setSitelink(sitelink={'site': 'enwiki', 'title': 'Douglas Adams'}, summary=u'Set sitelink')
            #item.removeSitelink(site='enwiki', summary=u'Remove sitelink')
            
            # You can also made this all in one time:
            #data = {'labels': {'en': 'Douglas Adams'},
            #  'descriptions': {'en': 'English writer'},
            #  'sitelinks': [{'site': 'enwiki', 'title': 'Douglas Adams'}]}
            #item.editEntity(data, summary=u'Edit item')
        else:
            print('NO RESULTS FOR: {}'.format(key))
