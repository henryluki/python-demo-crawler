# -*- coding=utf-8 -*-
import requests,json,re
from lxml import etree
from multiprocessing.dummy import Pool as ThreadPool

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

#######
###  model
#######

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:1994225317@localhost/items'
db = SQLAlchemy(app)

class Items(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  item_id = db.Column(db.Integer, unique=True)
  title = db.Column(db.String(80))
  tag = db.Column(db.String(20))
  desc = db.Column(db.String(256))
  like = db.Column(db.Integer)
  comment = db.Column(db.Integer)
  share = db.Column(db.Integer)
  # products = db.relationship('products', backref='item',
  #                               lazy='dynamic')

  def __init__(self, item_id, title, tag, desc, like, comment, share):
      self.item_id = item_id
      self.title = title
      self.tag = tag
      self.desc = desc
      self.like = like
      self.comment = comment
      self.share = share

class Products(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'))
  title = db.Column(db.String(80))
  price = db.Column(db.Float)
  like = db.Column(db.Float)

  def __init__(self, item_id, title, price, like):
    self.item_id = item_id
    self.title = title
    self.price = price
    self.like = like

#######
###  spider
#######

API_URL = "http://www.liwushuo.com/api/channels/1/items?"
_URLS = [] # api urls
_URL_IDS = [] # tuple list for item urls and ids

class Spider(object):

  def __init__(self):
    super(Spider, self).__init__()

  def get_headers(self):
    headers = {
      'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; SV1; .NET CLR 1.1.4322)'
    }
    return headers

  def get_items(self, url):
    data = requests.get(url,headers = self.get_headers())
    return data.text

  def parse_items(self, url):
    data_temp = self.get_items(url)
    json_data = json.loads(data_temp)

    for item in json_data['data']['items']:
      _URL_IDS.append((item['content_url'],item['id']))

      status = Items.query.filter_by(item_id = item['id']).first()
      if not status:
        item_model = Items(item['id'],item['title'], item['short_title'], item['share_msg'],
          item['likes_count'],item['comments_count'],item['shares_count'])
        db.session.add(item_model)
        try:
          db.session.commit()
        except Exception, e:
          print "insert error"

  def parse_one_item(self, url_ids):
    html = self.get_items(url_ids[0])
    page = etree.HTML(html)

    titles = page.xpath(u"//h3[@class='item-title']")
    prices = page.xpath(u"//p[@class='item-info-price']")
    likes = page.xpath(u"//p[@class='item-like-info']")
    links = page.xpath(u"//a[@class='item-info-link']")

    for item in range(len(titles)):
      title = titles[item][1].text if titles[item][1].text else titles[item][0].text
      price = self.to_integer(prices[item][0].text)
      like = self.to_integer(likes[item].text)

      status = Products.query.filter_by(item_id = url_ids[1], title = title).first()
      if not status:
        product = Products(url_ids[1], title, price, like)
        db.session.add(product)
        try:
          db.session.commit()
        except Exception, e:
          print "insert error"

  def to_integer(self, temp_str):
    m = re.search(r'(\d+\.?\d+)', temp_str)
    return float(m.group(0))

  def one_item_run(self):
    pool = ThreadPool(8)  # 4 process
    pool.map(self.parse_one_item, _URL_IDS) # func , args
    pool.close()
    pool.join()
    # map(self.parse_one_item, _URL_IDS)

  def items_run(self):
    limit = 20
    offset = 20
    # for 400 hundreds items

    # for i in range(20):
    #   params ="limit=" + str(limit) + "&offset=" + str(i * offset)
    #   url = API_URL + params
    #   _URLS.append(url)

    for i in range(20):
      params ="limit=" + str(limit) + "&offset=" + str((20 - i) * offset)
      url = API_URL + params
      _URLS.append(url)

    pool = ThreadPool(4)  # 4 process
    pool.map(self.parse_items, _URLS) # func , args
    pool.close()
    pool.join()


#######
###  run
#######


def main():
  # db.create_all()

  s = Spider()
  s.items_run()
  s.one_item_run()
  print "finished!"

if __name__ == '__main__':
  main()