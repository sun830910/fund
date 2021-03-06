# -*- coding: utf-8 -*-

"""
Created on 3/3/21 11:43 AM
@Author  : Justin Jiang
@Email   : jw_jiang@pku.edu.com
"""

import time
import json
import os


def get_time():
    """
    将time时间戳转换为特定格式的时间
    :param :
    :return:
    """
    time_arr = time.localtime()
    result = time.strftime("%Y-%m-%d %H:%M:%S", time_arr)
    return result


def parse_json(file_name: str) -> dict:
    """
    读取json文件
    dumps是将dict转化成str格式，loads是将str转化成dict格式。
    dump和load也是类似的功能，只是与文件操作结合起来了。
    :param file_name:
    :return:
    """
    try:
        if not os.path.exists(file_name):
            raise OSError("读取json文档错误，文档不存在，请检查路径是否正确")
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        str_lines = "".join(lines)
        if '\n' in str_lines:
            str_lines = str_lines.replace('\n', '')
        result = json.loads(str_lines)
        return result
    except OSError as e:
        raise e


if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_config_path = BASE_DIR + '/config/global_config.json'
    print(parse_json(default_config_path))
    total_fund_path = BASE_DIR + '/data/total_fund.json'
    result = parse_json(total_fund_path)
    print(len(result))
    print(type(result))
    print(get_time())
