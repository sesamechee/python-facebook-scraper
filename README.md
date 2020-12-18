# Facebook Scraper

## What It can Do


## Usage
#### 1. Add config.ini
    [db]
    host=localhost
    user=root
    passwd=
    database=xxx

    [facebook]
    email=xxx
    password=xxx
    
#### 2. Use main.py to scrape
    usage: main.py [-h] -page PAGE -depth DEPTH

    Facebook Scraper

    optional arguments:
      -h, --help                                        show this help message and exit

    required arguments:
      -page PAGE, -p PAGE                               The Facebook Public Page you want to scrape
      -depth DEPTH, -l DEPTH                            Number of Posts you want to scrape

    optional arguments:
      -h, --help                                        show this help message and exit
      -p PAGES [PAGES ...], --pages PAGES [PAGES ...]   List the pages you want to scrape for recent posts
      -d DEPTH, --depth DEPTH                           How many recent posts you want to gather -- in multiples of (roughly) 8.
