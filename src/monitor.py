# -*- coding: utf-8 -*-

"""
Created on 3/2/21 4:51 PM
@Author  : Justin Jiang
@Email   : jw_jiang@pku.edu.com
"""

import requests
import json
import re
from typing import List
import os
import datetime
import psutil
from logger import MyLogger
from utils import parse_json
import tushare as tu  # 指数追踪

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_config_path = BASE_DIR + '/config/global_config.json'


class FundMonitor(object):
    """
    基金收益查看器
    """

    def __init__(self):
        # 浏览器头
        self.headers = {'content-type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0'}
        self.pattern = r'^jsonpgz\((.*)\)'
        self.total_fund = None
        self.last_update_time = None
        self.global_config = parse_json(default_config_path)
        self.total_fund_file = self.global_config["total_fund_path"]
        self.target_fund = self.global_config["target_fund"]
        self.logger = MyLogger("monitor.py - Fund Monitor").get_logger()

    def str2list(self, context: str) -> List:
        """
        用于处理回来的数据的第一步
        :param context:
        :return:
        """
        result = []
        start, end = 0, 0
        while start < len(context) and end <= len(context):
            if context[start] == '[':
                if context[end] == ']':
                    result.append(context[start + 1:end])
                    start = end + 1
            else:
                start += 1
            end += 1
        return result

    def preprocess(self, context: str) -> dict:
        """
        回来数据的预处理主入口，后续存储成json保存用
        :param context:
        :return: dict, 形式为fund_num, [fund_name, fund_type]
        """
        temp = self.str2list(context)
        result = dict()
        for idx in temp:
            data = idx.split(',')
            assert len(data) == 5
            fund_num = str(data[0].strip('\"'))
            fund_name = data[2].strip('\"')
            fund_type = data[3].strip('\"')
            if fund_num not in result:
                result.setdefault(fund_num, [fund_name, fund_type])
        return result

    def get_fund_type_list(self):
        self.logger.info("正在更新所有基金列表")
        try:
            url = 'http://fund.eastmoney.com/js/fundcode_search.js'
            res = requests.get(url, headers=self.headers)
            context = re.findall('\[.*\]', res.text)
            context = context[0][1:-1]
            res = self.preprocess(context)  # 回来的数据预处理
            # 存文件
            with open(self.total_fund_file, 'w', encoding='utf-8') as file:
                json.dump(res, file, ensure_ascii=False)
        except:
            self.logger.waring("获取所有基金列表失败")
        else:
            self.logger.info("基金获取并保存完成")

    def get_info(self, fund_num: str) -> str:
        """
        获取基金信息的主入口
        :param fund_num: 基金号码
        :return: 基金信息
        """
        url = "http://fundgz.1234567.com.cn/js/%s.js" % fund_num
        try:
            res = requests.get(url, headers=self.headers)
            context = res.text
            re_result = re.findall(self.pattern, context)
            for idx in re_result:
                data = json.loads(idx)
                fund_num = data["fundcode"]
                fund_type = self.get_type(fund_num)
                formater = "基金:{} | {} | 收益率: {} %".format(data['name'], fund_type, data['gszzl'])
                return formater
        except:
            self.logger.waring("基金代码：{} ，搜索失败".format(fund_num))

    def read_total_fund(self):
        """
        初始化时用于读取全量基金类型使用
        :return:
        """
        try:
            if not os.path.exists(self.total_fund_file):
                raise OSError("全量基金文件不存在")
                self.get_fund_type_list()
            self.total_fund = parse_json(self.total_fund_file)
        except OSError as e:
            self.logger.waring("读取全量基金失败，文件不存在：{}".format(e))

    def get_type(self, fund_num: str) -> List:
        """
        获得该基金的名称与类型
        :param fund_num: 基金号码
        :return:
        """
        if self.total_fund is None:
            self.read_total_fund()
        if fund_num in self.total_fund:
            return self.total_fund.get(fund_num)[1]
        else:
            return []

    def get_target_fund_info(self, target_fund=None) -> List[str]:
        result = []
        if target_fund is None:
            self.logger.info("以global_config文件中的target_fund为目标进行全量查找")
            target_fund = self.target_fund
        for target in target_fund:
            target_result = self.get_info(target)
            result.append(target_result)
        return result


class SystemMonitor(object):
    """
    系统监视器
    """

    def __init__(self):
        self.logger = MyLogger("monitor.py - System Monitor").get_logger()

    def get_info(self):
        try:
            cpu_monitor = psutil.cpu_percent()  # 获取cpu使用情况
            memory_status = psutil.virtual_memory()  # 获取内存使用情况：系统内存大小，使用内存，有效内存，内存使用率
            memory_monitor = memory_status.percent  # 内存使用率
            now = datetime.datetime.now()  # 获取当前时间
            ts = now.strftime('%Y-%m-%d %H:%M:%S')
            line = f'{ts} cpu:{cpu_monitor}%, mem:{memory_monitor}%'
            return line
        except:
            self.logger.waring("获取系统状态失败")


class StockMonitor(object):
    """
    股票、指数监视器
    """

    def __init__(self):

        self.global_config = parse_json(default_config_path)
        self.total_stock = self.global_config["target_stock"]
        self.total_index = self.global_config["target_index"]
        self.total_mao = self.global_config["target_mao"]
        self.logger = MyLogger("monitor.py - Stock Monitor").get_logger()

    def get_realtime_quotes(self, target_arr: List[str]):
        """
        搜索标的，目前只能搜索沪深两市
        :param target_arr:
        :return:
        """
        result = []
        try:
            data = tu.get_realtime_quotes(target_arr)
            data = data.to_dict()
            for idx in range(len(target_arr)):
                idx_price = float(data.get('price').get(idx))
                idx_name = data.get('name').get(idx)
                idx_time = data.get('time').get(idx)
                idx_date = data.get('date').get(idx)
                idx_pre_close = float(data.get('pre_close').get(idx))
                idx_diff = (idx_price - idx_pre_close) / idx_pre_close * 100
                start = "{date} {time} - {name} |".format(date=idx_date, time=idx_time, name=idx_name)
                if idx_diff >= 0:
                    change = " 涨 {} % |".format(str(idx_diff)[:4])
                else:
                    change = " 跌 {} % |".format(str(idx_diff)[1:4])
                end = " 当前： {price} ".format(price=idx_price)
                idx_result = start + change + end
                result.append(idx_result)
            return result
        except:
            self.logger.waring("获得实时变化失败 ： {} ".format(target_arr))

    def get_total_mao(self):
        return self.get_realtime_quotes(self.total_mao)

    def get_total_stock(self):
        return self.get_realtime_quotes(self.total_stock)

    def get_total_index(self):
        return self.get_realtime_quotes(self.total_index)


if __name__ == '__main__':
    # logger = MyLogger("monitor.py - main").get_logger()
    # monitor = FundMonitor()
    # # print(monitor.get_info("000001"))  # 单笔查询
    # logger.info("----- 开始一次调查 -----")
    # result = monitor.get_target_fund_info()
    # for idx in result:
    #     logger.info(idx)
    # logger.info("----- 完成一次调查 -----")

    test = StockMonitor()
    stock_arr = ['600519', '601318', '600036']
    # print(test.get_realtime_quotes(stock_arr))
    index_arr = ['hs300', 'zh500', 'zxb', 'cyb']
    # print(test.get_realtime_quotes(index_arr))
    print(test.get_total_mao())
    print(test.get_total_index())
    print(test.get_total_stock())
