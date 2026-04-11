import requests, urllib.parse
journals = ['The Journal of Finance', 'Journal of Financial Economics', 'The Review of Financial Studies', 'Journal of Financial and Quantitative Analysis', 'Review of Finance', 'The Accounting Review', 'Journal of Accounting Research', 'Journal of Accounting and Economics', 'Contemporary Accounting Research', 'Review of Accounting Studies']
for j in journals:
    url = f'https://api.crossref.org/journals?query={urllib.parse.quote(j)}&rows=1'
    resp = requests.get(url).json()
    items = resp.get('message', {}).get('items', [])
    if items:
        print(f'{j}: {items[0].get("ISSN", [])}')
    else:
        print(f'{j}: NONE')
