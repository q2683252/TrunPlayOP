#!/usr/bin/env python3
"""
TrunPlay 测试场景复现工具

快速搭建特定测试场景的辅助脚本。

Usage:
    python reproduce_helper.py <command> [options]

Commands:
    setup-devices <count>     创建多个模拟设备
    setup-plans <count>       创建多个测试计划
    setup-history <count>     创建播放历史记录
    setup-study-tasks <count> 创建学习任务
    clear-all                 清空所有测试数据
    status                    显示当前数据状态
"""

import sys
import json
import argparse
from datetime import datetime

try:
    import httpx
except ImportError:
    print("请先安装 httpx: pip install httpx")
    sys.exit(1)


API_BASE = "http://localhost:8088/api/v1"


def api_get(endpoint: str) -> dict:
    """发送 GET 请求"""
    try:
        response = httpx.get(f"{API_BASE}{endpoint}", timeout=10.0)
        return response.json()
    except Exception as e:
        print(f"请求失败: {e}")
        return {"error": str(e)}


def api_post(endpoint: str, data: dict = None) -> dict:
    """发送 POST 请求"""
    try:
        response = httpx.post(f"{API_BASE}{endpoint}", json=data or {}, timeout=10.0)
        return response.json()
    except Exception as e:
        print(f"请求失败: {e}")
        return {"error": str(e)}


def api_delete(endpoint: str) -> dict:
    """发送 DELETE 请求"""
    try:
        response = httpx.delete(f"{API_BASE}{endpoint}", timeout=10.0)
        return response.json()
    except Exception as e:
        print(f"请求失败: {e}")
        return {"error": str(e)}


def setup_devices(count: int):
    """创建多个模拟设备"""
    print(f"创建 {count} 个模拟设备...")

    for i in range(count):
        result = api_post("/devices/add", {
            "address": f"114.193.206.{100 + i}",
            "port": 8200
        })
        if "error" not in result:
            print(f"  创建设备 {i + 1}: 114.193.206.{100 + i}")
        else:
            print(f"  设备 {i + 1} 创建失败: {result.get('message', 'unknown error')}")

    print(f"完成: 已尝试创建 {count} 个设备")


def setup_plans(count: int):
    """创建多个测试计划"""
    print(f"创建 {count} 个测试计划...")

    for i in range(count):
        hour = 8 + (i % 12)
        result = api_post("/plans", {
            "title": f"测试计划 {i + 1}",
            "start_time": f"{hour:02d}:00",
            "end_time": f"{hour + 1:02d}:00",
            "repeat_days": "1,2,3,4,5",
            "media_url": f"smb://nas/videos/video_{i:03d}.mp4",
            "is_active": i % 2 == 0  # 一半激活，一半未激活
        })
        if "error" not in result and result.get("code") == 0:
            print(f"  创建计划 {i + 1}: 测试计划 {i + 1}")
        else:
            print(f"  计划 {i + 1} 创建失败")

    print(f"完成: 已尝试创建 {count} 个计划")


def setup_history(count: int):
    """创建播放历史记录 (需要先有计划)"""
    print(f"创建 {count} 条播放历史...")
    print("注意: 播放历史需要通过实际播放创建，此功能需要后端支持直接插入")
    print("建议通过手动播放来生成历史记录")


def setup_study_tasks(count: int):
    """创建学习任务"""
    print(f"创建 {count} 个学习任务...")

    for i in range(count):
        media_items = []
        for j in range(3):  # 每个任务 3 个视频
            media_items.append({
                "media_uri": f"smb://nas/study/task_{i}/video_{j}.mp4",
                "media_name": f"第 {j + 1} 课",
                "duration": 1800 + j * 600  # 30-50 分钟
            })

        result = api_post("/study/tasks", {
            "name": f"学习任务 {i + 1}",
            "media_items": media_items
        })
        if "error" not in result and result.get("code") == 0:
            print(f"  创建学习任务 {i + 1}")
        else:
            print(f"  学习任务 {i + 1} 创建失败")

    print(f"完成: 已尝试创建 {count} 个学习任务")


def clear_all():
    """清空所有测试数据"""
    print("清空所有测试数据...")

    # 清空播放历史
    result = api_delete("/history")
    print(f"  清空播放历史: {result.get('message', 'unknown')}")

    # 获取并删除所有计划
    plans_result = api_get("/plans")
    if plans_result.get("code") == 0:
        plans = plans_result.get("data", {}).get("items", [])
        for plan in plans:
            api_delete(f"/plans/{plan['id']}")
        print(f"  删除 {len(plans)} 个计划")

    # 获取并删除所有设备
    devices_result = api_get("/devices")
    if devices_result.get("code") == 0:
        devices = devices_result.get("data", {}).get("items", [])
        for device in devices:
            api_delete(f"/devices/{device['id']}")
        print(f"  删除 {len(devices)} 个设备")

    # 获取并删除所有学习任务
    tasks_result = api_get("/study/tasks")
    if tasks_result.get("code") == 0:
        tasks = tasks_result.get("data", {}).get("items", [])
        for task in tasks:
            api_delete(f"/study/tasks/{task['id']}")
        print(f"  删除 {len(tasks)} 个学习任务")

    # 获取并删除所有 SMB 服务器
    smb_result = api_get("/smb/servers")
    if smb_result.get("code") == 0:
        servers = smb_result.get("data", {}).get("items", [])
        for server in servers:
            api_delete(f"/smb/servers/{server['id']}")
        print(f"  删除 {len(servers)} 个 SMB 服务器")

    print("完成: 已清空所有测试数据")


def show_status():
    """显示当前数据状态"""
    print("当前数据状态:")
    print("-" * 40)

    # 系统状态
    status = api_get("/system/status")
    if status.get("code") == 0:
        data = status.get("data", {})
        print(f"版本: {data.get('version', 'unknown')}")
        print(f"播放状态: {data.get('playback_status', 'unknown')}")

    # 计划数量
    plans = api_get("/plans")
    if plans.get("code") == 0:
        count = len(plans.get("data", {}).get("items", []))
        print(f"计划数量: {count}")

    # 设备数量
    devices = api_get("/devices")
    if devices.get("code") == 0:
        count = len(devices.get("data", {}).get("items", []))
        print(f"设备数量: {count}")

    # 历史数量
    history = api_get("/history")
    if history.get("code") == 0:
        count = history.get("data", {}).get("total", 0)
        print(f"历史记录: {count}")

    # 学习任务数量
    tasks = api_get("/study/tasks")
    if tasks.get("code") == 0:
        count = len(tasks.get("data", {}).get("items", []))
        print(f"学习任务: {count}")

    # SMB 服务器数量
    smb = api_get("/smb/servers")
    if smb.get("code") == 0:
        count = len(smb.get("data", {}).get("items", []))
        print(f"SMB 服务器: {count}")

    print("-" * 40)


def main():
    parser = argparse.ArgumentParser(
        description="TrunPlay 测试场景复现工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python reproduce_helper.py status
    python reproduce_helper.py setup-devices 5
    python reproduce_helper.py setup-plans 10
    python reproduce_helper.py clear-all
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # setup-devices
    p_devices = subparsers.add_parser("setup-devices", help="创建模拟设备")
    p_devices.add_argument("count", type=int, help="设备数量")

    # setup-plans
    p_plans = subparsers.add_parser("setup-plans", help="创建测试计划")
    p_plans.add_argument("count", type=int, help="计划数量")

    # setup-history
    p_history = subparsers.add_parser("setup-history", help="创建播放历史")
    p_history.add_argument("count", type=int, help="历史记录数量")

    # setup-study-tasks
    p_tasks = subparsers.add_parser("setup-study-tasks", help="创建学习任务")
    p_tasks.add_argument("count", type=int, help="任务数量")

    # clear-all
    subparsers.add_parser("clear-all", help="清空所有测试数据")

    # status
    subparsers.add_parser("status", help="显示当前数据状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "setup-devices":
        setup_devices(args.count)
    elif args.command == "setup-plans":
        setup_plans(args.count)
    elif args.command == "setup-history":
        setup_history(args.count)
    elif args.command == "setup-study-tasks":
        setup_study_tasks(args.count)
    elif args.command == "clear-all":
        confirm = input("确认清空所有数据? (y/N): ")
        if confirm.lower() == "y":
            clear_all()
        else:
            print("已取消")
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()
