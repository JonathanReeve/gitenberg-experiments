""" Gets a list of all the GITenberg repos, along with their descriptions and URLs. """
import github3
from getpass import getpass

try:
    from secrets import user, pw
except: 
    user = input('GitHub username: ')
    pw = getpass('GitHub password for {0}: '.format(user))

g = github3.login(user,pw)

org = g.organization('gitenberg')

for repo in org.iter_repos(): 
    try: 
        name = repo.name
        desc = repo.description
        url = repo.clone_url
        data = [name, desc, url]
        # Sanitize
        data = [item.replace('\t', ' ') for item in data]
        data = [item.replace('\n', ' ') for item in data]
        print('\t'.join(data))
    except: 
        continue
