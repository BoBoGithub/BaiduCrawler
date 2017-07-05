#!/user/bin/env python
# -*- coding:utf-8 -*-
#
# @author   Ringo
# @email    myfancoo@qq.com
# @date     2016/10/12
#

import requests
import time
import datetime
import logging
import pymysql as mdb
import config as cfg

log_file = './data/assess_logger.log'
logging.basicConfig(filename=log_file, level=logging.WARNING)

TEST_ROUND_COUNT = 0


def modify_score(ip, success, response_time):
    """
    代理数据评分
    """
    # type = 0 means ip hasn't pass the test

    # 连接数据库
    conn = mdb.connect(cfg.host, cfg.user, cfg.passwd, cfg.DB_NAME)
    cursor = conn.cursor()

    # ip超时
    if success == 0:
    	# 记录超时日志
        logging.warning(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + ip + " out of time") 

        try:
	    # 查询数据
            cursor.execute('SELECT * FROM %s WHERE content= "%s"' % (cfg.TABLE_NAME, ip))
            q_result = cursor.fetchall()

	    # 提取数据
            for r in q_result:
                test_times = r[1] + 1
                failure_times = r[2]
                success_rate = r[3]
                avg_response_time = r[4]

                # 超时达到4次且成功率低于标准 直接删除
                if failure_times > 4 and success_rate < cfg.SUCCESS_RATE:
                    cursor.execute('DELETE FROM %s WHERE content= "%s"' % (cfg.TABLE_NAME, ip))
                    conn.commit()
                    logging.warning(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + ip + " was deleted.")

                else:
                    # not too bad
                    failure_times += 1
                    success_rate = 1 - float(failure_times) / test_times
                    avg_response_time = (avg_response_time * (test_times - 1) + cfg.TIME_OUT_PENALTY) / test_times
                    score = (success_rate + float(test_times) / 500) / avg_response_time
                    n = cursor.execute('UPDATE %s SET test_times = %d, failure_times = %d, success_rate = %.2f, avg_response_time = %.2f, score = %.2f WHERE content = "%s"' % (TABLE_NAME, test_times, failure_times, success_rate, avg_response_time, score, ip))
                    conn.commit()

                    if n:
                        logging.error(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + ip + ' has been modify successfully!')

                break

        except Exception as e:
            logging.error(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + 'Error when try to delete ' + ip + str(e))

        finally:
            cursor.close()
            conn.close()

    elif success == 1:
        # pass the test
        try:
	    # 查询数据
            cursor.execute('SELECT * FROM %s WHERE content= "%s"' % (cfg.TABLE_NAME, ip))
            q_result = cursor.fetchall()

	    # 提取数据
            for r in q_result:
	    	# 测试次数++
                test_times = r[1] + 1

		# 设置失败次数
                failure_times = r[2]
		
		# 设置平均请求时间
                avg_response_time = r[4]
		
		# 计算成功的概率
                success_rate = 1 - float(failure_times) / test_times

		# 计算平均请求时间
                avg_response_time = (avg_response_time * (test_times - 1) + response_time) / test_times

		# 计算评分
                score = (success_rate + float(test_times) / 500) / avg_response_time
	
		# 更新评分入库
                n = cursor.execute('UPDATE %s SET test_times = %d, success_rate = %.2f, avg_response_time = %.2f, score = %.2f WHERE content = "%s"' %(cfg.TABLE_NAME, test_times, success_rate, avg_response_time, score, ip))
                conn.commit()

                if n:
                    logging.error(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + ip + 'has been modify successfully!')

                break

        except Exception as e:
            logging.error(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + 'Error when try to modify ' + ip + str(e))

        finally:
            cursor.close()
            conn.close()


def ip_test(proxies, timeout):

    # 设置检查代理请求地址
    url = 'https://www.baidu.com'

    # 循环检测代理数据
    for p in proxies:
        # 设置代理数据
        proxy = {'http': 'http://'+p}

        try:
            # 请求开始时间
            start = time.time()

	    # 获取请求数据
            r = requests.get(url, proxies=proxy, timeout=timeout)

            # 请求结束时间
            end = time.time()

            # 判断是否可用
            if r.text is not None:
	    	# 计算请求时间
                resp_time = end - start

		# 更新评分记录
                modify_score(p, 1, resp_time)

		# 输出请求日志
                print 'Database test succeed: '+p+'\t'+str(resp_time)

	    else:
	    	# 请求失败或超时 日志
                logging.warning(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + p + " out of time")

        except OSError:
	    # 请求异常
            modify_score(p, 0, 0)


def assess():
    global TEST_ROUND_COUNT
    TEST_ROUND_COUNT += 1
    logging.warning(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + ">>>>\t" + str(TEST_ROUND_COUNT) + " round!\t<<<<")

    # 连接数据库
    conn = mdb.connect(cfg.host, cfg.user, cfg.passwd, cfg.DB_NAME)
    cursor = conn.cursor()

    try:
    	# 查询代理数据
        cursor.execute('SELECT content FROM %s' % cfg.TABLE_NAME)
        result = cursor.fetchall()

	# 提取数据
        ip_list = []
        for i in result:
            ip_list.append(i[0])
        if len(ip_list) == 0:
            return
	
	# 检测数据　
        ip_test(ip_list, cfg.timeout)

    except Exception as e:
        logging.warning(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + str(e))

    finally:
        cursor.close()
        conn.close()


def main():
    while True:
        assess()

        # 每天定时
        time.sleep(cfg.CHECK_TIME_INTERVAL)

if __name__ == '__main__':
    main()
