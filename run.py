# -*- encoding=utf-8 -*-
# Run Airtest in parallel on multi-device-runner-pro-max
import os
import traceback
import subprocess
import webbrowser
import time
import json
import shutil
from gevent.pool import Pool
from gevent import monkey; monkey.patch_all(select=False)  # 关键补丁
from airtest.core.android.adb import ADB
from jinja2 import Environment, FileSystemLoader


# 获取指定目录的被测文件列表，以"xx"（test_）前缀为准，xx结尾的文件为测试用例，未考虑重名文件
def find_test_files(root_dir):
    """识别测试文件，自动处理文件和目录两种输入"""
    result = []

    if os.path.isfile(root_dir):
        # 处理单个文件情况
        if root_dir.endswith('_test.py'):
            return [root_dir]
        return []

    elif os.path.isdir(root_dir):
        # 处理目录情况
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith('_test.py'):
                    result.append(os.path.join(root, file))
        return result


# 动态负载均衡设备执行脚本
def map_tasks(devices, air, mode=False):
    """
    Args:
        devices:    可使用设备列表，动态获取
        test_files: 获取指定目录的被测文件列表
        mode:   模式 0默认负载均衡，1手动设置为兼容模型
    Returns:        动态负载均衡均分并行执行
    """
    test_files = find_test_files(air)
    result = {}
    unused_devices = set(devices)  # 跟踪未使用的设备
    device_count = len(devices)
    device_index = 0

    for file_path in test_files:
        path_parts = file_path.split('\\')
        base_name = os.path.splitext(path_parts[-1])[0]

        # 兼容模式
        if mode:
            for device in devices:
                result.setdefault(f"{device}", [])
                result[f"{device}"].append(
                    {
                        "py_path": file_path,
                        "log_path": f"{device}_{base_name}",
                    }
                )

        # 负载均衡模式
        else:
            # 优先使用路径中匹配的设备
            matched_device = next((d for d in devices if d in path_parts), None)
            if matched_device:
                current_device = matched_device
                if current_device in unused_devices:
                    unused_devices.remove(current_device)
            else:
                # 优先分配未使用的设备
                if unused_devices:
                    current_device = next(iter(unused_devices))
                    unused_devices.remove(current_device)
                else:
                    current_device = devices[device_index % device_count]
                    device_index += 1

            result.setdefault(f"{current_device}", [])
            result[f"{current_device}"].append(
                {
                    "py_path": file_path,
                    "log_path": f"{current_device}_{base_name}",
                }
            )

    return result


# 并发执行Airtest测试脚本
def execute_concurrent_airtest_run(devices_tasks):
    """
    并发执行Airtest测试脚本
    参数:
        devices_tasks (dict):
            - 必须包含设备ID作为键
            - 每个设备ID对应一个测试脚本配置列表
            - 每个配置需包含:
                * py_path: 测试脚本路径
                * log_path: 日志保存路径
                * airtest_run_cmd: 完整的airtest命令行参数列表
    返回:
        dict: 修改后的测试数据字典，每个测试配置会新增:
            - status: 子进程执行状态码（0表示成功）
    """
    def airtest_run_cme(device):
        for device_info in devices_tasks[device]:
            cmd = device_info.get("airtest_run_cmd", None)
            if cmd:
                device_info["start_time"] = time.time()
                status = subprocess.call(cmd, shell=True, cwd=os.getcwd())
                device_info["status"] = status
                device_info["end_time"] = time.time()
                device_info["spend_time"] = device_info["end_time"] - device_info["start_time"]

    producer_tasks = []
    producer_pool = Pool(size=len(devices_tasks))
    for device in devices_tasks:
        producer_tasks.append(producer_pool.spawn(airtest_run_cme, device))
    producer_pool.join()

    return devices_tasks


def run(devices, air, report_start, mode=False, run_all=False):
    """"
        mode
            = True: 兼容模式，多台设备并行，单设备脚本串行，每个脚本只执行设备数据的次数
            = False: 负载均衡模式，多台设备并行，单设备脚本串行，每个脚本只执行1次
        run_all
            = True: 从头开始完整测试 (run test fully) ;
            = False: 续着data.json的进度继续测试 (continue test with the progress in data.jason)
    """
    try:
        logs = f"{report_start}_logs"
        results = load_jdon_data(air, logs, report_start, run_all)
        devices_tasks = run_on_multi_device(devices, air, logs, results, mode, run_all)
        for device in devices_tasks:
            for task in devices_tasks[device]:
                status = task.get("status", "no value")
                if status != "no value":
                    airtest_one_report = run_one_report(task['py_path'], logs, task['log_path'])
                    airtest_one_report["airtest_run_cmd"] = task["airtest_run_cmd"]
                    airtest_one_report["spend_time"] = task["spend_time"]
                    results['tests'][task['log_path']] = airtest_one_report
                    results['tests'][task['log_path']]['status'] = status
        results['end'] = time.time()
        results['spend_time'] = results['end'] - results['start']
        json.dump(results, open(f'{report_start}_data.json', "w"), indent=4)
        run_summary(results, report_start)
        return results
    except Exception as e:
        traceback.print_exc()


def run_on_multi_device(devices, air, logs, results, mode, run_all):
    """
        在多台设备上运行airtest脚本
        Run airtest on multi-device-runner-pro-max
    """
    devices_tasks = map_tasks(devices, air, mode)
    airtest_run_num = 0
    for device in devices_tasks:
        for device_tasks in devices_tasks[device]:
            dev = device_tasks["log_path"]
            if (not run_all and results['tests'].get(dev) and results['tests'].get(dev).get('status') == 0):
                print("Skip device %s" % dev)
                continue
            else:
                log_dir = get_log_dir(dev, logs)
                airtest_run_cmd = [
                    "airtest",
                    "run",
                    device_tasks["py_path"],
                    "--device",
                    "Android:///" + device,
                    "--log",
                    log_dir
                ]
                device_tasks["airtest_run_cmd"] = airtest_run_cmd
                airtest_run_num += 1

    if airtest_run_num == 0:
        return devices_tasks

    # 多设备并行执行 airtest_run_cmd
    devices_tasks = execute_concurrent_airtest_run(devices_tasks)
    return devices_tasks


def run_one_report(air, logs, dev):
    """"
        生成一个脚本的测试报告
        Build one test report for one air script
    """
    try:
        log_dir = get_log_dir(dev, logs)
        log = os.path.join(log_dir, 'log.txt')
        if os.path.isfile(log):
            airtest_report_cmd = [
                "airtest",
                "report",
                air,
                "--log_root",
                log_dir,
                "--outfile",
                os.path.join(log_dir, 'log.html'),
                "--lang",
                "zh"
            ]
            ret = subprocess.call(airtest_report_cmd, shell=True, cwd=os.getcwd())
            return {
                    'airtest_report_cmd': airtest_report_cmd,
                    'status': ret,
                    'path': os.path.join(log_dir, 'log.html'),
                    'path_time': time.time(),
            }
        else:
            print("Report build Failed. File not found in dir %s" % log)
    except Exception as e:
        traceback.print_exc()
    return {'status': -1, 'device': dev, 'path': '', 'path_time': time.time(), 'airtest_report_cmd': ''}


def run_summary(data, report_start):
    """"
        生成汇总的测试报告
        Build sumary test report
    """
    try:
        summary = {
            'time': "%.3f" % (time.time() - data['start']),
            'success': [item['status'] for item in data['tests'].values()].count(0),
            'count': len(data['tests'])
        }
        summary.update(data)
        summary['start'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data['start']))
        env = Environment(loader=FileSystemLoader(os.getcwd()), trim_blocks=True)
        html = env.get_template('report_tpl.html').render(data=summary)
        report_html = f"{report_start}_report.html"
        with open(report_html, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(report_html)
    except Exception as e:
        traceback.print_exc()


def load_jdon_data(air, logs, report_start, run_all):
    """"
        加载进度
            如果data.json存在且run_all=False，加载进度
            否则，返回一个空的进度数据
        Loading data
            if data.json exists and run_all=False, loading progress in data.json
            else return an empty data
    """
    json_file = os.path.join(os.getcwd(), f'{report_start}_data.json')
    if (not run_all) and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        clear_log_dir(logs)
        return {
            'start': time.time(),
            'script': air,
            'tests': {},
            'data_json': f'{report_start}_data.json',
            'report_html': f'{report_start}_report.html'
        }


def clear_log_dir(logs):
    """"
        清理log文件夹 test_blackjack.air/log
        Remove folder test_blackjack.air/log
    """
    log_path = os.path.join(os.getcwd(), logs)
    if os.path.exists(log_path):
        shutil.rmtree(log_path)
    os.makedirs(log_path, exist_ok=True)


def get_log_dir(device, logs):
    """"
        在 test_blackjack.air/log/ 文件夹下创建每台设备的运行日志文件夹
        Create log folder based on device name under test_blackjack.air/log/
    """
    log_dir = os.path.join(logs, device.replace(".", "_").replace(':', '_'))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir


def run_all_route_test_case(air, devices=None, mode=False, report_start_data=None):
    """
        air
            传入用例目录，扫描目录中的 _test.py 命名结尾的文件
            传入用例文件，需以 _test.py 命名结尾的用例
        devices
            传入可用设备列表 ['66J5T19730001281', 'YWT0222A10000129']，adb指定设备运行
            不传入，默认获取已连接设备
        mode
            = True: 兼容模式，多台设备并行，单设备脚本串行，每个脚本只执行设备数据的次数
            = False: 负载均衡模式，多台设备并行，单设备脚本串行，每个脚本只执行1次
        report_start_data
            传入断点续跑 或 重试失败的用例，传入 1753085644830_data.json 记录用例执行报告的数据
    """
    if air is None:
        return False

    if devices is None:
        devices = [tmp[0] for tmp in ADB().devices()]

    if report_start_data is None:
        report_start = int(time.time() * 1000)
        run_all = True
    else:
        report_start = report_start_data.split("_")[0]
        run_all = False

    devices_tasks = run(devices, air, report_start, mode=mode, run_all=run_all)
    return devices_tasks



if __name__ == '__main__':
    """
        初始化数据
        Init variables here
    """

    # 调试代码
    # devices = ['66J5T19730001281', 'YWT0222A10000129']
    air = r'D:\code_path\Python\AUI\Tests\Tmapi-Client'

    # Resun all script
    devices_tasks = run_all_route_test_case(air, report_start_data="1753090954431_data.json")


    # Continue tests saved in xxxx_data.json
    # Skip scripts that run succeed
    # 基于{report_start}_data.json的进度，跳过已运行成功的脚本
    air = r'D:\code_path\Python\AUI\Tests\Tmapi-Client\testAICase\ai_AIcaseEasyDemo_test.py'
    # run_all_route_test_case(air, devices=None, mode=True, report_start_data="1752648916360_data.json")
    devices_tasks = run_all_route_test_case(air, mode=False, report_start_data="1753085644830_data.json")
