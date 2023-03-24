# Finnish Wikipedia Pywikipedia scripts

This repository contains Finnish Wikipedia pywikipedia example codes, scripts and documentation.

Homepage
- https://fi.wikipedia.org/wiki/Wikipedia:Pywikibot

Pywikibot
- https://doc.wikimedia.org/pywikibot/stable/introduction.html

## Install

```
git clone https://github.com/Wikimedia-Suomi/pywikibot-fiwiki-scripts.git
```
OR if you want to commit

```
git clone git@github.com:Wikimedia-Suomi/pywikibot-fiwiki-scripts.git
```

Initialise enviroment.
```
cd pywikibot-fiwiki-scripts
python3 -m venv ./venv
source venv/bin/activate
pip install pywikibot
echo "usernames['wikipedia']['fi'] = 'ZacheBot'" > user-config.py
echo "put_throttle = 5" >> user-config.py
```

## Examples

### myscript.py

```
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
```


Execute
```
# python myscript.py
```
