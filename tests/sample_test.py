#set up a function to create content in your sandbox.  Then create a test for the changes that are necessary
import unittest, pywikibot, os

def create_content():
    # set up page for test
    os.environ["PYWIKIBOT2_DIR"] = '../'
    wiki_file = open('fixtures/test_data.txt', 'r')
    contents = wiki_file.read()
    site = pywikibot.Site('en', 'wikipedia')
    repo = site.data_repository()

    key = 'User:Sasan-CDS/sandbox'
    page = pywikibot.Page(site, key)
    page.text = contents
    page.save('setting up test')
    del os.environ["PYWIKIBOT2_DIR"]

class testPage(unittest.TestCase):
    
    def test_pop_rank(self):
        create_content()
        self.assertTrue(True)

if __name__ == '__main__':
        unittest.main()
