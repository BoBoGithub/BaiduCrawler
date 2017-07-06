# -*- coding:utf-8 -*-
import sys
import requests
from lxml import etree
import random
import ip_pool
import threading

reload(sys)
sys.setdefaultencoding('utf-8')

"""
================================================
 Extract text from the result of BaiDu search
================================================
"""

# 全局变量定义
keywords	= []
threadPool	= []
queueArr	= []
useful_proxies	= {}

def download_html(keywords, proxy):
    """
    抓取网页
    """
    # 抓取参数 https://www.baidu.com/s?wd=testRequest
    key = {'wd': keywords}
    
    # 请求Header
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Trident/7.0; rv:11.0 cb) like Gecko'}

    proxy = {'http': 'http://'+proxy}

    # 抓取数据内容
    web_content = requests.get("https://www.baidu.com/s?", params=key, headers=headers, proxies=proxy, timeout=4)

    return web_content.text


def html_parser(html):
    """
    解析html
    """
    # 设置提取数据正则
    path_cn = "//div[@id='content_left']//div[@class='c-abstract']/text()"
    path_en = "//div[@id='content_left']//div[@class='c-abstract c-abstract-en']/text()"

    # 提取数据
    tree = etree.HTML(html)
    results_cn = tree.xpath(path_cn)
    results_en = tree.xpath(path_en)
    text_cn = [line.strip() for line in results_cn]
    text_en = [line.strip() for line in results_en]

    # 设置返回结果
    text_str = ''

    # 提取数据
    if len(text_cn) != 0 or len(text_en) != 0:
        # 提取中文
        if len(text_cn):
            for i in text_cn:
                text_str += (i.strip())
        # 提取英文
        if len(text_en) != 0:
            for i in text_en:
                text_str += (i.strip())
    # 返回结果
    return text_str

# 设置字典数据
def dealKeywordDict(key, word):
    global queueArr

    queueArr[key].append(word)


def extract_all_text(keyword_dict, keyword_text, ip_factory, threadNum):
    """
    存储结果
    """
    global keywords
    global threadPool
    global queueArr
    global useful_proxies

    #useful_proxies = {}
    max_failure_times = 3
    try:
        # 获取代理IP数据
        for ip in ip_factory.get_proxies():
            useful_proxies[ip] = 0

        print "总共：" + str(len(useful_proxies)) + 'IP可用'

    except OSError:
        print "获取代理ip时出错！"

    # 提取抓取的关键词
    cn = open(keyword_dict, 'r')
    for line in cn:
        keywords.append(line.strip())
    cn.close()

    # 初始化线程字典数组
    for i in range(threadNum):
	queueArr.append([])
    
    # 提取关键词到线程字典数组
    nums      = 0
    for char in keywords:
	dealKeywordDict(nums % threadNum, char)
	nums += 1

    # 启动多个下载
    for i in range(threadNum):
	threadRet = startDownload(i)

    # 结束开启的线程
    for thread in threadPool:
	thread.join(30)

def startDownload(i):
	global threadPool

        # 实例化 抓取数据线程
	dataThread = GetDataThread(i)

        # 追加进线程池数组
	threadPool.append(dataThread)

        # 启动线程
	dataThread.start()


class GetDataThread(threading.Thread):
	def __init__(self, i):
		threading.Thread.__init__(self)
		self.i	= i

	def run(self):
		global queueArr
		global useful_proxies

		# 保存抓取结果文件
		keyword_text = 'data/results.txt'

    		with open(keyword_text, 'w') as ct:
	       		# 逐行读取关键词
        		for word in queueArr[self.i]:
			
           	 		# 设置随机代理
            			proxy = random.choice(useful_proxies.keys())
            			print "change proxies: " + proxy

            			content = ''
            			try:
               				content = download_html(word.strip(), proxy)
            			except OSError:
               				# 超过3次则删除此proxy
               				useful_proxies[proxy] += 1
               				if useful_proxies[proxy] > 3:
               					useful_proxies.remove(proxy)
               				# 再抓一次
                			proxy = random.choice(useful_proxies.keys())
                			content = download_html(word.strip(), proxy)

            			raw_text = html_parser(content)
            			raw_text = raw_text.replace('\n', '||')
            			print raw_text

            			# 写入数据到文件
            			ct.write(word.strip()+':\t'+raw_text+'\n')

        		ct.close()


def main():
    # 抓取搜索关键词
    keyword_dict = 'data/samples.txt'
    # 抓取存取结果
    keyword_text = 'data/results.txt'

    # 启动线个数
    threadNum	= 5

    # 抓取数据
    extract_all_text(keyword_dict, keyword_text, ip_pool.ip_factory, threadNum)

if __name__ == '__main__':
    main()
