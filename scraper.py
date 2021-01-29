import os
import time
import sys
import re
import mysql.connector
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import urlparse, parse_qsl

class CollectPosts(object):

  def __init__(self, ids, depth=10, delay=2):

    self.ids = ids
    self.depth = depth
    self.delay = delay
    self.current = 0
    
    option = Options()
    option.add_argument("--disable-notifications")
    self.browser = webdriver.Chrome(chrome_options=option)

  def safe_find_element_by_id(self, elem_id):
    try:
        return self.browser.find_element_by_id(elem_id)
    except NoSuchElementException:
        return None

  def safe_find_element_by_xpath(self, path):
    try:
        return self.browser.find_element_by_xpath(path)
    except NoSuchElementException:
        return None

  def connectDB(self, host, user, passwd, database):
    self.db = mysql.connector.connect(
        host=host,
        user=user,
        passwd=passwd,
        database=database
    )
    self.dbcursor = self.db.cursor()
    print(self.db)

  def collect(self, typ):
    if typ == "pages":
      for iden in self.ids:
        self.collect_page(iden)
        self.collect_posts(iden)
    elif typ == "comments":
      for iden in self.ids:
        self.collect_comments(iden)
    self.browser.close()

  def login(self, email, password):
    try:
      self.browser.get("https://www.facebook.com")
      # self.browser.maximize_window()

      # filling the form
      self.browser.find_element_by_name('email').send_keys(email)
      self.browser.find_element_by_name('pass').send_keys(password)

      # clicking on login button
      self.browser.find_element_by_id('u_0_b').click()
      # if your account uses multi factor authentication
      mfa_code_input = self.safe_find_element_by_id('approvals_code')

      if mfa_code_input is None:
          return

      mfa_code_input.send_keys(input("Enter MFA code: "))
      self.browser.find_element_by_id('checkpointSubmitButton').click()

      # there are so many screens asking you to verify things. Just skip them all
      while self.safe_find_element_by_id('checkpointSubmitButton') is not None:
        dont_save_browser_radio = self.safe_find_element_by_id('u_0_3')
        if dont_save_browser_radio is not None:
            dont_save_browser_radio.click()

        self.browser.find_element_by_id('checkpointSubmitButton').click()

    except Exception:
        print("There was some error while logging in.")
        print(sys.exc_info()[0])
        exit()

  def get_soup (self):
    return BeautifulSoup(self.browser.page_source, "lxml")
  
  def scroll_page_to_elem (self, elem) :
    self.browser.execute_script('arguments[0].scrollIntoView({ block: "center" })', elem)

  def collect_posts(self, page):
    self.browser.get('https://www.facebook.com/' + page + '/')
    time.sleep(self.delay)

    while self.current < self.depth :
      htmltext = self.browser.page_source
      soup = BeautifulSoup(htmltext, "lxml")

      postList = soup.find_all('div', 'du4w35lb k4urcfbm l9j0dhe7 sjgh65i0')
      postTotal = len(postList)
      print('postTotal: ' + str(postTotal) + ' | current: ' + str(self.current))

      for post in postList[self.current:] : # Start from current postcount
          print('current Post: ' + str(self.current))
          # Extract id of each Post
          postLabelList = post.find('div', {'class': 'lzcic4wl', 'role': 'article'})['aria-describedby'].split(' ')

          # Get post id + link + type + date
          if self.safe_find_element_by_id(postLabelList[0]) is not None :
            postLinkElem = self.safe_find_element_by_xpath('//*[@id="'+ postLabelList[0] +'"]//a')
            if postLinkElem is not None :
              self.scroll_page_to_elem(postLinkElem)
              ActionChains(self.browser).move_to_element(postLinkElem).perform()
              time.sleep(self.delay)
            soup = self.get_soup()
            link = postLinkElem.get_attribute('href').split("?")[0]
            post_id = self.extract_post_id(link)
            typename = self.extract_post_type(link)
            post_created_date = soup.find('span', {'role': 'tooltip'}).text # Orginal format = 2020年12月08日星期三18:00
            post_created_date = re.sub(r"星期+(一|二|三|四|五|六|日)", "", post_created_date) # cut 星期三
            post_created_date = datetime.strptime(post_created_date, '%Y年%m月%d日%H:%M')
          
          # Get post caption
          if self.safe_find_element_by_id(postLabelList[1]) is not None :
            readmoreElem = self.safe_find_element_by_xpath('//*[@id="' + postLabelList[1] + '"]//*[text()="查看更多"]')
            if readmoreElem is not None:
              self.scroll_page_to_elem(readmoreElem)
              ActionChains(self.browser).move_to_element(readmoreElem).click().perform()
            caption = self.browser.find_element_by_id(postLabelList[1]).text
            
          # Get post comments
          comment_count = 0
          share_count = 0
          postTool = post.find('div', 'bp9cbjyn j83agx80 pfnyh3mw p1ueia1e').find_all('div', {'role': 'button'})
          for item in postTool :
            if '回應' in item.text :
              comment_count = re.findall(r"\d+", item.text.replace(',', ''))[0]
            elif '分享' in item.text:
              share_count = re.findall(r"\d+", item.text.replace(',', ''))[0]


          # Get post emoji
          if self.safe_find_element_by_id(postLabelList[3]) is not None :
            emojiTypeList = {
              'tc5IAx58Ipa': { 'label': 'like', 'val': 0 },
              'MB1XWOdQjV0': { 'label': 'heart', 'val': 0 },
              'bkP6GqAFgZ_': { 'label': 'haha', 'val': 0 },
              'QTVmPoFjk5O': { 'label': 'hug', 'val': 0 },
              'PByJ079GWfl': { 'label': 'angry', 'val': 0 },
              'tHO3j6Ngeyx': { 'label': 'wow', 'val': 0 },
              '1eqxxZX7fYp': { 'label': 'sad', 'val': 0 }
            }

            # Open Emoji Popup
            emojiToolElem = self.safe_find_element_by_xpath('//*[@id="'+ postLabelList[3] +'"]/span')
            if emojiToolElem is not None :
              self.scroll_page_to_elem(emojiToolElem)
              ActionChains(self.browser).move_to_element(emojiToolElem).click().perform()
              time.sleep(self.delay)
              soup = self.get_soup()
              emojiPopup = soup.find('div', {'role': 'dialog', 'aria-label': '心情數量'})
              emojiList = emojiPopup.find('div', 'soycq5t1 l9j0dhe7').find_all('div', {'role': 'tab'})
              for emojiItem in emojiList[2:] : # Ignore first 2 tabs
                emojiSrcName = emojiItem.find('img')['src'].split('/')[-1].split('.')[0]
                emojiTypeList[emojiSrcName]['val'] = int(emojiItem.text.replace(',', ''))

              # Close Emoji Popup
              emojiClose = self.safe_find_element_by_xpath('//div[@role="button"][@aria-label="關閉"]')
              if emojiClose is not None :
                ActionChains(self.browser).move_to_element(emojiClose).click().perform()

          postObj = {
              'user_id': page,
              'post_id': post_id,
              'typename': typename,
              'like_count': emojiTypeList['tc5IAx58Ipa']['val'],
              'heart_count': emojiTypeList['MB1XWOdQjV0']['val'],
              'haha_count': emojiTypeList['bkP6GqAFgZ_']['val'],
              'hug_count': emojiTypeList['QTVmPoFjk5O']['val'],
              'angry_count': emojiTypeList['PByJ079GWfl']['val'],
              'wow_count': emojiTypeList['tHO3j6Ngeyx']['val'],
              'sad_count': emojiTypeList['1eqxxZX7fYp']['val'],
              'comment_count': comment_count,
              'share_count': share_count,
              'caption': caption,
              'link': link,
              'post_created_date': post_created_date.strftime('%Y-%m-%d %H:%M:%S'),
              'last_updated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
          }

          self.insert_db_post(postObj)
          self.current = self.current + 1

    #Scroll
    self.browser.execute_script('window.scrollTo(0, document.body.scrollHeight)')
    time.sleep(self.delay)

  def collect_comments(self, postId):
    self.browser.get('https://www.facebook.com/' + postId + '/')
    time.sleep(self.delay)

    postElem = '//div[@class="d2edcug0 oh7imozk tr9rh885 abvwweq7 ejjq64ki"]'

    # Click filter options
    commentFilterElem = self.safe_find_element_by_xpath(postElem + '//div[@class="h3fqq6jp hcukyx3x oygrvhab cxmmr5t8 kvgmc6g5 j83agx80 bp9cbjyn"]')
    if commentFilterElem is not None:
      self.scroll_page_to_elem(commentFilterElem)
      commentFilterElem.click()
      time.sleep(self.delay)

    # Click filter all comments
    try :
      allcommentElem = WebDriverWait(self.browser, 8).until(EC.visibility_of_element_located((By.XPATH, '//div[@class="j34wkznp qp9yad78 pmk7jnqg kr520xx4"]//div[@role="menuitem"][last ()]')))
      allcommentElem.click()
      time.sleep(self.delay)
    except TimeoutException:
      print('TimeoutException')

    # Click all total comments
    i = 0
    while True:
      try :
        WebDriverWait(self.browser, 8).until_not(EC.presence_of_element_located((By.XPATH, postElem + '//div[@class="j83agx80 fv0vnmcu hpfvmrgz"]')))
        loadElem = WebDriverWait(self.browser, 2).until(EC.visibility_of_element_located((By.XPATH, postElem + '//div[@role="button"][.//*[text()="查看更多回應" OR contains(text(), "檢視另")]]')))
        self.scroll_page_to_elem(loadElem)
        loadElem.click()
        time.sleep(self.delay)
        i += 1
        print('click more: ' + str(i))
      except ElementClickInterceptedException:
        print('ElementClickInterceptedException')
        break
      except TimeoutException:
        print('TimeoutException')
        break
    
    # 1st level Hover
    comments = self.browser.find_elements_by_xpath(postElem + '//*[@class="cwj9ozl2 tvmbv18p"]/ul/li')
    for comment in comments:
      self.scroll_page_to_elem(comment)
      ActionChains(self.browser).move_to_element(comment).perform()

    # 2nd level expand
    # replies = comments.find_elements_by_xpath(postElem + '//*[@class="cwj9ozl2 tvmbv18p"]/ul/li//div[@role="button"][.//*[contains(text(), "對此讚好")]]')
    # for reply in replies:
    #   self.scroll_page_to_elem(reply)
    #   ActionChains(self.browser).move_to_element(reply).perform()

    # Click all read more
    readmoreElem = self.browser.find_elements_by_xpath(postElem + '//*[text()="查看更多"]')
    for item in readmoreElem:
      self.scroll_page_to_elem(item)
      ActionChains(self.browser).move_to_element(item).click().perform()

    soup = self.get_soup()
    commentsList = soup.select('div.d2edcug0.oh7imozk.tr9rh885.abvwweq7.ejjq64ki div.cwj9ozl2.tvmbv18p > ul > li')

    # Get reaction
    comments = self.browser.find_elements_by_xpath(postElem + '//div[@class="cwj9ozl2 tvmbv18p"]/ul/li')
    for comment in comments:
      print(comment)
      try:
        reaction = comment.find_element_by_xpath('.//div[@class="hyh9befq hn33210v jkio9rs9"]')
        print(reaction)
      except:
        print('no element')
      # self.scroll_page_to_elem(reaction)
      # ActionChains(self.browser).move_to_element(reaction).perform()

    # Get post id + link + type + date
    for comment in commentsList:
      link = comment.select_one('a.m9osqain.gpro0wi8.knj5qynh')['href']
      query = self.extract_comment_id(link)
      typename = 'media' if comment.find('div', 'j83agx80 bvz0fpym c1et5uql') else 'text'
      caption = comment.find('div', 'ecm0bbzt e5nlhep0 a8c37x1j').text
      reaction = comment.find('div', 'bp9cbjyn fni8adji hgaippwi')
        
      commentObj = {
        'comment_id': query['comment_id'],
        'reply_comment_id': query['reply_comment_id'],
        'typename': typename,
        'caption': caption,
        'link': 'https://www.facebook.com/' + query['comment_id'],
        # 'like_count': 0,
        # 'heart_count': 0,
        # 'haha_count': 0,
        # 'hug_count': 0,
        # 'angry_count': 0,
        # 'wow_count': 0,
        # 'sad_count': 0,
        # 'post_created_date': post_created_date.strftime('%Y-%m-%d %H:%M:%S'),
        'last_updated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
      }

      self.insert_db_comment(commentObj)

  def collect_page(self, page):
    self.browser.get('https://www.facebook.com/' + page + '/about')
    time.sleep(self.delay)

    # Click all read more
    readmoreElem = self.browser.find_elements_by_xpath('//*[text()="查看更多"]')
    for item in readmoreElem :
      self.scroll_page_to_elem(item)
      ActionChains(self.browser).move_to_element(item).click().perform()

    # Get like count
    like_count = 0
    likeElem = self.safe_find_element_by_xpath('//div[@class="qzhwtbm6 knvmm38d"][.//*[contains(text(), "對此讚好")]]')
    if likeElem is not None :
      like_count = re.findall(r"\d+", likeElem.text.replace(',', ''))[0]

    # Get like count
    followers = 0
    followersElem = self.safe_find_element_by_xpath('//div[@class="qzhwtbm6 knvmm38d"][.//*[contains(text(), "人在追蹤")]]')
    if followersElem is not None :
      followers = re.findall(r"\d+", followersElem.text.replace(',', ''))[0]

    # Get checkin
    checkin = 0
    checkinElem = self.safe_find_element_by_xpath('//div[@class="qzhwtbm6 knvmm38d"][.//*[contains(text(), "曾在這裡簽到")]]')
    if checkinElem is not None :
      checkin = re.findall(r"\d+", checkinElem.text.replace(',', ''))[0]

    # Get biography
    biography = ''
    biographyElem = self.safe_find_element_by_xpath('//div[@class="kvgmc6g5 cxmmr5t8 oygrvhab hcukyx3x c1et5uql"]')
    if biographyElem is not None :
      biography = biographyElem.text

    page_info = {
      'user_id': page,
      'like_count': like_count,
      'checkin_count': checkin,
      'followers': followers,
      'biography': biography,
      'last_updated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    self.insert_db_page(page_info)

  def extract_post_id (self, link) :
    return list(filter(None, link.split('/')))[-1]

  def extract_post_type (self, link) :
    if '/videos/' in link :
      return 'videos'
    elif '/photos/' in link:
      return 'photos'
    else :
      return 'posts'

  def extract_comment_id (self, link):
    parsed_url = urlparse(link)
    query = dict(parse_qsl(parsed_url.query))
    return {
      'comment_id': query.get('comment_id', None),
      'reply_comment_id': query.get('reply_comment_id', None)
    }

  def insert_db_page(self, pageObj):
    print(pageObj)
    # Check Duplicate Post by user_id
    self.dbcursor.execute("SELECT * FROM facebook WHERE user_id = '"+ pageObj['user_id'] +"'")
    sqlpage = self.dbcursor.fetchall()

    if len(sqlpage) > 0:
      # Update Post
      sql = """UPDATE facebook SET
                like_count = %s,
                checkin_count = %s,
                followers = %s,
                last_updated_date = %s
                WHERE user_id = """ + "'" + pageObj['user_id'] + "'"
      val = (pageObj['like_count'],
             pageObj['checkin_count'],
             pageObj['followers'],
             pageObj['last_updated_date'])
      self.dbcursor.execute(sql, val)
      self.db.commit()
    else :
      # Insert Post
      sql = """INSERT INTO facebook(
                user_id,
                biography,
                like_count,
                checkin_count,
                followers,
                last_updated_date)
                VALUES (%s, %s, %s, %s, %s, %s)"""
      val = (pageObj['user_id'],
             pageObj['biography'],
             pageObj['like_count'],
             pageObj['checkin_count'],
             pageObj['followers'],
             pageObj['last_updated_date'])
      self.dbcursor.execute(sql, val)
      self.db.commit()

  def insert_db_post (self, postObj) :
    # Check Duplicate Post by post_id
    self.dbcursor.execute("SELECT * FROM facebook_posts WHERE post_id = '"+ postObj['post_id'] +"'")
    sqlpost = self.dbcursor.fetchall()

    if len(sqlpost) > 0 :
      # Update Post
      sql = """UPDATE facebook_posts SET
                like_count = %s,
                heart_count = %s,
                haha_count = %s,
                hug_count = %s,
                angry_count = %s,
                wow_count = %s,
                sad_count = %s,
                comment_count = %s,
                share_count = %s,
                last_updated_date = %s
                WHERE post_id = """ + "'" + postObj['post_id'] + "'"
      val = (postObj['like_count'],
             postObj['heart_count'],
             postObj['haha_count'],
             postObj['hug_count'],
             postObj['angry_count'],
             postObj['wow_count'],
             postObj['sad_count'],
             postObj['comment_count'],
             postObj['share_count'],
             postObj['last_updated_date'])
      self.dbcursor.execute(sql, val)
      self.db.commit()
    else :
      # Insert Post
      sql = """INSERT INTO facebook_posts(
                user_id,
                post_id,
                typename,
                like_count,
                heart_count,
                haha_count,
                hug_count,
                angry_count,
                wow_count,
                sad_count,
                comment_count,
                share_count,
                caption,
                link,
                post_created_date,
                last_updated_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
      val = (postObj['user_id'],
             postObj['post_id'],
             postObj['typename'],
             postObj['like_count'],
             postObj['heart_count'],
             postObj['haha_count'],
             postObj['hug_count'],
             postObj['angry_count'],
             postObj['wow_count'],
             postObj['sad_count'],
             postObj['comment_count'],
             postObj['share_count'],
             postObj['caption'],
             postObj['link'],
             postObj['post_created_date'],
             postObj['last_updated_date'])
      self.dbcursor.execute(sql, val)
      self.db.commit()

  def insert_db_comment (self, commentObj):
    print(commentObj)
