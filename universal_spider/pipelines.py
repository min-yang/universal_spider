# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import hashlib
import time
import os
import io
from minio import Minio
from urllib.parse import quote
from scrapy.utils.python import to_bytes

class UniversalSpiderPipeline(object):
    def open_spider(self, spider):
        self.minio_client = Minio(spider.settings['AWS_ENDPOINT_URL'][7:], 
                                  access_key=spider.settings['AWS_ACCESS_KEY_ID'], 
                                  secret_key=spider.settings['AWS_SECRET_ACCESS_KEY'], 
                                  secure=False)

        self.images_bucket, self.images_prefix = spider.settings['IMAGES_STORE'][5:].split('/', 1)
        self.files_bucket, self.files_prefix = spider.settings['FILES_STORE'][5:].split('/', 1)
        self.webpages_bucket, self.webpages_prefix = spider.settings['WEBPAGES_STORE'][5:].split('/', 1)
        self.index_bucket, self.index_prefix = spider.settings['INDEX_STORE'][5:].split('/', 1)
        
        self.index_path = self.index_prefix + spider.pro_id + '/index.csv'
        self.index_content = ''
                    
    def process_item(self, item, spider):   
        if item['text']:
            path = self.webpages_prefix + hashlib.sha1(to_bytes(item['url'])).hexdigest() + '.txt'
            self.index_content += item['url'] + '\t' + self.webpages_bucket + '\t' + path + '\n' 
            
            try:
                data = self.minio_client.stat_object(self.webpages_bucket, path)
                last_modified = time.mktime(data.last_modified)
                age_seconds = time.time() - last_modified
                age_days = age_seconds / 60 / 60 / 24                         
            except:
                age_days = 91   
                
            if age_days > 90:
                self.minio_client.put_object(
                    self.webpages_bucket, 
                    path, 
                    io.BytesIO(bytes(' '.join(item['text']), encoding='utf-8')),
                    len(item['text'])
                )
                spider.logger.info(item['url'] + ' write done!')                
            else:
                spider.logger.info(item['url'] + ' skipped!')    
                
            queue_key = 'webpage_audit_queue_' + spider.pro_id               
            mapping = {self.webpages_bucket + '/' + path: int(time.time()/60)}
            spider.redis_client.zadd(queue_key, mapping, nx=True)
                                        
        if item['images']:
            path = self.images_prefix + item['images'][0]['path']
            self.index_content += item['url'] + '\t' + self.images_bucket + '\t' + path + '\n'
               
            queue_key = 'image_audit_queue_' + spider.pro_id
            mapping = {self.images_bucket + '/' + path: int(time.time()/60)}
            spider.redis_client.zadd(queue_key, mapping, nx=True)
            
        if item['files']:
            path = self.files_prefix + item['files'][0]['path']
            self.index_content += item['url'] + '\t' + self.files_bucket + '\t' + path + '\n'
            
            queue_key = 'file_audit_queue_' + spider.pro_id
            mapping = {self.files_bucket + '/' + path: int(time.time()/60)}
            spider.redis_client.zadd(queue_key, mapping, nx=True)
                   
    def close_spider(self, spider):
        self.minio_client.put_object(
            self.index_bucket,
            self.index_path,
            io.BytesIO(bytes(self.index_content, encoding='utf-8')),
            len(self.index_content)
        )
        