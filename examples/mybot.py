# What this does
# 1.) Program uses pywikibot command line argument handling  
# 2.) In treat_page() it adds text "This is a test text" to selected page
# 3.) after confirm it will save it back to selected wiki
# 
# Execute:
# - python mybot.py -site:wikipedia:fi -page:Ohje:Hiekkalaatikko -text:"A text added to the sandbox"


import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import ExistingPageBot

class MyBot(ExistingPageBot):
    update_options = {
        'text': 'This is a test text',
        'summary': 'Bot: a bot test edit with Pywikibot.',
    }

    def treat_page(self):
        """Load the given page, do some changes, and save it."""
        text = self.current_page.text
        text += '\n' + self.opt.text
        self.put_current(text, summary=self.opt.summary)

def main():
    """Parse command line arguments and invoke bot."""
    options = {}
    gen_factory = pagegenerators.GeneratorFactory()

    # Option parsing
    local_args = pywikibot.handle_args()  # global options
    local_args = gen_factory.handle_args(local_args)  # generators options

    for arg in local_args:
        opt, sep, value = arg.partition(':')
        if opt in ('-summary', '-text'):
            options[opt[1:]] = value

    MyBot(generator=gen_factory.getCombinedGenerator(), **options).run()

if __name__ == '__main__':
    main()
