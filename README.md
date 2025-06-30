> # Airtest多设备多脚本测试框架（增强版）
>
> multi-device-runner-pro-max 基于官方 multi-device-runner 重构，支持智能任务调度与聚合报告
> 
> [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
> ![Python Version](https://img.shields.io/badge/python-3.7%2B-green)
> 
> ## 🚀 核心优势
> 
> ### 突破官方限制
> | 功能                | 官方版本         | 本框架           |
> |---------------------|----------------|------------------|
> | 多脚本支持          | ❌ 仅单脚本      | ✅ 目录批量执行    |
> | 任务调度            | ❌ 简单并行      | ✅ 动态负载均衡    |
> | 设备分组策略        | ❌ 无            | ✅ 同设备串行/异设备并行 |
> | 报告系统            | ❌ 基础设备报告   | ✅ 设备+脚本联合报告 |
> 
> ### 智能任务调度
> ```mermaid
> flowchart TB
>     S[扫描test_*.py脚本] --> D{设备分组}
>     D -->|相同类型| S1[设备组A串行执行]
>     D -->|不同类型| P1[设备组B并行执行]
>     S1 --> T1[脚本1]
>     S1 --> T2[脚本2]
>     P1 --> T3[脚本1]
>     P1 --> T4[脚本2]
> ```
> 
> ## 快速开始
> ## ✨ Airtest 原特性
> ```python
> # 测试脚本元数据示例
> __author__ = "QA Team"
> __title__ = "支付功能测试"
> __priority__ = "P0"
> __timeout__ = 120  # 超时设置(秒)
> __retry__ = 2      # 失败重试次数
> # 测试用例描述
> __desc__ = """测试点：test_blackjack1.py 1、启动APP 2、点击公共首页酒店按钮 3、点击酒店首页查找酒店"""
"""
> ```
> 

> ### 测试框架执行说明
> 
> #### 1. 基础配置
> ```python
> # 获取已连接设备ID
> devices = [tmp[0] for tmp in ADB().devices()]  
> 
> # 关键路径配置
> air = 'test_blackbenjamin.air'  # 测试用例集根目录
> logs = "logs"  # 日志存放目录
> ```
> 
> #### 2. 执行命令
> ```python
> # 核心执行方法
> devices_tasks = run(
>     devices,     # 设备列表
>     air,         # 用例目录
>     logs,        # 日志路径
>     mode=False,   # 运行模式 (False=默认模式)
>     run_all=True # True=执行所有用例
> )
> 
> # 生成Airtest执行命令（内部自动构建）
> print(devices_tasks) 
> # 输出示例: ['airtest_run test_xx.air --device xxx --log logs/xxx']
> ```
> 
> #### 3. 报告生成效果
> **目录结构**  
> ```
> ├─logs  # 自动化生成的日志目录
> │ ├─66J5T19730001281_test_blackjack1  # 设备ID+用例名的独立日志
> │ ├─YWT0222A10000129_test_blackbenjamin
> │ └──...
> │
> ├─test_blackbenjamin.air  # 测试用例集目录
> │ └─test_xx.py  # 自动扫描的测试用例文件
> │
> ├─data.json      # 自动化生成的测试数据
> ├─report.html    # 最终测试报告
> └─report_tpl.html # 报告HTML模板
> ```
> 
> **生成文件说明**  
> - `data.json`：测试过程数据（截图、性能指标等）  
> - `report.html`：可视化测试报告（基于模板动态生成）  
> 
> #### 4. 关键补充
> - **动态用例发现**：自动扫描所有`test_xx.py`文件收集用例  
> - **设备分配策略**：
>   - 多设备自动负载均衡  
>   - 每个设备独立日志目录（避免冲突）  
> - **执行流程**：
>   1. 扫描设备 → 2. 收集用例 → 3. 分配任务 → 4. 生成日志 → 5. 构建报告
> - **模式说明**：
>   - `mode=False`：标准执行模式，默认负载均衡模式
>   - `run_all=True`：执行所有用例（False时执行指定用例集） 
> 
> ### 联系作者
> 
> **微信**  
> `wechat_benjamin`  
> 
> **邮箱**  
> `benjamin_v@qq.com`  
>
> **CSDN 博客**
> 
> https://qatester.blog.csdn.net/
> 
> **GitHub 参考**
> 
> https://github.com/AirtestProject/multi-device-runner  
>
> ## 许可协议
> Apache 2.0 © 2023-Present Your-Name