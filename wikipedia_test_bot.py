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

    #metric_values = get_census_values(api_url, get_var, for_var, api_key)
    #metric_values.append(['User:CensusBot/sandbox', '2302030'])
    metric_values = [['sfda','0'],['Wikipedia:sandbox', '2302030']]
    print('Number of items in API Response: {}'.format(len(metric_values[1:])))
    for i, val in enumerate(metric_values[1:]):
        metric_val = int(val[1])
        key = val[0].split(',')[0]
        print('key: {}'.format(key))
        if key == 'Kansas':
            key = 'Kansas, United States'
        elif key == 'Washington':
            key = 'Washington (state)'
        elif key == 'North Carolina':
            key = 'North Carolina, United States'
        elif key == 'Georgia':
            key = 'Georgia, United States'
        site = pywikibot.Site('en', 'wikipedia') 
        repo = site.data_repository()
        print('site: {}, key: {}'.format(site, key)) 
        page = pywikibot.Page(site, key)
        if page.exists():
            if page.isRedirectPage():
                print('redirect true!!!!')
                page = page.getRedirectTarget()
            #item = pywikibot.ItemPage.fromPage(page)
            #item.get()  # you need to call it to access any data.
            # you can also define an item like this
            #repo = site.data_repository()  # this is a DataSite object
            #item = pywikibot.ItemPage(repo, 'Q42')
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
                        elif template.has('2000Pop'):
                            print('Infobox US state has 2000Pop value')
                            print(template.get('2000Pop').value)
                    elif template.has('2010Pop'):
                        print('Pop present but not in typical templates?')
                        print('new template 2010Pop value: {}'.format(template.get('2010Pop').value))
                        if key == 'User:CensusBot/sandbox':
                            print('ORIG VAL: {}'.format(template.get('2010Pop').value))
                            item = pywikibot.ItemPage.fromPage(page)
                            text = text.replace('2,911,641 (2015 est)', '3333333 (2017 est)')
                            item.editEntity(text, summary='test edit')
                            print('afer item')
                    elif template.has('population_estimate'):
                        print('population_estimate present but not in typical template')
                        print(template.get('population_estimate').value)
                    elif template.has('2000Pop'):
                        print('2000Pop present')
                        print(template.get('2000Pop').value)
                if key == 'User:CensusBot/sandbox':
                    print('in sandbox key')
            

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
