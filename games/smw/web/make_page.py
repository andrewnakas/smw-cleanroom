"""Write index.html for the web build from shell.html."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
site = sys.argv[1]
s = open(os.path.join(here, 'shell.html'), encoding='utf-8').read()
open(os.path.join(site, 'index.html'), 'w', encoding='utf-8', newline='\n').write(s)
open(os.path.join(site, '.nojekyll'), 'w').close()
print('page ->', os.path.join(site, 'index.html'))
