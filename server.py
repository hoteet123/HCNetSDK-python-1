#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple alarm receiving server using HCNetSDK.

This script logs into configured cameras, sets up alarm channels,
and prints received alarms with camera number and alarm type.
"""

import time
from ctypes import byref, sizeof, POINTER, c_long
from loguru import logger

import HCNetSDK
from HCNetSDK import (
    NetClient,
    MSGCallBack_V31,
    NET_DVR_ALARMINFO_V30,
    NET_DVR_SETUPALARM_PARAM,
)


sdk = NetClient()
sdk.Init()
sdk.SetConnectTime(2000, 3)
sdk.SetReconnect(10000, True)
sdk.SetLogToFile(3)


# Alarm callback
def _alarm_callback(lCommand, pAlarmer, pAlarmInfo, dwBufLen, pUser):
    alarmer = pAlarmer.contents
    ip = bytes(alarmer.sDeviceIP).split(b"\x00", 1)[0].decode()
    info = POINTER(NET_DVR_ALARMINFO_V30).from_address(pAlarmInfo).contents
    channels = [i + 1 for i, v in enumerate(info.byChannel) if v == 1]
    logger.info(
        f"Alarm from {ip} Camera {channels} Type {info.dwAlarmType} Command {hex(lCommand)}"
    )
    return True


cb_func = MSGCallBack_V31(_alarm_callback)
sdk.SetDVRMessageCallBack_V31(cb_func, None)

# Camera configuration list
CAMERAS = [
    {
        "ip": "192.168.1.10",
        "port": 8000,
        "username": "admin",
        "password": "12345",
    },
]

alarm_handles = []

for cam in CAMERAS:
    uid, _ = sdk.Login_V40(cam["ip"], cam["port"], cam["username"], cam["password"])
    if uid < 0:
        logger.error(f"Login failed for {cam['ip']}")
        continue

    alarm_param = NET_DVR_SETUPALARM_PARAM()
    alarm_param.dwSize = sizeof(NET_DVR_SETUPALARM_PARAM)
    handle = sdk.SetupAlarmChan_V41(uid, alarm_param)
    if handle < 0:
        logger.error(f"Setup alarm failed for {cam['ip']}")
        sdk.Logout(uid)
        continue

    alarm_handles.append((uid, handle))
    logger.success(f"Alarm channel setup for {cam['ip']}")


try:
    logger.info("Alarm server started. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    for uid, handle in alarm_handles:
        sdk.CloseAlarmChan_V30(handle)
        sdk.Logout(uid)
    sdk.Cleanup()
