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

def exists(page):
    """
    Determine if an entity exists in the data repository.

    @rtype: bool
    """
    if not hasattr(page, '_content'):
        try:
            page.get()
            return True
        except pywikibot.NoPage:
            print('NOPAGE')
            return False
        except pywikibot.IsRedirectPage:
            print('REDIRECT')
            return True
    return 'lastrevid' in page._content

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

        site = pywikibot.Site('en', 'wikipedia')  # any site will work, this is just an example
        repo = site.data_repository()
        print('site: {}, key: {}'.format(site, key)) 
        #search_results = find_wiki_items(site, key)
        #num_of_results = len(search_results['search'])
        #item_id = search_results['search'][0]['id']
        page = pywikibot.Page(site, key)
        if page.exists():
            if pywikibot.ItemPage.fromPage(page):
                print('true')
            else:
                print('FALSE')
            item = pywikibot.ItemPage.fromPage(page)  # this can be used for any page object

            # you can also define an item like this
            #repo = site.data_repository()  # this is a DataSite object
            #item = pywikibot.ItemPage(repo, 'Q42')  # This will be functionally the same as the other item we defined
            item.get()  # you need to call it to access any data.
            sitelinks = item.sitelinks
            aliases = item.aliases
            text = page.get()
            code = mwparserfromhell.parse(text)
            for template in code.filter_templates():
                if template.name.matches('Infobox U.S. state'):
                    if template.has('2010Pop'):
                        print('population available')
                        print(template.get('2010Pop').value)
                    #print(template.get('2010Pop').value)
            
            
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
