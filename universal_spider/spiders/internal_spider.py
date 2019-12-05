# -*- coding: utf-8 -*-
from ..items import Webpage
from scrapy import Spider, Request
import redis
import time
import random
import hashlib
import os

class InternalSpider(Spider):
    name = 'internal_spider'
    #allowed_domains -- 通过参数传递
    #start_urls -- 通过参数传递
    img_suffix = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp', 'ico', 'tif', 'pcx', 'tga', 'exif', 'fpx', 'svg', 'psd', 'cdr', 'pcd', 'dxf', 'ufo', 'eps', 'ai', 'raw', 'WMF']
    file_suffix = ['7z', 'rar', 'zip', 'gz', 'pdf', 'txt', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'eml', 'csv', 'epub', 'json', 'msg', 'odt', 'rm', 'avi', 'mp4', 'mpg', 'mov', 'swf', 'rtf', 'xlsm', 'xltx', 'xltm']
    not_support_suffix = ['css', 'js', 'jsp']
    
    def __init__(self, start_urls, allowed_domains, pro_id, *args, **kwargs):
        super(InternalSpider, self).__init__(*args, **kwargs)
        self.start_urls = eval(start_urls)             
        self.allowed_domains = eval(allowed_domains)

        # Redis 
        self.redis_client = redis.Redis(host='172.16.0.227', port=6379, db=0, password='T2BKn0EH')       
        ret = self.redis_client.zrank('task_queue', pro_id)
        if ret != None:
            self.logger.error('Pro ID already exists!')
            raise ValueError('Pro ID already exists!')
  
        self.redis_client.zadd('task_queue', {pro_id: int(time.time()/60)})
        self.pro_id = pro_id
    
    def start_request(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)
          
    def parse(self, response): 
        item = Webpage()
        item['url'] = response.url
        item['text'] = None
        item['image_urls'] = []
        item['file_urls'] = []
        
        suffix = response.url.split('.')[-1]
        
        if suffix in self.img_suffix:
            item['image_urls'].append(response.url)       
            yield item
            return         
        elif suffix in self.file_suffix:
            item['file_urls'].append(response.url)
            yield item
            return          
        else:
            try:       
                item['text'] = response.xpath('//text()').extract()  
            except:
                self.logger.info('<%s> Unable to extract text from the link!' %response.url)
                
            try:
                url_list = response.xpath('//@href|//@src').getall()
                url_set = set()
                for url in url_list:
                    url_set.add(response.urljoin(url))   
            except Exception as e:
                self.logger.error('<' + response.url + '>' + str(e))  
                return

            yield item
               
        for url in url_set:  
            suffix = url.split('.')[-1]
            if suffix in self.not_support_suffix:
                continue
                
            no_filter = False
            if suffix in self.img_suffix + self.file_suffix:
                no_filter = True
            yield Request(url=url, callback=self.parse, dont_filter=no_filter)
            