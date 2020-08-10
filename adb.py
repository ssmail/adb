# -*- coding: utf-8 -*-
# __author__ = 'hongkefeng'

import os
import re
import shlex
import subprocess
from threading import Timer
from time import sleep

from clog import SimpleLog


class ADB:
    """
    ADB Tool function library
    because all of the third python adb library not friendly,
    """
    __adb_cmd = "adb {device_id} {cmd}"
    __adb_shell_cmd = "adb {device_id} shell {cmd}"
    __adb_get_default_device = "get-serialno"
    __log = SimpleLog()

    def __init__(self, device_id="", debug=True):
        if device_id:
            self.device_id = "-s {device_id}".format(device_id=device_id)
        else:
            self.device_id = ""
        self.__debug = debug
        self.default_ime = self.get_current_ime()
        self.__log.info("current ime:" + self.default_ime)

    def cmd(self, cmd):
        """
        exec: adb -s $device_id $cmd
        Args:
            cmd: adb command content
        Returns:
            adb command line output
        """
        return self.exec_shell(self.__adb_cmd.format(device_id=self.device_id, cmd=cmd))

    def shell(self, cmd):
        """
        exec adb -s $device_id shell $cmd
        Args:
            cmd: adb shell command content
        Returns:
            adb command line output
        """
        return self.exec_shell(
            self.__adb_shell_cmd.format(device_id=self.device_id, cmd=cmd)
        )

    def __show_log(self, cmd):
        """
        if debug=True, all adb command line would be show in console output
        Args:
            cmd: adb shell command line
        Returns:
        """
        if self.__debug: self.__log.info("ADB:" + cmd)

    def exec_shell(self, cmd):
        """
        exec command line and return standard console output
        Args:
            cmd: command line detail
        Returns: stdout if stdout else stderr
        """
        self.__show_log(cmd)
        p = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p.wait()
        stdout = p.stdout.read().strip().decode("gbk")
        stderr = p.stderr.read().strip().decode("gbk")
        return stdout if stdout else stderr

    @staticmethod
    def get_local_device():
        """
        get device id if one android device connected
        Returns: android device id
        """
        return (
            subprocess.Popen(
                "adb get-serialno",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.read().strip().decode("utf-8")
        )

    def send_key_event(self, keycode):
        """
        send android system key event
        Args:
            keycode: Android key code, ref: https://developer.android.com/reference/android/view/KeyEvent
        Returns: None, no return
        """
        self.shell("input keyevent %s" % str(keycode))
        sleep(0.5)

    def swipe_down(self, height):
        """
        swipe down
        Args:
            height: swipe distance
        Returns: None
        """
        self.shell("input swipe 500 {height} 500 0".format(height=str(height)))

    def swipe_up(self, height):
        """
        swipe UP
        Args:
            height: swipe distance
        Returns: None
        """
        self.shell("input swipe 500 500 500 {height}".format(height=str(height + 500)))

    def swipe_left(self):
        """
        swipe left 500 pix
        Returns: None
        """
        self.shell("input swipe 500 500 0 500")

    def swipe_right(self):
        """
        swipe left 500 pix
        Returns: None
        """
        self.shell("input swipe 500 500 1000 500")

    def enable_ime(self):
        """
        install and set android keyboard as default IME
        Returns: None
        """
        self.install_adb_keyboard()
        self.shell("ime enable com.android.adbkeyboard/.AdbIME")
        self.shell("ime set com.android.adbkeyboard/.AdbIME")

    def get_current_ime(self):
        """
        get current ime package name
        Returns: None
        """
        return self.shell("settings get secure default_input_method")

    def recover_ime(self):
        """
        recover to original ime
        Returns: None
        """
        self.shell("ime set {}".format(self.default_ime))
        current_ime = self.get_current_ime()
        if current_ime == self.default_ime:
            self.__log.info("recover ime to {}".format(current_ime))
            return
        else:
            self.__log.error("recover ime failed")

    def send_text(self, text):
        """
        send text to android device.
        Args:
            text: text content
        Returns: None
        """
        input_text_shell = 'am broadcast -a ADB_INPUT_TEXT --es msg "{}'
        self.shell(
            input_text_shell.format(text.replace("&", "\&") + '"')
        )

    def entry_url(self, url):
        """
        entry android specific activity via url scheme protocol
        Args:
            url: url scheme, such as : weidianbuyer://wdb/account
        Returns: None
        """
        url_scheme_entry_prefix = "am start -a android.intent.action.VIEW -d {}"
        url = url.replace("&", "\&")
        if not url.startswith('"'):
            url = '"' + url + '"'
        self.shell(url_scheme_entry_prefix.format(url))

    def back_app(self, package_name):
        """
        Usage:
            if your test app is not activate at top activity, call
            this method can recover your test app to top activity.
        :param package_name:
        :return:
        """
        recover_app_to_top_monkey_shell = "monkey -p {} -c android.intent.category.LAUNCHER 1"
        self.shell(
            recover_app_to_top_monkey_shell.format(
                package=package_name
            )
        )

    @property
    def current_window(self):
        """
        get android device top activity info
        Returns: String, android top activity name
        """
        adb_dump_activity_shell = "dumpsys window |grep mFocusedWindow"
        return self.shell(adb_dump_activity_shell)

    def current_package(self):
        """
        get top app package name
        Returns: android device top app package name
        """
        adb_get_package_name = "dumpsys window windows | grep mCurrentFocus"
        package_text = self.shell(adb_get_package_name)
        return self.__clean_package_output(package_text)

    @staticmethod
    def __clean_package_output(text):
        new_text = text.replace("mCurrentFocus=", "").split(" ")[-1].strip()
        return new_text[:-1]

    def is_keyboard_active(self):
        """
        detect if keyboard is active status or not
        Returns: Boolean, True or False
        """
        adb_get_ime_status = 'dumpsys window InputMethod | grep "mHasSurface"'
        keyboard_text = self.shell(adb_get_ime_status)
        return keyboard_text.endswith("true")

    def get_connected_device_list(self):
        """
        get all connected devices
        Returns: a list of all connected devices
        """
        devices_text = self.exec_shell("adb devices")
        devices_name = re.findall(r"\b(\w+)\sdevice\b", devices_text)
        return devices_name

    def is_install_app(self, package_name):
        """
        detect android device has installed the app?
        Args:
            package_name: app package name
        Returns: if app has installed return string with format package:$package,
                 if not installed, return blank string.
        """
        return self.shell("pm list packages {}".format(package_name))

    def pull(self, source, target):
        """
        pull file from android device
        Args:
            source: android device file path
            target: local path
        Returns: None
        """
        self.cmd("pull {source} {target}".format(source=source, target=target))

    def push(self, source, target):
        """
        push local file to android device
        Args:
            source: local file path
            target: android device path
        Returns: None
        """
        self.cmd("push {source} {target}".format(source=source, target=target))

    def screenshot(self, image_path):
        """
        take a screen shot on android device, and pull it to local path
        Args:
            image_path: local image path
        Returns: None
        """
        scree_shot_shell = "screencap -p /data/local/tmp/screen_png"
        screen_shot_path = "/data/local/tmp/screen_png"
        self.shell(scree_shot_shell)
        self.pull(screen_shot_path, image_path)

    def clean_app_cache(self, package):
        """
        clean app cache
        Args:
            package: package name
        Returns:
        """
        adb_clear_package_cache = "pm clear {}"
        self.shell(adb_clear_package_cache.format(package))

    def get_app_version(self, package):
        """
        get app version number
        Args:
            package: app package name
        Returns:
        """
        adb_get_app_version_shell = "dumpsys package {} | grep versionName"
        return (
            self.shell(adb_get_app_version_shell.format(package))
                .replace("versionName=", "")
                .strip()
        )

    def install_adb_keyboard(self):
        """
        Usage:
            install adb keyboard ime, if not install this ime,
            download from uitest.daily.vdian.net file server and install
        :return:
        """
        adb_keyboard_url = "http://uitest.daily.vdian.net:8080/package/ADBKeyBoard.apk"
        adb_keyboard_package = "com.android.adbkeyboard"
        if not self.is_install_app(adb_keyboard_package):
            self.__log.info("adb keyboard has not installed")
            if not os.path.exists("ADBKeyBoard.apk"):
                self.__log.info("download ADBKeyBoard apk")
                os.system("wget " + adb_keyboard_url + " -q")
            self.cmd("install ADBKeyBoard.apk")
            if self.is_install_app(adb_keyboard_package):
                self.__log.info("install adb keyboard successfully")
                os.remove("ADBKeyBoard.apk")
            else:
                self.__log.critical("install adb keyboard failed")
        else:
            self.__log.info("adb keyboard successfully")

    def enable_wifi(self):
        self.__set_wifi("enablewifi")

    def disable_wifi(self):
        self.__set_wifi("disablewifi")

    def __set_wifi(self, status):
        """
        adb set wifi status
        Args:
            status: String, enablewifi or disablewifi
        Returns: None
        """
        adb_set_wifi_mode = 'am start -n com.example.chris.adbhelper/.MainActivity --es "msg" "{}"'
        self.shell(adb_set_wifi_mode.format(status))

    def press_back(self):
        """
        send key code BLACK to android device
        Returns: None
        """
        self.send_key_event(AndroidKeyCode.BACK)

    def press_home(self):
        """
        send key code HOME to android device
        Returns: None
        """
        self.send_key_event(AndroidKeyCode.HOME)

    def press_entry(self):
        """
        send key code ENTRY to android device
        Returns: None
        """
        self.send_key_event(AndroidKeyCode.ENTRY)

    def tap(self, x, y):
        """
        exec a tap event on android device location (x,y)
        Returns: None
        """
        self.shell("input tap {} {}".format(x, y))

    @staticmethod
    def run(cmd, timeout_sec=20):
        """
        exec cmd with timeout
        Args:
            cmd: cmd shell line
            timeout_sec: timeout value
        Returns: stdout if stdout else stderr
        """
        proc = subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        timer = Timer(timeout_sec, lambda p: p.kill(), [proc])
        try:
            timer.start()
            stdout, stderr = proc.communicate()
        finally:
            timer.cancel()
            return stdout if stdout else stderr


class AndroidKeyCode:
    HOME = 3
    BACK = 4
    ENTRY = 66


if __name__ == "__main__":
    adb = ADB()
    print(adb.get_app_version("com.koudai.weidian.buyer"))
    print(adb.current_package())
