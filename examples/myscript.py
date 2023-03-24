# What this does
# 1.) Program logins
# 2.) Program adds text "Foobar" to "Ohje:Hiekkalaatikko" (sandbox page)
# 3.) after confirm it will save it back to Finnish Wikipedia
# 
# Execute:
# - python myscript.py

import pywikibot

site = pywikibot.Site("fi", "wikipedia")
site.login()

page = pywikibot.Page(site, 'Ohje:Hiekkalaatikko')
oldtext=page.text
newtext= page.text + "Foobar"

# Confirm
print("")
pywikibot.showDiff(oldtext, newtext)
pywikibot.info('Edit summary: {}'.format('summary'))

question='Do you want to accept these changes?'
choice = pywikibot.input_choice(
            question,
            [('Yes', 'y'), ('No', 'N')],
            default='N',
            automatic_quit=False
         )

# Save
if choice == 'y':
   page.text = newtext 
   page.save('Testing')
