#!/usr/bin/env python
# -*- coding=utf-8 -*-
from airtest.core.api import *
import time

__author__ = "Benjamin"  # 替换实际作者名:ml-citation{ref="7" data="citationList"}
__title__ = "报告聚合调试 test_blackjack4.py"  # 报告标题:ml-citation{ref="7" data="citationList"}
__desc__ = """
测试点：test_blackjack4.py
1、启动APP
2、点击公共首页酒店按钮
3、点击酒店首页查找酒店
"""  # 多行描述:ml-citation{ref="7" data="citationList"}

ElementsRepo = "../../ElementsRepo/app"
ElementsRepo_assert = "../../ElementsRepo/app_assert"

start_app("com.benjamin.android")
# 点击公共首页酒店按钮
touch(Template(f"{ElementsRepo}/public/酒店2.png"))
