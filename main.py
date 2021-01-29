import os
import argparse
from configparser import ConfigParser
from scraper import CollectPosts

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Non API public FB miner')

  parser.add_argument('-p', '--pages', nargs='+',
                      dest="pages",
                      help="List the pages you want to scrape for recent posts")

  parser.add_argument('-c', '--comments', nargs='+',
                      dest="comments",
                      help="List the comments you want to scrape for recent posts")

  parser.add_argument("-d", "--depth", action="store",
                      dest="depth", default=10, type=int,
                      help="How many recent posts you want to gather -- in multiples of (roughly) 8.")

  args = parser.parse_args()

  proDir = os.path.split(os.path.realpath(__file__))[0]
  configPath = os.path.join(proDir, "config.ini")

  cfg = ConfigParser()
  cfg.read(configPath)

  if not args.pages and not args.comments:
    print("Something went wrong!")
    print(parser.print_help())
    exit()

  if args.pages:
    C = CollectPosts(ids=args.pages, depth=args.depth)
    C.connectDB(cfg['db']['host'], cfg['db']['user'], cfg['db']['passwd'], cfg['db']['database'])
    C.login(cfg['facebook']['email'], cfg['facebook']['password'])
    C.collect("pages")

  if args.comments:
    C = CollectPosts(ids=args.comments, depth=args.depth)
    C.connectDB(cfg['db']['host'], cfg['db']['user'], cfg['db']['passwd'], cfg['db']['database'])
    C.login(cfg['facebook']['email'], cfg['facebook']['password'])
    C.collect("comments")
