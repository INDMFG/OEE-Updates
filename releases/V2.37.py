import gc
import lvgl as lv
import lv_utils
import tft_config
import gt911
from machine import Pin, I2C, RTC
import time

os = None
json = None
socket = None
ssl = None
network = None
ntptime = None
machine = None
binascii = None

time.sleep(3)

WIDTH = 800
HEIGHT = 480
RUN_PIN = 44
DEBOUNCE_MS = 50
MIN_CYCLE_SECONDS = 5
PPH_IGNORE_INITIAL_CYCLES = 3
PPH_DISPLAY_READY_CYCLES = 3
PPH_STOP_BEFORE_SHIFT_END_MINUTES = 30
DEFAULT_YEAR = 2026
DEFAULT_MONTH = 4
DEFAULT_DAY = 11
APP_VERSION = "V2.37"
BUTTON_FLASH_MS = 140
SAVE_INTERVAL_MS = 120000
STATE_FILE = "machine_oee_state.json"
CONFIG_FILE = "machine_oee_config.json"
WIFI_SSID = ""
WIFI_PASSWORD = ""
WIFI_TIMEOUT_MS = 15000
UPDATE_SERVER_URL = "https://raw.githubusercontent.com/INDMFG/OEE-Updates/main/ota_versions.json"
PARTS_RESET_HOLD_MS = 3000
GRAPH_RESET_HOLD_MS = 2000
OFF_SHIFT_CYCLE = "OFF"
BOOT_FLAG_FRAME_MS = 120
STARTUP_SPLASH_MS = 2600
UI_REFRESH_ACTIVE_MS = 250
UI_REFRESH_IDLE_MS = 1000
UI_REFRESH_SETTINGS_MS = 1000
GESTURE_COOLDOWN_MS = 250
MAIN_SCREEN_BUTTON_GUARD_MS = 450
DAILY_PRODUCTION_RESET_MINUTE = 9 * 60
DAILY_PRODUCTION_RESET_HOLD_MS = 2000
APP_RUNTIME_FILE = "app_runtime.py"
OTA_STAGED_FILE = "app_ota.py"
OTA_BACKUP_FILE = "app_previous.py"
OTA_MANIFEST_URL = UPDATE_SERVER_URL
STATS_REPO_OWNER = "INDMFG"
STATS_REPO_NAME = "Machine-Stats"
STATS_REPO_BRANCH = "main"
NOTES_REPO_OWNER = "INDMFG"
NOTES_REPO_NAME = "Notes"
NOTES_REPO_BRANCH = "main"
NOTES_TEXT_EXTENSIONS = (".txt", ".md", ".json", ".csv")
DEFAULT_MACHINE_OPTIONS = (
    {"id": "matsuura", "name": "Matsuura", "active": True},
    {"id": "doosan", "name": "Doosan", "active": False},
    {"id": "AS00", "name": "Nakamura", "active": False},
    {"id": "tap_arm", "name": "Tap Arm", "active": False},
    {"id": "x7_1", "name": "Syil X7 #1", "active": False},
    {"id": "x7_2", "name": "Syil X7 #2", "active": False},
    {"id": "taig", "name": "Taig", "active": False},
)
DEFAULT_STATS_MACHINE_ID = "matsuura"
DEFAULT_STATS_TOKEN_IMPORT_URL = ""
STATS_UPLOAD_INTERVAL_MS = 120000
BOOT_FLAG_WAVE = (0, 2, 5, 8, 10, 8, 5, 2, 0, -2, -5, -8, -10, -8, -5, -2)
BOOT_FLAG_VIEW_WIDTH = 220
BOOT_FLAG_VIEW_HEIGHT = 130
BOOT_FLAG_IMAGE_BASE_X = -10
startup_flag_asset = None
startup_flag_asset_error = None
TIME_OPTION_STEP_MINUTES = 30
DRAW_BUFFER_LINES = 32
SHIFT_NAMES = ("A", "B", "C")
DEFAULT_SHIFT_SETTINGS = {
    "A": {"enabled": True, "start": 9 * 60, "end": 13 * 60},
    "B": {"enabled": True, "start": 13 * 60, "end": 17 * 60},
    "C": {"enabled": True, "start": 17 * 60, "end": 8 * 60},
}


# =========================================================
# DISPLAY / TOUCH INIT
# =========================================================
backlight_pin = Pin(2, Pin.OUT)
backlight_pin.value(0)
time.sleep(0.15)
backlight_pin.value(1)
time.sleep(0.15)


def init_tft_with_retry():
    gc.collect()
    lv.init()
    gc.collect()
    last_error = None
    for attempt in range(2):
        try:
            return tft_config.config()
        except OSError as err:
            last_error = err
            if attempt == 0:
                print("Display init retry:", err)
                gc.collect()
                time.sleep(0.5)
            else:
                raise last_error
    raise last_error


tft = init_tft_with_retry()

i2c = I2C(1, scl=Pin(20), sda=Pin(19), freq=400000)
tp = gt911.GT911(i2c, width=WIDTH, height=HEIGHT)
tp.set_rotation(tp.ROTATION_INVERTED)

if not lv_utils.event_loop.is_running():
    lv_utils.event_loop()

disp_buf0 = lv.disp_draw_buf_t()
buf1_0 = bytearray(WIDTH * DRAW_BUFFER_LINES * lv.color_t.__SIZE__)
disp_buf0.init(buf1_0, None, len(buf1_0) // lv.color_t.__SIZE__)

disp_drv = lv.disp_drv_t()
disp_drv.init()
disp_drv.draw_buf = disp_buf0
disp_drv.flush_cb = tft.flush
disp_drv.hor_res = WIDTH
disp_drv.ver_res = HEIGHT
disp0 = disp_drv.register()
lv.disp_t.set_default(disp0)

indev_drv = lv.indev_drv_t()
indev_drv.init()
indev_drv.disp = disp0
indev_drv.type = lv.INDEV_TYPE.POINTER
indev_drv.read_cb = tp.lvgl_read
indev_drv.register()

dispp = lv.disp_get_default()
theme = lv.theme_default_init(
    dispp,
    lv.palette_main(lv.PALETTE.BLUE),
    lv.palette_main(lv.PALETTE.RED),
    False,
    lv.font_default(),
)
dispp.set_theme(theme)

try:
    import os as _os
    os = _os
except ImportError:
    os = None

try:
    import ujson as _json
except ImportError:
    import json as _json
json = _json

try:
    import usocket as _socket
except ImportError:
    try:
        import socket as _socket
    except ImportError:
        _socket = None
socket = _socket

try:
    import ussl as _ssl
except ImportError:
    try:
        import ssl as _ssl
    except ImportError:
        _ssl = None
ssl = _ssl

try:
    import network as _network
    import ntptime as _ntptime
except ImportError:
    _network = None
    _ntptime = None
network = _network
ntptime = _ntptime

try:
    import machine as _machine
except ImportError:
    _machine = None
machine = _machine

try:
    import ubinascii as _binascii
except ImportError:
    try:
        import binascii as _binascii
    except ImportError:
        _binascii = None
binascii = _binascii

gc.collect()

try:
    import startup_flag_asset as _startup_flag_asset
    startup_flag_asset = _startup_flag_asset
except Exception as err:
    startup_flag_asset = None
    startup_flag_asset_error = err
    print("Startup flag asset import fallback:", err)


# =========================================================
# SQUARELINE HELPERS
# =========================================================
def safe_font(name):
    return getattr(lv, name, lv.font_default())


def ui_theme_set(idx):
    return


def SetFlag(obj, flag, value):
    if value:
        obj.add_flag(flag)
    else:
        obj.clear_flag(flag)
    return


def SetBarProperty(target, prop_id, val):
    if prop_id == "Value_with_anim":
        target.set_value(val, lv.ANIM.ON)
    if prop_id == "Value":
        target.set_value(val, lv.ANIM.OFF)
    return


def set_arc_graph_style(arc, color_hex):
    arc.set_range(0, 100)
    arc.set_bg_angles(135, 45)
    arc.set_rotation(0)
    arc.set_value(0)
    arc.clear_flag(lv.obj.FLAG.CLICKABLE)
    arc.remove_style(None, lv.PART.KNOB)
    arc.set_style_arc_width(12, lv.PART.MAIN | lv.STATE.DEFAULT)
    arc.set_style_arc_width(12, lv.PART.INDICATOR | lv.STATE.DEFAULT)
    arc.set_style_arc_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
    arc.set_style_arc_color(lv.color_hex(color_hex), lv.PART.INDICATOR | lv.STATE.DEFAULT)
    arc.set_style_bg_opa(0, lv.PART.KNOB | lv.STATE.DEFAULT)
    arc.set_style_border_opa(0, lv.PART.KNOB | lv.STATE.DEFAULT)


def set_button_visual(btn, label, bg_color, border_color, text_color, border_width):
    btn.set_style_bg_color(lv.color_hex(bg_color), lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_border_color(lv.color_hex(border_color), lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_border_width(border_width, lv.PART.MAIN | lv.STATE.DEFAULT)
    label.set_style_text_color(lv.color_hex(text_color), lv.PART.MAIN | lv.STATE.DEFAULT)


def make_button(parent, text, x, y, w, h, color_hex):
    btn = lv.btn(parent)
    btn.set_width(w)
    btn.set_height(h)
    btn.align(lv.ALIGN.CENTER, x, y)
    btn.set_style_bg_color(lv.color_hex(color_hex), lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_button(btn)
    lbl = lv.label(btn)
    lbl.set_text(text)
    lbl.center()
    return btn


def stabilize_button(btn):
    SetFlag(btn, lv.obj.FLAG.SCROLL_ON_FOCUS, False)
    try:
        btn.clear_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
    except AttributeError:
        pass
    try:
        btn.set_style_anim_time(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_anim_time(0, lv.PART.MAIN | lv.STATE.PRESSED)
        btn.set_style_anim_time(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        btn.set_style_outline_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_outline_width(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        btn.set_style_outline_pad(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        btn.set_style_shadow_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_shadow_width(0, lv.PART.MAIN | lv.STATE.PRESSED)
        btn.set_style_shadow_width(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        btn.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.PRESSED)
        btn.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        btn.set_style_transform_width(0, lv.PART.MAIN | lv.STATE.PRESSED)
        btn.set_style_transform_height(0, lv.PART.MAIN | lv.STATE.PRESSED)
        btn.set_style_translate_x(0, lv.PART.MAIN | lv.STATE.PRESSED)
        btn.set_style_translate_y(0, lv.PART.MAIN | lv.STATE.PRESSED)
    except AttributeError:
        pass


def stabilize_widget(obj):
    try:
        SetFlag(obj, lv.obj.FLAG.SCROLL_ON_FOCUS, False)
    except Exception:
        pass
    for flag_name in ("SCROLL_CHAIN_HOR", "SCROLL_CHAIN_VER", "SCROLL_ELASTIC", "SCROLL_MOMENTUM"):
        try:
            obj.clear_flag(getattr(lv.obj.FLAG, flag_name))
        except Exception:
            pass
    try:
        obj.set_style_anim_time(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        obj.set_style_anim_time(0, lv.PART.MAIN | lv.STATE.PRESSED)
        obj.set_style_anim_time(0, lv.PART.MAIN | lv.STATE.FOCUSED)
    except Exception:
        pass
    try:
        obj.set_style_outline_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        obj.set_style_outline_opa(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        obj.set_style_outline_width(0, lv.PART.MAIN | lv.STATE.FOCUSED)
        obj.set_style_outline_pad(0, lv.PART.MAIN | lv.STATE.FOCUSED)
    except Exception:
        pass
    try:
        obj.set_style_translate_x(0, lv.PART.MAIN | lv.STATE.PRESSED)
        obj.set_style_translate_y(0, lv.PART.MAIN | lv.STATE.PRESSED)
        obj.set_style_transform_width(0, lv.PART.MAIN | lv.STATE.PRESSED)
        obj.set_style_transform_height(0, lv.PART.MAIN | lv.STATE.PRESSED)
    except Exception:
        pass


def stabilize_value_label(label, width, text_align=lv.TEXT_ALIGN.CENTER):
    label.set_width(width)
    label.set_style_text_align(text_align, lv.PART.MAIN | lv.STATE.DEFAULT)
    try:
        label.set_long_mode(lv.label.LONG.CLIP)
    except AttributeError:
        pass


# =========================================================
# STARTUP SPLASH
# =========================================================
startup_scr = lv.obj()
startup_scr.clear_flag(lv.obj.FLAG.SCROLLABLE)
stabilize_widget(startup_scr)
startup_scr.set_style_bg_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
startup_scr.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

startup_title = lv.label(startup_scr)
startup_title.set_text("MACHINE OEE")
startup_title.align(lv.ALIGN.CENTER, -150, -140)
startup_title.set_style_text_color(lv.color_hex(0x0C2D5B), lv.PART.MAIN | lv.STATE.DEFAULT)
startup_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

startup_note = lv.label(startup_scr)
startup_note.set_text("Starting up...")
startup_note.align(lv.ALIGN.CENTER, -150, -105)
startup_note.set_style_text_color(lv.color_hex(0x555555), lv.PART.MAIN | lv.STATE.DEFAULT)

startup_version_label = lv.label(startup_scr)
startup_version_label.set_text(APP_VERSION)
startup_version_label.align(lv.ALIGN.BOTTOM_RIGHT, -16, -12)
startup_version_label.set_style_text_color(lv.color_hex(0x7A7A7A), lv.PART.MAIN | lv.STATE.DEFAULT)


# =========================================================
# BOOT SCREEN
# =========================================================
boot_scr = lv.obj()
boot_scr.clear_flag(lv.obj.FLAG.SCROLLABLE)
stabilize_widget(boot_scr)
boot_scr.set_style_bg_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_scr.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

boot_title = lv.label(boot_scr)
boot_title.set_text("SET TIME")
boot_title.align(lv.ALIGN.CENTER, -150, -168)
boot_title.set_style_text_color(lv.color_hex(0x0C2D5B), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

boot_note = lv.label(boot_scr)
boot_note.set_text("Set hour and minute, then press OK")
boot_note.align(lv.ALIGN.CENTER, -150, -133)
boot_note.set_style_text_color(lv.color_hex(0x333333), lv.PART.MAIN | lv.STATE.DEFAULT)

boot_hour_title = lv.label(boot_scr)
boot_hour_title.set_text("HOUR")
boot_hour_title.align(lv.ALIGN.CENTER, -140, -40)
boot_hour_title.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_hour_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

boot_min_title = lv.label(boot_scr)
boot_min_title.set_text("MIN")
boot_min_title.align(lv.ALIGN.CENTER, 140, -40)
boot_min_title.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_min_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

boot_hour_value = lv.label(boot_scr)
boot_hour_value.set_text("12")
boot_hour_value.align(lv.ALIGN.CENTER, -140, 0)
boot_hour_value.set_style_text_color(lv.color_hex(0x1D1D1D), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_hour_value.set_style_text_font(safe_font("font_montserrat_30"), lv.PART.MAIN | lv.STATE.DEFAULT)

boot_min_value = lv.label(boot_scr)
boot_min_value.set_text("50")
boot_min_value.align(lv.ALIGN.CENTER, 140, 0)
boot_min_value.set_style_text_color(lv.color_hex(0x1D1D1D), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_min_value.set_style_text_font(safe_font("font_montserrat_30"), lv.PART.MAIN | lv.STATE.DEFAULT)

btn_hour_plus = make_button(boot_scr, "HOUR +", -140, 70, 130, 60, 0x04BE2D)
btn_hour_minus = make_button(boot_scr, "HOUR -", -140, 145, 130, 60, 0xC32331)
btn_min_plus = make_button(boot_scr, "MIN +", 140, 70, 130, 60, 0x465AC4)
btn_min_minus = make_button(boot_scr, "MIN -", 140, 145, 130, 60, 0xC32331)
btn_time_ok = make_button(boot_scr, "OK", 0, 220, 160, 70, 0xFCA903)

boot_flag_frame = lv.obj(startup_scr)
boot_flag_frame.set_size(250, 160)
boot_flag_frame.align(lv.ALIGN.CENTER, 220, -110)
boot_flag_frame.clear_flag(lv.obj.FLAG.SCROLLABLE)
boot_flag_frame.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag_frame.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag_frame.set_style_pad_all(0, lv.PART.MAIN | lv.STATE.DEFAULT)

boot_flag_pole = lv.obj(boot_flag_frame)
boot_flag_pole.set_size(8, 150)
boot_flag_pole.align(lv.ALIGN.LEFT_MID, 6, 0)
boot_flag_pole.clear_flag(lv.obj.FLAG.SCROLLABLE)
boot_flag_pole.set_style_radius(4, lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag_pole.set_style_bg_color(lv.color_hex(0x6E6E6E), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag_pole.set_style_border_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)

boot_flag = lv.obj(boot_flag_frame)
boot_flag.set_size(BOOT_FLAG_VIEW_WIDTH, BOOT_FLAG_VIEW_HEIGHT)
boot_flag.align(lv.ALIGN.LEFT_MID, 18, -8)
boot_flag.clear_flag(lv.obj.FLAG.SCROLLABLE)
boot_flag.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag.set_style_border_width(1, lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag.set_style_border_color(lv.color_hex(0xA0A0A0), lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
boot_flag.set_style_pad_all(0, lv.PART.MAIN | lv.STATE.DEFAULT)

boot_flag_stripes = []
boot_flag_union = None
boot_flag_stars = []
boot_flag_img = None
if startup_flag_asset is not None:
    try:
        boot_flag_img = lv.img(boot_flag)
        boot_flag_img.set_src(startup_flag_asset.get_startup_flag(lv.color_t.__SIZE__))
        boot_flag_img.set_pos(BOOT_FLAG_IMAGE_BASE_X, 0)
    except Exception as err:
        print("Startup flag asset fallback:", err)
        boot_flag_img = None
if boot_flag_img is None:
    startup_scr.set_style_bg_color(lv.color_hex(0x000000), lv.PART.MAIN | lv.STATE.DEFAULT)
    startup_title.add_flag(lv.obj.FLAG.HIDDEN)
    startup_note.add_flag(lv.obj.FLAG.HIDDEN)
    startup_version_label.add_flag(lv.obj.FLAG.HIDDEN)
    boot_flag_frame.add_flag(lv.obj.FLAG.HIDDEN)


# =========================================================
# V3 SQUARELINE UI
# =========================================================
ui____initial_actions0 = lv.obj()

ui_MAIN_SCREEN = lv.obj()
SetFlag(ui_MAIN_SCREEN, lv.obj.FLAG.SCROLLABLE, False)
stabilize_widget(ui_MAIN_SCREEN)
ui_MAIN_SCREEN.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_MAIN_SCREEN.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_SHIFT_A_BACKGROUND = lv.obj(ui_MAIN_SCREEN)
ui_SHIFT_A_BACKGROUND.set_width(200)
ui_SHIFT_A_BACKGROUND.set_height(150)
ui_SHIFT_A_BACKGROUND.set_x(-252)
ui_SHIFT_A_BACKGROUND.set_y(-135)
ui_SHIFT_A_BACKGROUND.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SHIFT_A_BACKGROUND, lv.obj.FLAG.SCROLLABLE, False)
ui_SHIFT_A_BACKGROUND.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_A_BACKGROUND.set_style_bg_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_A_BACKGROUND.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_A_BACKGROUND.set_style_border_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_A_BACKGROUND.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_SHIFT_B_BACKGROUND = lv.obj(ui_MAIN_SCREEN)
ui_SHIFT_B_BACKGROUND.set_width(200)
ui_SHIFT_B_BACKGROUND.set_height(150)
ui_SHIFT_B_BACKGROUND.set_x(7)
ui_SHIFT_B_BACKGROUND.set_y(-135)
ui_SHIFT_B_BACKGROUND.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SHIFT_B_BACKGROUND, lv.obj.FLAG.SCROLLABLE, False)
ui_SHIFT_B_BACKGROUND.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_B_BACKGROUND.set_style_bg_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_B_BACKGROUND.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_B_BACKGROUND.set_style_border_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_B_BACKGROUND.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_SHIFT_C_BACKGROUND = lv.obj(ui_MAIN_SCREEN)
ui_SHIFT_C_BACKGROUND.set_width(200)
ui_SHIFT_C_BACKGROUND.set_height(150)
ui_SHIFT_C_BACKGROUND.set_x(255)
ui_SHIFT_C_BACKGROUND.set_y(-132)
ui_SHIFT_C_BACKGROUND.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SHIFT_C_BACKGROUND, lv.obj.FLAG.SCROLLABLE, False)
ui_SHIFT_C_BACKGROUND.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_C_BACKGROUND.set_style_bg_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_C_BACKGROUND.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_C_BACKGROUND.set_style_border_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_C_BACKGROUND.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_SHIFT_A_GRAPH = lv.arc(ui_MAIN_SCREEN)
ui_SHIFT_A_GRAPH.set_width(150)
ui_SHIFT_A_GRAPH.set_height(144)
ui_SHIFT_A_GRAPH.set_x(-247)
ui_SHIFT_A_GRAPH.set_y(-124)
ui_SHIFT_A_GRAPH.set_align(lv.ALIGN.CENTER)
set_arc_graph_style(ui_SHIFT_A_GRAPH, 0x04BE2D)

ui_SHIFT_B_GRAPH = lv.arc(ui_MAIN_SCREEN)
ui_SHIFT_B_GRAPH.set_width(150)
ui_SHIFT_B_GRAPH.set_height(144)
ui_SHIFT_B_GRAPH.set_x(10)
ui_SHIFT_B_GRAPH.set_y(-124)
ui_SHIFT_B_GRAPH.set_align(lv.ALIGN.CENTER)
set_arc_graph_style(ui_SHIFT_B_GRAPH, 0xFCA903)

ui_SHIFT_C_GRAPH = lv.arc(ui_MAIN_SCREEN)
ui_SHIFT_C_GRAPH.set_width(150)
ui_SHIFT_C_GRAPH.set_height(144)
ui_SHIFT_C_GRAPH.set_x(261)
ui_SHIFT_C_GRAPH.set_y(-119)
ui_SHIFT_C_GRAPH.set_align(lv.ALIGN.CENTER)
set_arc_graph_style(ui_SHIFT_C_GRAPH, 0x465AC4)

ui_Shift_A_Lable = lv.label(ui_MAIN_SCREEN)
ui_Shift_A_Lable.set_text("SHIFT A\nPPH ")
ui_Shift_A_Lable.set_x(-249)
ui_Shift_A_Lable.set_y(-128)
ui_Shift_A_Lable.set_align(lv.ALIGN.CENTER)
ui_Shift_A_Lable.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Shift_A_Lable.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Shift_A_Lable.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Shift_B_Lable = lv.label(ui_MAIN_SCREEN)
ui_Shift_B_Lable.set_text("SHIFT B\nPPH ")
ui_Shift_B_Lable.set_x(8)
ui_Shift_B_Lable.set_y(-125)
ui_Shift_B_Lable.set_align(lv.ALIGN.CENTER)
ui_Shift_B_Lable.set_style_text_color(lv.color_hex(0xCC8E10), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Shift_B_Lable.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Shift_B_Lable.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Shift_C_Lable = lv.label(ui_MAIN_SCREEN)
ui_Shift_C_Lable.set_text("SHIFT C\nPPH ")
ui_Shift_C_Lable.set_x(260)
ui_Shift_C_Lable.set_y(-119)
ui_Shift_C_Lable.set_align(lv.ALIGN.CENTER)
ui_Shift_C_Lable.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Shift_C_Lable.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Shift_C_Lable.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_SHIFT_A_RESET_TOUCH = lv.btn(ui_MAIN_SCREEN)
ui_SHIFT_A_RESET_TOUCH.set_size(180, 150)
ui_SHIFT_A_RESET_TOUCH.set_x(-247)
ui_SHIFT_A_RESET_TOUCH.set_y(-124)
ui_SHIFT_A_RESET_TOUCH.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SHIFT_A_RESET_TOUCH, lv.obj.FLAG.SCROLLABLE, False)
ui_SHIFT_A_RESET_TOUCH.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_A_RESET_TOUCH.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_A_RESET_TOUCH.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_SHIFT_A_RESET_TOUCH)

ui_SHIFT_B_RESET_TOUCH = lv.btn(ui_MAIN_SCREEN)
ui_SHIFT_B_RESET_TOUCH.set_size(180, 150)
ui_SHIFT_B_RESET_TOUCH.set_x(10)
ui_SHIFT_B_RESET_TOUCH.set_y(-124)
ui_SHIFT_B_RESET_TOUCH.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SHIFT_B_RESET_TOUCH, lv.obj.FLAG.SCROLLABLE, False)
ui_SHIFT_B_RESET_TOUCH.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_B_RESET_TOUCH.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_B_RESET_TOUCH.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_SHIFT_B_RESET_TOUCH)

ui_SHIFT_C_RESET_TOUCH = lv.btn(ui_MAIN_SCREEN)
ui_SHIFT_C_RESET_TOUCH.set_size(180, 150)
ui_SHIFT_C_RESET_TOUCH.set_x(261)
ui_SHIFT_C_RESET_TOUCH.set_y(-119)
ui_SHIFT_C_RESET_TOUCH.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SHIFT_C_RESET_TOUCH, lv.obj.FLAG.SCROLLABLE, False)
ui_SHIFT_C_RESET_TOUCH.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_C_RESET_TOUCH.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SHIFT_C_RESET_TOUCH.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_SHIFT_C_RESET_TOUCH)

ui_Button1 = lv.btn(ui_MAIN_SCREEN)
ui_Button1.set_width(130)
ui_Button1.set_height(130)
ui_Button1.set_x(-314)
ui_Button1.set_y(160)
ui_Button1.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Button1, lv.obj.FLAG.SCROLLABLE, False)
ui_Button1.set_style_radius(125, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button1.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button1.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button1.set_style_border_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button1.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button1.set_style_border_width(8, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_Button1)

ui_GOOD_PART = lv.label(ui_MAIN_SCREEN)
ui_GOOD_PART.set_text("GOOD")
ui_GOOD_PART.set_x(-315)
ui_GOOD_PART.set_y(160)
ui_GOOD_PART.set_align(lv.ALIGN.CENTER)
ui_GOOD_PART.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_GOOD_PART.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_GOOD_PART.set_style_text_font(safe_font("font_montserrat_30"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Button2 = lv.btn(ui_MAIN_SCREEN)
ui_Button2.set_width(130)
ui_Button2.set_height(130)
ui_Button2.set_x(316)
ui_Button2.set_y(167)
ui_Button2.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Button2, lv.obj.FLAG.SCROLLABLE, False)
ui_Button2.set_style_radius(125, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button2.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button2.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button2.set_style_border_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button2.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Button2.set_style_border_width(8, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_Button2)

ui_GOOD_PART1 = lv.label(ui_MAIN_SCREEN)
ui_GOOD_PART1.set_text("BAD")
ui_GOOD_PART1.set_x(317)
ui_GOOD_PART1.set_y(169)
ui_GOOD_PART1.set_align(lv.ALIGN.CENTER)
ui_GOOD_PART1.set_style_text_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_GOOD_PART1.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_GOOD_PART1.set_style_text_font(safe_font("font_montserrat_30"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_PPH_GOAL_NUMBER_A = lv.label(ui_MAIN_SCREEN)
ui_PPH_GOAL_NUMBER_A.set_text("0")
ui_PPH_GOAL_NUMBER_A.set_x(-252)
ui_PPH_GOAL_NUMBER_A.set_y(-77)
ui_PPH_GOAL_NUMBER_A.set_align(lv.ALIGN.CENTER)
ui_PPH_GOAL_NUMBER_A.set_style_text_color(lv.color_hex(0x04BD2D), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_PPH_GOAL_NUMBER_A, 72)

ui_PPH_GOAL_NUMBER_B = lv.label(ui_MAIN_SCREEN)
ui_PPH_GOAL_NUMBER_B.set_text("0")
ui_PPH_GOAL_NUMBER_B.set_x(6)
ui_PPH_GOAL_NUMBER_B.set_y(-74)
ui_PPH_GOAL_NUMBER_B.set_align(lv.ALIGN.CENTER)
ui_PPH_GOAL_NUMBER_B.set_style_text_color(lv.color_hex(0xAD7C1B), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_PPH_GOAL_NUMBER_B, 72)

ui_PPH_GOAL_NUMBER_C = lv.label(ui_MAIN_SCREEN)
ui_PPH_GOAL_NUMBER_C.set_text("0")
ui_PPH_GOAL_NUMBER_C.set_x(258)
ui_PPH_GOAL_NUMBER_C.set_y(-72)
ui_PPH_GOAL_NUMBER_C.set_align(lv.ALIGN.CENTER)
ui_PPH_GOAL_NUMBER_C.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_PPH_GOAL_NUMBER_C, 72)

ui_Panel2 = lv.obj(ui_MAIN_SCREEN)
ui_Panel2.set_width(394)
ui_Panel2.set_height(69)
ui_Panel2.set_x(0)
ui_Panel2.set_y(166)
ui_Panel2.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Panel2, lv.obj.FLAG.SCROLLABLE, False)
ui_Panel2.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Panel2.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Panel2.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Panel2.set_style_border_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Panel2.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Panel2.set_style_border_width(6, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Label5 = lv.label(ui_MAIN_SCREEN)
ui_Label5.set_text("Good Count:")
ui_Label5.set_x(-132)
ui_Label5.set_y(168)
ui_Label5.set_align(lv.ALIGN.CENTER)
ui_Label5.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Good_Label_Reset_Touch = lv.btn(ui_MAIN_SCREEN)
ui_Good_Label_Reset_Touch.set_size(132, 38)
ui_Good_Label_Reset_Touch.set_x(-132)
ui_Good_Label_Reset_Touch.set_y(168)
ui_Good_Label_Reset_Touch.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Good_Label_Reset_Touch, lv.obj.FLAG.SCROLLABLE, False)
ui_Good_Label_Reset_Touch.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Good_Label_Reset_Touch.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Good_Label_Reset_Touch.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_Good_Label_Reset_Touch)

ui_Good_Count_bar = lv.label(ui_MAIN_SCREEN)
ui_Good_Count_bar.set_text("0")
ui_Good_Count_bar.set_x(-72)
ui_Good_Count_bar.set_y(168)
ui_Good_Count_bar.set_align(lv.ALIGN.CENTER)
ui_Good_Count_bar.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_Good_Count_bar, 58, lv.TEXT_ALIGN.RIGHT)

ui_Good_Count_Edit = lv.btn(ui_MAIN_SCREEN)
ui_Good_Count_Edit.set_size(60, 38)
ui_Good_Count_Edit.set_x(-72)
ui_Good_Count_Edit.set_y(168)
ui_Good_Count_Edit.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Good_Count_Edit, lv.obj.FLAG.SCROLLABLE, False)
ui_Good_Count_Edit.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Good_Count_Edit.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Good_Count_Edit.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_Good_Count_Edit)

ui_Label7 = lv.label(ui_MAIN_SCREEN)
ui_Label7.set_text("Bad Count:")
ui_Label7.set_x(15)
ui_Label7.set_y(167)
ui_Label7.set_align(lv.ALIGN.CENTER)
ui_Label7.set_style_text_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Bad_Label_Reset_Touch = lv.btn(ui_MAIN_SCREEN)
ui_Bad_Label_Reset_Touch.set_size(118, 38)
ui_Bad_Label_Reset_Touch.set_x(15)
ui_Bad_Label_Reset_Touch.set_y(167)
ui_Bad_Label_Reset_Touch.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Bad_Label_Reset_Touch, lv.obj.FLAG.SCROLLABLE, False)
ui_Bad_Label_Reset_Touch.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Bad_Label_Reset_Touch.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Bad_Label_Reset_Touch.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_Bad_Label_Reset_Touch)

ui_Label8 = lv.label(ui_MAIN_SCREEN)
ui_Label8.set_text("0")
ui_Label8.set_x(62)
ui_Label8.set_y(167)
ui_Label8.set_align(lv.ALIGN.CENTER)
ui_Label8.set_style_text_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_Label8, 48, lv.TEXT_ALIGN.RIGHT)

ui_Bad_Count_Edit = lv.btn(ui_MAIN_SCREEN)
ui_Bad_Count_Edit.set_size(52, 38)
ui_Bad_Count_Edit.set_x(62)
ui_Bad_Count_Edit.set_y(167)
ui_Bad_Count_Edit.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Bad_Count_Edit, lv.obj.FLAG.SCROLLABLE, False)
ui_Bad_Count_Edit.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Bad_Count_Edit.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Bad_Count_Edit.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(ui_Bad_Count_Edit)

ui_Label9 = lv.label(ui_MAIN_SCREEN)
ui_Label9.set_text("%:")
ui_Label9.set_x(108)
ui_Label9.set_y(166)
ui_Label9.set_align(lv.ALIGN.CENTER)
ui_Label9.set_style_text_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_BAD_PARTS_PRC = lv.label(ui_MAIN_SCREEN)
ui_BAD_PARTS_PRC.set_text("0.0")
ui_BAD_PARTS_PRC.set_x(128)
ui_BAD_PARTS_PRC.set_y(166)
ui_BAD_PARTS_PRC.set_align(lv.ALIGN.CENTER)
ui_BAD_PARTS_PRC.set_style_text_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_BAD_PARTS_PRC, 56, lv.TEXT_ALIGN.RIGHT)

ui_SETTING_BUTTON = lv.btn(ui_MAIN_SCREEN)
ui_SETTING_BUTTON.set_width(38)
ui_SETTING_BUTTON.set_height(35)
ui_SETTING_BUTTON.set_x(376)
ui_SETTING_BUTTON.set_y(-222)
ui_SETTING_BUTTON.set_align(lv.ALIGN.CENTER)
SetFlag(ui_SETTING_BUTTON, lv.obj.FLAG.SCROLLABLE, False)
stabilize_button(ui_SETTING_BUTTON)
ui_SETTING_BUTTON.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SETTING_BUTTON.set_style_bg_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SETTING_BUTTON.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SETTING_BUTTON.set_style_border_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Label11 = lv.label(ui_MAIN_SCREEN)
ui_Label11.set_text("SET")
ui_Label11.set_x(375)
ui_Label11.set_y(-223)
ui_Label11.set_align(lv.ALIGN.CENTER)
ui_Label11.set_style_text_color(lv.color_hex(0xE39B0A), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_NOTE_BUTTON = lv.btn(ui_MAIN_SCREEN)
ui_NOTE_BUTTON.set_width(50)
ui_NOTE_BUTTON.set_height(35)
ui_NOTE_BUTTON.set_x(-374)
ui_NOTE_BUTTON.set_y(-222)
ui_NOTE_BUTTON.set_align(lv.ALIGN.CENTER)
SetFlag(ui_NOTE_BUTTON, lv.obj.FLAG.SCROLLABLE, False)
stabilize_button(ui_NOTE_BUTTON)
ui_NOTE_BUTTON.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_NOTE_BUTTON.set_style_bg_color(lv.color_hex(0x444242), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_NOTE_BUTTON.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_NOTE_BUTTON.set_style_border_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_NOTE_LABEL = lv.label(ui_MAIN_SCREEN)
ui_NOTE_LABEL.set_text("NOTE")
ui_NOTE_LABEL.set_x(-374)
ui_NOTE_LABEL.set_y(-223)
ui_NOTE_LABEL.set_align(lv.ALIGN.CENTER)
ui_NOTE_LABEL.set_style_text_color(lv.color_hex(0xCFCFCF), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_PPH_GOAL_SETTING = lv.btn(ui_MAIN_SCREEN)
ui_PPH_GOAL_SETTING.set_width(92)
ui_PPH_GOAL_SETTING.set_height(62)
ui_PPH_GOAL_SETTING.set_x(2)
ui_PPH_GOAL_SETTING.set_y(-11)
ui_PPH_GOAL_SETTING.set_align(lv.ALIGN.CENTER)
SetFlag(ui_PPH_GOAL_SETTING, lv.obj.FLAG.SCROLLABLE, False)
stabilize_button(ui_PPH_GOAL_SETTING)
ui_PPH_GOAL_SETTING.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_PPH_GOAL_SETTING.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_PPH_GOAL_SETTING.set_style_border_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_PPH_GOAL_SETTING.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_PPH_GOAL_SETTING.set_style_border_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_PPH_GOAL_SETTING.set_style_shadow_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_PPH_GOAL_SETTING.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Label12 = lv.label(ui_MAIN_SCREEN)
ui_Label12.set_text("PPH Goal")
ui_Label12.set_x(2)
ui_Label12.set_y(-23)
ui_Label12.set_align(lv.ALIGN.CENTER)
ui_Label12.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Label12.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_PPH_GOAL_NUMBER = lv.label(ui_MAIN_SCREEN)
ui_PPH_GOAL_NUMBER.set_text("100")
ui_PPH_GOAL_NUMBER.set_x(2)
ui_PPH_GOAL_NUMBER.set_y(-1)
ui_PPH_GOAL_NUMBER.set_align(lv.ALIGN.CENTER)
ui_PPH_GOAL_NUMBER.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_PPH_GOAL_NUMBER, 96)

ui_Label14 = lv.label(ui_MAIN_SCREEN)
ui_Label14.set_text("Cycle Time W/Load")
ui_Label14.set_x(-257)
ui_Label14.set_y(-20)
ui_Label14.set_align(lv.ALIGN.CENTER)
ui_Label14.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Label14.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_with_load_cycle_current = lv.label(ui_MAIN_SCREEN)
ui_with_load_cycle_current.set_text("0m 0s")
ui_with_load_cycle_current.set_x(-262)
ui_with_load_cycle_current.set_y(7)
ui_with_load_cycle_current.set_align(lv.ALIGN.CENTER)
ui_with_load_cycle_current.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_with_load_cycle_current, 170)

ui_AVARAGE_CYCLE_TIME_W_LOAD = lv.label(ui_MAIN_SCREEN)
ui_AVARAGE_CYCLE_TIME_W_LOAD.set_text("AVRG W/LOAD")
ui_AVARAGE_CYCLE_TIME_W_LOAD.set_x(-259)
ui_AVARAGE_CYCLE_TIME_W_LOAD.set_y(48)
ui_AVARAGE_CYCLE_TIME_W_LOAD.set_align(lv.ALIGN.CENTER)
ui_AVARAGE_CYCLE_TIME_W_LOAD.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_AVARAGE_CYCLE_TIME_W_LOAD.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_AVRG_W_LOAD_TIME = lv.label(ui_MAIN_SCREEN)
ui_AVRG_W_LOAD_TIME.set_text("0m 0s")
ui_AVRG_W_LOAD_TIME.set_x(-262)
ui_AVRG_W_LOAD_TIME.set_y(76)
ui_AVRG_W_LOAD_TIME.set_align(lv.ALIGN.CENTER)
ui_AVRG_W_LOAD_TIME.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_AVRG_W_LOAD_TIME, 170)

ui_Load_Time_Lable = lv.label(ui_MAIN_SCREEN)
ui_Load_Time_Lable.set_text("AVRG LOAD TIME")
ui_Load_Time_Lable.set_x(0)
ui_Load_Time_Lable.set_y(42)
ui_Load_Time_Lable.set_align(lv.ALIGN.CENTER)
ui_Load_Time_Lable.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Load_Time_Lable.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_AVRG_LOAD_TIME_NUMBER = lv.label(ui_MAIN_SCREEN)
ui_AVRG_LOAD_TIME_NUMBER.set_text("0m 0s")
ui_AVRG_LOAD_TIME_NUMBER.set_x(2)
ui_AVRG_LOAD_TIME_NUMBER.set_y(72)
ui_AVRG_LOAD_TIME_NUMBER.set_align(lv.ALIGN.CENTER)
ui_AVRG_LOAD_TIME_NUMBER.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_AVRG_LOAD_TIME_NUMBER, 170)

ui_AVRG_IDLE_TIME_LABLE = lv.label(ui_MAIN_SCREEN)
ui_AVRG_IDLE_TIME_LABLE.set_text("AVRG IDLE TIME")
ui_AVRG_IDLE_TIME_LABLE.set_x(259)
ui_AVRG_IDLE_TIME_LABLE.set_y(43)
ui_AVRG_IDLE_TIME_LABLE.set_align(lv.ALIGN.CENTER)
ui_AVRG_IDLE_TIME_LABLE.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_AVRG_IDLE_TIME_LABLE.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_AVRG_IDLE_TIME_NUMBER = lv.label(ui_MAIN_SCREEN)
ui_AVRG_IDLE_TIME_NUMBER.set_text("0m 0s")
ui_AVRG_IDLE_TIME_NUMBER.set_x(258)
ui_AVRG_IDLE_TIME_NUMBER.set_y(69)
ui_AVRG_IDLE_TIME_NUMBER.set_align(lv.ALIGN.CENTER)
ui_AVRG_IDLE_TIME_NUMBER.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_AVRG_IDLE_TIME_NUMBER, 170)

ui_cycle_time = lv.label(ui_MAIN_SCREEN)
ui_cycle_time.set_text("Machine Cycle Time")
ui_cycle_time.set_x(258)
ui_cycle_time.set_y(-13)
ui_cycle_time.set_align(lv.ALIGN.CENTER)
ui_cycle_time.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_machine_cycle_time = lv.label(ui_MAIN_SCREEN)
ui_machine_cycle_time.set_text("0m 0s")
ui_machine_cycle_time.set_x(257)
ui_machine_cycle_time.set_y(12)
ui_machine_cycle_time.set_align(lv.ALIGN.CENTER)
ui_machine_cycle_time.set_style_text_color(lv.color_hex(0x465AC4), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_machine_cycle_time, 170)

ui_SETTINGS = lv.obj()
ui_Shift_Data_Screen = ui_SETTINGS
SetFlag(ui_SETTINGS, lv.obj.FLAG.SCROLLABLE, False)
stabilize_widget(ui_SETTINGS)
ui_SETTINGS.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SETTINGS.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

stats_hint = lv.label(ui_SETTINGS)
stats_hint.set_text("Swipe right to return")
stats_hint.align(lv.ALIGN.TOP_MID, 0, 8)
stats_hint.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)


def make_shift_data_box(parent, title_text, x, title_y, box_y, border_color):
    box = lv.obj(parent)
    box.set_width(175)
    box.set_height(260)
    box.set_x(x)
    box.set_y(box_y)
    box.set_align(lv.ALIGN.CENTER)
    SetFlag(box, lv.obj.FLAG.SCROLLABLE, False)
    box.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
    box.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
    box.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    box.set_style_border_color(lv.color_hex(border_color), lv.PART.MAIN | lv.STATE.DEFAULT)
    box.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    box.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)

    title_lbl = lv.label(parent)
    title_lbl.set_text(title_text)
    title_lbl.set_x(x)
    title_lbl.set_y(title_y)
    title_lbl.set_align(lv.ALIGN.CENTER)
    title_lbl.set_style_text_color(lv.color_hex(border_color), lv.PART.MAIN | lv.STATE.DEFAULT)
    title_lbl.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    good_lbl = lv.label(box)
    good_lbl.set_text("Good: 0")
    good_lbl.align(lv.ALIGN.TOP_LEFT, 12, 16)
    good_lbl.set_style_text_color(lv.color_hex(0x04BE2D), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(good_lbl, 150, lv.TEXT_ALIGN.LEFT)

    bad_lbl = lv.label(box)
    bad_lbl.set_text("Bad: 0")
    bad_lbl.align(lv.ALIGN.TOP_LEFT, 12, 48)
    bad_lbl.set_style_text_color(lv.color_hex(0xC32331), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(bad_lbl, 150, lv.TEXT_ALIGN.LEFT)

    total_lbl = lv.label(box)
    total_lbl.set_text("Cycles: 0")
    total_lbl.align(lv.ALIGN.TOP_LEFT, 12, 80)
    total_lbl.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(total_lbl, 150, lv.TEXT_ALIGN.LEFT)

    avg_title_lbl = lv.label(box)
    avg_title_lbl.set_text("Avg W/Load:")
    avg_title_lbl.align(lv.ALIGN.TOP_LEFT, 12, 116)
    avg_title_lbl.set_style_text_color(lv.color_hex(border_color), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(avg_title_lbl, 150, lv.TEXT_ALIGN.LEFT)

    avg_value_lbl = lv.label(box)
    avg_value_lbl.set_text("0m 0s")
    avg_value_lbl.align(lv.ALIGN.TOP_LEFT, 12, 144)
    avg_value_lbl.set_style_text_color(lv.color_hex(border_color), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(avg_value_lbl, 150, lv.TEXT_ALIGN.LEFT)

    pph_lbl = lv.label(box)
    pph_lbl.set_text("PPH: 0")
    pph_lbl.align(lv.ALIGN.TOP_LEFT, 12, 194)
    pph_lbl.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(pph_lbl, 150, lv.TEXT_ALIGN.LEFT)

    return box, title_lbl, {
        "good": good_lbl,
        "bad": bad_lbl,
        "total": total_lbl,
        "avg_title": avg_title_lbl,
        "avg_value": avg_value_lbl,
        "pph": pph_lbl,
    }


ui_Shift_Data_A, ui_Shift_A_Text, stats_box_a_info = make_shift_data_box(
    ui_SETTINGS, "Shift A Data", -270, -197, -51, 0x2DA041
)
ui_Shift_Data_B, ui_Shift_B_Text, stats_box_b_info = make_shift_data_box(
    ui_SETTINGS, "Shift B Data", 0, -196, -50, 0xFCA903
)
ui_Shift_Data_C, ui_Shift_C_Text, stats_box_c_info = make_shift_data_box(
    ui_SETTINGS, "Shift C Data", 264, -195, -50, 0x465AC4
)

ui_Daily_Parts_Count = lv.obj(ui_SETTINGS)
ui_Daily_Parts_Count.set_width(272)
ui_Daily_Parts_Count.set_height(50)
ui_Daily_Parts_Count.set_x(1)
ui_Daily_Parts_Count.set_y(155)
ui_Daily_Parts_Count.set_align(lv.ALIGN.CENTER)
SetFlag(ui_Daily_Parts_Count, lv.obj.FLAG.SCROLLABLE, False)
ui_Daily_Parts_Count.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Daily_Parts_Count.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Daily_Parts_Count.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Daily_Parts_Count.set_style_border_color(lv.color_hex(0x030000), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Daily_Parts_Count.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
ui_Daily_Parts_Count.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Total_Parts_Today_Lable = lv.label(ui_SETTINGS)
ui_Total_Parts_Today_Lable.set_text("Total Daily Production:")
ui_Total_Parts_Today_Lable.set_x(-36)
ui_Total_Parts_Today_Lable.set_y(156)
ui_Total_Parts_Today_Lable.set_align(lv.ALIGN.CENTER)
ui_Total_Parts_Today_Lable.set_style_text_color(lv.color_hex(0x2DA041), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_Total_Parts_Today_Lable, 190, lv.TEXT_ALIGN.LEFT)

ui_Total_Daily_Production = lv.label(ui_SETTINGS)
ui_Total_Daily_Production.set_text("0")
ui_Total_Daily_Production.set_x(86)
ui_Total_Daily_Production.set_y(156)
ui_Total_Daily_Production.set_align(lv.ALIGN.CENTER)
ui_Total_Daily_Production.set_style_text_color(lv.color_hex(0x2D9840), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_Total_Daily_Production, 64, lv.TEXT_ALIGN.RIGHT)

stats_daily_reset_touch = lv.btn(ui_SETTINGS)
stats_daily_reset_touch.set_width(272)
stats_daily_reset_touch.set_height(50)
stats_daily_reset_touch.set_x(1)
stats_daily_reset_touch.set_y(155)
stats_daily_reset_touch.set_align(lv.ALIGN.CENTER)
SetFlag(stats_daily_reset_touch, lv.obj.FLAG.SCROLLABLE, False)
stats_daily_reset_touch.set_style_bg_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stats_daily_reset_touch.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stats_daily_reset_touch.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_button(stats_daily_reset_touch)

stats_reset_status = lv.label(ui_SETTINGS)
stats_reset_status.set_text("")
stats_reset_status.align(lv.ALIGN.BOTTOM_MID, 0, -16)
stats_reset_status.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(stats_reset_status, 250, lv.TEXT_ALIGN.CENTER)

stats_version_label = lv.label(ui_SETTINGS)
stats_version_label.set_text(APP_VERSION)
stats_version_label.align(lv.ALIGN.BOTTOM_RIGHT, -16, -58)
stats_version_label.set_style_text_color(lv.color_hex(0x7A7A7A), lv.PART.MAIN | lv.STATE.DEFAULT)

stats_widgets = {
    "A": stats_box_a_info,
    "B": stats_box_b_info,
    "C": stats_box_c_info,
}

notes_overlay = lv.obj(ui_SETTINGS)
notes_overlay.set_size(WIDTH, HEIGHT)
notes_overlay.align(lv.ALIGN.CENTER, 0, 0)
SetFlag(notes_overlay, lv.obj.FLAG.SCROLLABLE, False)
stabilize_widget(notes_overlay)
notes_overlay.set_style_radius(0, lv.PART.MAIN | lv.STATE.DEFAULT)
notes_overlay.set_style_bg_color(lv.color_hex(0x181818), lv.PART.MAIN | lv.STATE.DEFAULT)
notes_overlay.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
notes_overlay.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
SetFlag(notes_overlay, lv.obj.FLAG.HIDDEN, True)

notes_title_label = lv.label(notes_overlay)
notes_title_label.set_text("NOTES")
notes_title_label.align(lv.ALIGN.TOP_MID, 0, 18)
notes_title_label.set_style_text_color(lv.color_hex(0xF0F0F0), lv.PART.MAIN | lv.STATE.DEFAULT)
notes_title_label.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(notes_title_label, 620, lv.TEXT_ALIGN.CENTER)

notes_page_label = lv.label(notes_overlay)
notes_page_label.set_text("")
notes_page_label.align(lv.ALIGN.TOP_RIGHT, -18, 22)
notes_page_label.set_style_text_color(lv.color_hex(0xA0A0A0), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(notes_page_label, 90, lv.TEXT_ALIGN.RIGHT)

notes_body_label = lv.label(notes_overlay)
notes_body_label.set_text("")
notes_body_label.set_width(730)
notes_body_label.set_long_mode(lv.label.LONG.WRAP)
notes_body_label.align(lv.ALIGN.TOP_LEFT, 32, 64)
notes_body_label.set_style_text_color(lv.color_hex(0xF7F7F7), lv.PART.MAIN | lv.STATE.DEFAULT)
notes_body_label.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)
notes_body_label.set_style_text_line_space(6, lv.PART.MAIN | lv.STATE.DEFAULT)

notes_status_label = lv.label(notes_overlay)
notes_status_label.set_text("")
notes_status_label.align(lv.ALIGN.BOTTOM_MID, 0, -16)
notes_status_label.set_style_text_color(lv.color_hex(0x9C9C9C), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(notes_status_label, 680, lv.TEXT_ALIGN.CENTER)

notes_main_button = lv.btn(notes_overlay)
notes_main_button.set_size(42, 42)
notes_main_button.align(lv.ALIGN.BOTTOM_LEFT, 12, -12)
SetFlag(notes_main_button, lv.obj.FLAG.SCROLLABLE, False)
stabilize_button(notes_main_button)
notes_main_button.set_style_bg_color(lv.color_hex(0x7A7A7A), lv.PART.MAIN | lv.STATE.DEFAULT)
notes_main_button.set_style_bg_opa(191, lv.PART.MAIN | lv.STATE.DEFAULT)
notes_main_button.set_style_border_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)
notes_main_button.set_style_shadow_opa(0, lv.PART.MAIN | lv.STATE.DEFAULT)

notes_main_button_label = lv.label(notes_main_button)
notes_main_button_label.set_text("MAIN")
notes_main_button_label.center()
notes_main_button_label.set_style_text_color(lv.color_hex(0xE8E8E8), lv.PART.MAIN | lv.STATE.DEFAULT)


# =========================================================
# SETTINGS MENU SCREEN
# =========================================================
ui_SETTINGS_MENU = lv.obj()
SetFlag(ui_SETTINGS_MENU, lv.obj.FLAG.SCROLLABLE, False)
stabilize_widget(ui_SETTINGS_MENU)
ui_SETTINGS_MENU.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
ui_SETTINGS_MENU.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

settings_menu_title = lv.label(ui_SETTINGS_MENU)
settings_menu_title.set_text("SETTINGS")
settings_menu_title.align(lv.ALIGN.TOP_MID, 0, 20)
settings_menu_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
settings_menu_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

settings_menu_hint = lv.label(ui_SETTINGS_MENU)
settings_menu_hint.set_text("Swipe right to return")
settings_menu_hint.align(lv.ALIGN.TOP_MID, 0, 52)
settings_menu_hint.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)


def make_settings_button(parent, text, x, y):
    btn = lv.btn(parent)
    btn.set_width(136)
    btn.set_height(50)
    btn.set_x(x)
    btn.set_y(y)
    btn.set_align(lv.ALIGN.CENTER)
    SetFlag(btn, lv.obj.FLAG.SCROLLABLE, False)
    stabilize_button(btn)
    btn.set_style_bg_color(lv.color_hex(0x313030), lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_border_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    btn.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    lbl = lv.label(btn)
    lbl.set_text(text)
    lbl.center()
    lbl.set_style_text_color(lv.color_hex(0x2DA041), lv.PART.MAIN | lv.STATE.DEFAULT)
    return btn, lbl


ui_WiFi_Settings, ui_WiFi_Settings_Text = make_settings_button(ui_SETTINGS_MENU, "WiFi Settings", -303, -150)
ui_Shift_Hours_Settings, ui_Shift_Hours_Text = make_settings_button(ui_SETTINGS_MENU, "Shift Hours", 6, -150)
ui_Parts_Per_Cycle, ui_Parts_Per_Cycle_Text = make_settings_button(ui_SETTINGS_MENU, "Parts Per Cycle", 303, -150)
ui_Invert_Cycle_Start_IO, ui_Invert_Cycle_Start_IO_Text = make_settings_button(ui_SETTINGS_MENU, "Cycle Start Invert", -303, -39)
ui_Reset_Rules, ui_Reset_Rules_Text = make_settings_button(ui_SETTINGS_MENU, "Reset Rules", 4, -39)
ui_IO_Check, ui_IO_Check_Text = make_settings_button(ui_SETTINGS_MENU, "IO Check", 301, -39)
ui_Door_Switch_Enable_Button, ui_Door_Switch_Enable_Lable = make_settings_button(ui_SETTINGS_MENU, "Door Switch\nOFF", -303, 72)
ui_Software_Update, ui_Software_Update_Text = make_settings_button(ui_SETTINGS_MENU, "Software\nUpdate", 0, 72)
ui_Reset_Shift_Data_Lock_Button, ui_Shift_Data_Reset_Lock_Text = make_settings_button(
    ui_SETTINGS_MENU,
    "Shift Reset\nUNLOCKED",
    303,
    72,
)

settings_time_caption = lv.label(ui_SETTINGS_MENU)
settings_time_caption.set_text("Time")
settings_time_caption.align(lv.ALIGN.BOTTOM_LEFT, 18, -92)
settings_time_caption.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Time = lv.label(ui_SETTINGS_MENU)
ui_Time.set_text("--:--:--")
ui_Time.align(lv.ALIGN.BOTTOM_LEFT, 18, -68)
ui_Time.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_Time, 190, lv.TEXT_ALIGN.LEFT)

settings_sync_caption = lv.label(ui_SETTINGS_MENU)
settings_sync_caption.set_text("Time Sync")
settings_sync_caption.align(lv.ALIGN.BOTTOM_LEFT, 218, -92)
settings_sync_caption.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)

ui_Time_Sync = lv.label(ui_SETTINGS_MENU)
ui_Time_Sync.set_text("Default Sync")
ui_Time_Sync.align(lv.ALIGN.BOTTOM_LEFT, 218, -68)
ui_Time_Sync.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(ui_Time_Sync, 170, lv.TEXT_ALIGN.LEFT)

settings_menu_status = lv.label(ui_SETTINGS_MENU)
settings_menu_status.set_text("")
settings_menu_status.align(lv.ALIGN.BOTTOM_LEFT, 18, -16)
settings_menu_status.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
stabilize_value_label(settings_menu_status, 420, lv.TEXT_ALIGN.LEFT)

settings_menu_version = lv.label(ui_SETTINGS_MENU)
settings_menu_version.set_text(APP_VERSION)
settings_menu_version.align(lv.ALIGN.BOTTOM_RIGHT, -16, -12)
settings_menu_version.set_style_text_color(lv.color_hex(0x7A7A7A), lv.PART.MAIN | lv.STATE.DEFAULT)


# =========================================================
# PPH GOAL POPUP
# =========================================================
goal_popup = lv.obj(ui_MAIN_SCREEN)
goal_popup.set_size(320, 360)
goal_popup.center()
stabilize_widget(goal_popup)
goal_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
goal_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
goal_popup.set_style_border_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
goal_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
goal_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
goal_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
goal_popup.add_flag(lv.obj.FLAG.HIDDEN)

goal_popup_title = lv.label(goal_popup)
goal_popup_title.set_text("SET PPH GOAL")
goal_popup_title.align(lv.ALIGN.TOP_MID, 0, 12)
goal_popup_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
goal_popup_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

goal_textarea = lv.textarea(goal_popup)
goal_textarea.set_size(250, 50)
goal_textarea.align(lv.ALIGN.TOP_MID, 0, 48)
goal_textarea.set_one_line(True)
goal_textarea.set_max_length(4)
goal_textarea.set_text("100")
goal_textarea.set_placeholder_text("PPH")
stabilize_widget(goal_textarea)

goal_kb = lv.btnmatrix(goal_popup)
goal_kb.set_map([
    "1", "2", "3", "\n",
    "4", "5", "6", "\n",
    "7", "8", "9", "\n",
    "CLR", "0", "BKSP", "\n",
    "OK", "CANCEL", ""
])
goal_kb.set_size(280, 210)
goal_kb.align(lv.ALIGN.BOTTOM_MID, 0, -12)
stabilize_widget(goal_kb)

count_popup = lv.obj(ui_MAIN_SCREEN)
count_popup.set_size(320, 360)
count_popup.center()
stabilize_widget(count_popup)
count_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
count_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
count_popup.set_style_border_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
count_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
count_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
count_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
count_popup.add_flag(lv.obj.FLAG.HIDDEN)

count_popup_title = lv.label(count_popup)
count_popup_title.set_text("SET COUNT")
count_popup_title.align(lv.ALIGN.TOP_MID, 0, 12)
count_popup_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
count_popup_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

count_textarea = lv.textarea(count_popup)
count_textarea.set_size(250, 50)
count_textarea.align(lv.ALIGN.TOP_MID, 0, 48)
count_textarea.set_one_line(True)
count_textarea.set_max_length(6)
count_textarea.set_text("0")
count_textarea.set_placeholder_text("COUNT")
stabilize_widget(count_textarea)

count_kb = lv.btnmatrix(count_popup)
count_kb.set_map([
    "1", "2", "3", "\n",
    "4", "5", "6", "\n",
    "7", "8", "9", "\n",
    "CLR", "0", "BKSP", "\n",
    "OK", "CANCEL", ""
])
count_kb.set_size(280, 210)
count_kb.align(lv.ALIGN.BOTTOM_MID, 0, -12)
stabilize_widget(count_kb)


# =========================================================
# SETTINGS POPUPS
# =========================================================
settings_number_popup = None
settings_number_title = None
settings_number_textarea = None
settings_number_kb = None

wifi_scan_popup = None
wifi_scan_status = None
wifi_scan_refresh = None
wifi_scan_close = None
wifi_list = None

wifi_password_popup = None
wifi_password_ssid = None
wifi_password_status = None
wifi_password_textarea = None
wifi_password_connect = None
wifi_password_cancel = None

shift_hours_popup = None
shift_hours_widgets = {}
shift_hours_save = None
shift_hours_cancel = None

invert_popup = None
invert_checkbox = None
invert_save = None
invert_cancel = None

io_check_popup = None
io_check_label = None
io_check_close = None


def make_shift_hours_row(parent, shift_name, y_offset):
    row_label = lv.label(parent)
    row_label.set_text("SHIFT {}".format(shift_name))
    row_label.align(lv.ALIGN.TOP_LEFT, 28, y_offset + 2)
    row_label.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)

    enabled_cb = lv.checkbox(parent)
    enabled_cb.set_text("")
    enabled_cb.align(lv.ALIGN.TOP_LEFT, 148, y_offset)
    stabilize_widget(enabled_cb)

    start_dd = lv.dropdown(parent)
    start_dd.set_options(TIME_OPTION_TEXT)
    start_dd.set_size(140, 40)
    start_dd.align(lv.ALIGN.TOP_LEFT, 218, y_offset - 6)
    stabilize_widget(start_dd)

    end_dd = lv.dropdown(parent)
    end_dd.set_options(TIME_OPTION_TEXT)
    end_dd.set_size(140, 40)
    end_dd.align(lv.ALIGN.TOP_LEFT, 410, y_offset - 6)
    stabilize_widget(end_dd)

    return {
        "label": row_label,
        "enabled": enabled_cb,
        "start": start_dd,
        "end": end_dd,
    }

software_update_popup = None
software_update_status = None
software_update_list = None
software_update_refresh = None
software_update_ok = None
software_update_stats = None
software_update_close = None
software_update_entries = []
software_update_callbacks = []
software_update_selected_entry = None
software_update_selected_btn = None
software_update_entry_buttons = []

stats_config_popup = None
stats_config_machine_value = DEFAULT_STATS_MACHINE_ID
stats_config_machine_button = None
stats_config_machine_button_label = None
stats_config_import_url_textarea = None
stats_config_token_textarea = None
stats_config_status = None
stats_config_kb = None
stats_config_save = None
stats_config_import = None
stats_config_upload = None
stats_config_close = None
machine_picker_popup = None
machine_picker_list = None
machine_picker_status = None
machine_picker_close = None
machine_picker_refresh = None
machine_picker_callbacks = []

# =========================================================
# DATA / LOGIC
# =========================================================
run_pin = Pin(RUN_PIN, Pin.IN, Pin.PULL_UP)


def make_shift_bucket():
    return {
        "good": 0,
        "bad": 0,
        "cycle_count": 0,
        "produced_parts": 0,
        "with_load_sum": 0.0,
        "with_load_count": 0,
        "pph_cycle_count": 0,
        "pph_produced_parts": 0,
        "pph_with_load_sum": 0.0,
        "pph_with_load_count": 0,
    }


def make_shift_bucket_map():
    return {shift_name: make_shift_bucket() for shift_name in SHIFT_NAMES}


def clone_shift_settings():
    return {
        shift_name: {
            "enabled": bool(DEFAULT_SHIFT_SETTINGS[shift_name]["enabled"]),
            "start": int(DEFAULT_SHIFT_SETTINGS[shift_name]["start"]),
            "end": int(DEFAULT_SHIFT_SETTINGS[shift_name]["end"]),
        }
        for shift_name in SHIFT_NAMES
    }


def format_minutes_hhmm(total_minutes):
    total_minutes = int(total_minutes) % (24 * 60)
    return "{:02d}:{:02d}".format(total_minutes // 60, total_minutes % 60)


TIME_OPTION_VALUES = [index * TIME_OPTION_STEP_MINUTES for index in range((24 * 60) // TIME_OPTION_STEP_MINUTES)]
TIME_OPTION_TEXT = "\n".join([format_minutes_hhmm(value) for value in TIME_OPTION_VALUES])


good_count = 0
bad_count = 0
pph_goal = 100
parts_per_cycle = 1
io_invert = False
shift_reset_lead_minutes = 60
daily_production_count = 0
daily_production_reset_key = ""
last_daily_production = 0
daily_production_history = []
wifi_ssid = WIFI_SSID
wifi_password = WIFI_PASSWORD
update_server_url = UPDATE_SERVER_URL
stats_machine_id = DEFAULT_STATS_MACHINE_ID
stats_token_import_url = DEFAULT_STATS_TOKEN_IMPORT_URL
github_stats_token = ""
selected_wifi_ssid = ""
wifi_scan_results = []
shift_settings = clone_shift_settings()
door_switch_enabled = False
shift_reset_lock = False
machine_options_cache = [dict(item) for item in DEFAULT_MACHINE_OPTIONS]
notes_entries = []
notes_text_cache = {}
notes_current_index = 0
notes_title_text = "NOTES"
notes_body_text = ""
notes_status_text = ""
notes_page_text = ""
notes_mode_active = False

time_is_set = False
set_hour = 12
set_minute = 50

last_raw = run_pin.value()
last_change_ms = time.ticks_ms()
machine_high = (last_raw == 0 and not io_invert) or (last_raw != 0 and io_invert)

machine_run_start_epoch = time.time() if machine_high else None
machine_run_confirmed = machine_high
pending_machine_run_start_epoch = None
pending_cycle_shift = None
current_cycle_start_epoch = None
current_cycle_shift = None
last_cycle_complete_epoch = None

current_machine_run_seconds = 0
current_cycle_with_load_seconds = 0

graph_shift_stats = make_shift_bucket_map()
pending_shift_stats = make_shift_bucket_map()
completed_shift_stats = make_shift_bucket_map()
graph_cycle_anchor_epoch = {"A": None, "B": None, "C": None}

good_flash_until = None
bad_flash_until = None
data_dirty = False
stats_upload_dirty = False
last_save_ms = time.ticks_ms()
last_stats_upload_ms = time.ticks_add(time.ticks_ms(), -STATS_UPLOAD_INTERVAL_MS)
time_source_label = "Default"
daily_production_press_ms = None
good_label_reset_press_ms = None
bad_label_reset_press_ms = None
last_daily_reset_key = ""
count_edit_target = None
settings_number_target = None
shift_reset_keys = {shift_name: "" for shift_name in SHIFT_NAMES}
completed_shift_keys = {shift_name: "" for shift_name in SHIFT_NAMES}
graph_reset_press_ms = {shift_name: None for shift_name in SHIFT_NAMES}
ui_cache = {}
last_ui_refresh_ms = time.ticks_ms()
last_gesture_ms = time.ticks_add(time.ticks_ms(), -GESTURE_COOLDOWN_MS)
main_screen_button_guard_until = time.ticks_add(time.ticks_ms(), -MAIN_SCREEN_BUTTON_GUARD_MS)
boot_flag_phase = 0
boot_flag_last_ms = time.ticks_ms()
startup_splash_active = True
startup_splash_start_ms = time.ticks_ms()
startup_target_screen = None
boot_wifi_sync_attempted = False
wifi_network_callbacks = []


def format_mmss(total_seconds):
    total_seconds = int(max(0, total_seconds))
    mins = total_seconds // 60
    secs = total_seconds % 60
    return "{}m {}s".format(mins, secs)


def format_hhmmss(hours, minutes, seconds):
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)


def clamp_minute_value(value):
    return int(value) % (24 * 60)


def normalize_import_url(url_text):
    url_text = str(url_text).strip()
    if not url_text:
        return ""
    if "://" not in url_text:
        url_text = "http://" + url_text
    return url_text


def sanitize_imported_token(token_text):
    token_text = str(token_text).replace("\r", "")
    for line in token_text.split("\n"):
        line = line.strip()
        if line:
            return line
    return ""


def format_status_message(text, max_len=58):
    text = " ".join(str(text).split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def dropdown_index_from_minutes(value):
    step = TIME_OPTION_STEP_MINUTES
    return int(round(clamp_minute_value(value) / step)) % len(TIME_OPTION_VALUES)


def minutes_from_dropdown(dropdown):
    index = dropdown.get_selected()
    if index < 0 or index >= len(TIME_OPTION_VALUES):
        return 0
    return TIME_OPTION_VALUES[index]


def normalize_shift_setting(shift_name, setting):
    default = DEFAULT_SHIFT_SETTINGS[shift_name]
    return {
        "enabled": bool(setting.get("enabled", default["enabled"])),
        "start": clamp_minute_value(setting.get("start", default["start"])),
        "end": clamp_minute_value(setting.get("end", default["end"])),
    }


def is_signal_active(raw_value):
    active = raw_value == 0
    if io_invert:
        active = not active
    return active


def is_minute_in_shift_window(minute_value, start_minute, end_minute):
    start_minute = clamp_minute_value(start_minute)
    end_minute = clamp_minute_value(end_minute)
    if start_minute == end_minute:
        return False
    if start_minute < end_minute:
        return start_minute <= minute_value < end_minute
    return minute_value >= start_minute or minute_value < end_minute


def set_cached_label_text(key, label, text):
    text = str(text)
    if ui_cache.get(key) != text:
        label.set_text(text)
        ui_cache[key] = text


def set_cached_arc_value(key, arc, value):
    if ui_cache.get(key) != value:
        arc.set_value(value)
        ui_cache[key] = value


def set_object_hidden(obj, hidden):
    cache_key = "hidden_{}".format(id(obj))
    if ui_cache.get(cache_key) != hidden:
        SetFlag(obj, lv.obj.FLAG.HIDDEN, hidden)
        ui_cache[cache_key] = hidden


def set_notes_mode(enabled):
    global notes_mode_active
    notes_mode_active = bool(enabled)
    set_object_hidden(notes_overlay, not notes_mode_active)


def arm_main_screen_button_guard():
    global main_screen_button_guard_until
    main_screen_button_guard_until = time.ticks_add(time.ticks_ms(), MAIN_SCREEN_BUTTON_GUARD_MS)


def main_screen_button_guard_active():
    return time.ticks_diff(time.ticks_ms(), main_screen_button_guard_until) < 0


def load_main_screen_with_guard():
    arm_main_screen_button_guard()
    lv.scr_load(ui_MAIN_SCREEN)
    update_ui()


def get_time_sync_display():
    if str(time_source_label).lower().startswith("wifi"):
        return "WiFi Sync"
    return "Default Sync"


def set_door_switch_visibility():
    hidden = not door_switch_enabled
    for obj in (
        ui_Load_Time_Lable,
        ui_AVRG_LOAD_TIME_NUMBER,
        ui_AVRG_IDLE_TIME_LABLE,
        ui_AVRG_IDLE_TIME_NUMBER,
    ):
        set_object_hidden(obj, hidden)


def day_of_week(year, month, day):
    if month < 3:
        month += 12
        year -= 1
    k = year % 100
    j = year // 100
    h = (day + ((13 * (month + 1)) // 5) + k + (k // 4) + (j // 4) + (5 * j)) % 7
    return (h + 5) % 7


def nth_weekday_of_month(year, month, weekday, nth):
    first_wday = day_of_week(year, month, 1)
    day = 1 + ((weekday - first_wday) % 7)
    day += (nth - 1) * 7
    return day


def is_us_central_dst_utc(year, month, day, hour):
    dst_start_day = nth_weekday_of_month(year, 3, 6, 2)
    dst_end_day = nth_weekday_of_month(year, 11, 6, 1)

    if month < 3 or month > 11:
        return False
    if 3 < month < 11:
        return True
    if month == 3:
        if day > dst_start_day:
            return True
        if day < dst_start_day:
            return False
        return hour >= 8
    if day < dst_end_day:
        return True
    if day > dst_end_day:
        return False
    return hour < 7


def connect_wifi():
    if network is None or not wifi_ssid:
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(wifi_ssid, wifi_password)
        start_ms = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_ms) > WIFI_TIMEOUT_MS:
                return None
            time.sleep(0.2)
    return wlan


def scan_wifi_networks():
    if network is None:
        return []
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        found = []
        seen = set()
        for entry in wlan.scan():
            raw_ssid = entry[0]
            try:
                ssid = raw_ssid.decode("utf-8")
            except AttributeError:
                ssid = str(raw_ssid)
            except Exception:
                ssid = str(raw_ssid)
            ssid = ssid.strip()
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            found.append(ssid)
        found.sort()
        return found
    except Exception as err:
        print("WiFi scan failed:", err)
        return []


def sync_time_from_wifi():
    global time_is_set, set_hour, set_minute, time_source_label
    if ntptime is None:
        time_source_label = "Default"
        return False

    wlan = connect_wifi()
    if wlan is None:
        time_source_label = "Default"
        return False

    try:
        ntptime.settime()
        utc_epoch = time.time()
        utc_tuple = time.localtime(utc_epoch)
        dst_active = is_us_central_dst_utc(utc_tuple[0], utc_tuple[1], utc_tuple[2], utc_tuple[3])
        offset_hours = -5 if dst_active else -6
        local_epoch = utc_epoch + (offset_hours * 3600)
        local_tuple = time.localtime(local_epoch)

        rtc = RTC()
        rtc.datetime((
            local_tuple[0],
            local_tuple[1],
            local_tuple[2],
            0,
            local_tuple[3],
            local_tuple[4],
            local_tuple[5],
            0,
        ))

        set_hour = local_tuple[3]
        set_minute = local_tuple[4]
        time_is_set = True
        time_source_label = "WiFi Sync"
        mark_data_dirty()
        save_state(force=True)
        return True
    except Exception as err:
        print("WiFi time sync failed:", err)
        time_source_label = "Default"
        return False


def maybe_run_boot_wifi_sync():
    global boot_wifi_sync_attempted
    if boot_wifi_sync_attempted:
        return
    boot_wifi_sync_attempted = True

    if sync_time_from_wifi():
        refresh_boot_time_labels()
        sync_live_timers()
        update_ui()
        if lv.scr_act() == boot_scr:
            load_main_screen_with_guard()


def get_update_manifest_url():
    source_url = str(update_server_url).strip()
    if "raw.githubusercontent.com/INDMFG/Machien-OEE/" in source_url:
        return OTA_MANIFEST_URL
    if source_url and source_url.lower().endswith(".json"):
        return source_url
    return OTA_MANIFEST_URL


def parse_url(url_text):
    url_text = str(url_text).strip()
    if url_text.startswith("https://"):
        scheme = "https"
        default_port = 443
        rest = url_text[8:]
    elif url_text.startswith("http://"):
        scheme = "http"
        default_port = 80
        rest = url_text[7:]
    else:
        raise ValueError("Only http:// or https:// URLs are supported")

    slash_index = rest.find("/")
    if slash_index < 0:
        host_port = rest
        path = "/"
    else:
        host_port = rest[:slash_index]
        path = rest[slash_index:]

    if not host_port:
        raise ValueError("Missing update source host")

    if ":" in host_port:
        host_name, port_text = host_port.rsplit(":", 1)
        port = int(port_text)
    else:
        host_name = host_port
        port = default_port

    if not host_name:
        raise ValueError("Missing update source host")

    return scheme, host_name, port, path


def open_http_socket(scheme, host_name, port):
    if socket is None:
        raise OSError("Socket support unavailable")

    addr = socket.getaddrinfo(host_name, port)[0][-1]
    sock = socket.socket()
    sock.connect(addr)

    if scheme == "https":
        if ssl is None:
            raise OSError("HTTPS unavailable")
        try:
            sock = ssl.wrap_socket(sock, server_hostname=host_name)
        except TypeError:
            sock = ssl.wrap_socket(sock)

    return sock


def socket_send_bytes(sock, data):
    if not isinstance(data, bytes):
        data = bytes(data)
    total_sent = 0
    while total_sent < len(data):
        chunk = data[total_sent:]
        if hasattr(sock, "send"):
            sent = sock.send(chunk)
        elif hasattr(sock, "write"):
            sent = sock.write(chunk)
        else:
            raise OSError("Socket send unavailable")
        if sent is None:
            sent = len(chunk)
        if sent <= 0:
            raise OSError("Socket send failed")
        total_sent += sent
    return total_sent


def socket_recv_bytes(sock, size):
    if hasattr(sock, "recv"):
        return sock.recv(size)
    if hasattr(sock, "read"):
        data = sock.read(size)
        if data is None:
            return b""
        return data
    raise OSError("Socket recv unavailable")


def socket_close_safe(sock):
    try:
        if sock is not None:
            sock.close()
    except Exception:
        pass


def http_open_response(url_text, redirect_limit=2):
    scheme, host_name, port, path = parse_url(url_text)
    sock = None

    try:
        sock = open_http_socket(scheme, host_name, port)
        request = (
            "GET {} HTTP/1.0\r\n"
            "Host: {}\r\n"
            "User-Agent: Machine-OEE\r\n"
            "Connection: close\r\n\r\n"
        ).format(path, host_name)
        socket_send_bytes(sock, request.encode("utf-8"))

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = socket_recv_bytes(sock, 128)
            if not chunk:
                break
            header_data += chunk
            if len(header_data) > 8192:
                break

        header_parts = header_data.split(b"\r\n\r\n", 1)
        raw_headers = header_parts[0].decode("utf-8", "ignore")
        body = header_parts[1] if len(header_parts) > 1 else b""
        header_lines = raw_headers.split("\r\n")
        status_line = header_lines[0] if header_lines else ""

        headers = {}
        for line in header_lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()

        try:
            status_code = int(status_line.split(" ")[1])
        except Exception:
            status_code = 0

        if status_code in (301, 302, 303, 307, 308):
            location = headers.get("location", "")
            socket_close_safe(sock)
            sock = None
            if redirect_limit <= 0 or not location:
                raise OSError(status_line)
            if location.startswith("/"):
                default_port = 443 if scheme == "https" else 80
                if port == default_port:
                    location = "{}://{}{}".format(scheme, host_name, location)
                else:
                    location = "{}://{}:{}{}".format(scheme, host_name, port, location)
            return http_open_response(location, redirect_limit - 1)

        if status_code != 200:
            raise OSError(status_line)

        return sock, body, headers
    except Exception:
        socket_close_safe(sock)
        raise


def http_read_text(url_text):
    sock, body, _headers = http_open_response(url_text)
    chunks = [body]
    try:
        while True:
            chunk = socket_recv_bytes(sock, 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        socket_close_safe(sock)
    return b"".join(chunks).decode("utf-8", "ignore")


def http_download_to_file(url_text, dest_path):
    temp_path = dest_path + ".part"
    sock = None
    out_file = None

    try:
        sock, body, _headers = http_open_response(url_text)
        out_file = open(temp_path, "wb")
        if body:
            out_file.write(body)

        while True:
            chunk = socket_recv_bytes(sock, 1024)
            if not chunk:
                break
            out_file.write(chunk)

        out_file.close()
        out_file = None

        preview_file = open(temp_path, "rb")
        preview = preview_file.read(256)
        preview_file.close()
        if not preview:
            raise OSError("Downloaded file is empty")
        if b"import lvgl" not in preview and b"APP_VERSION" not in preview:
            raise OSError("Downloaded file does not look like app_runtime.py")

        try:
            os.remove(dest_path)
        except OSError:
            pass
        os.rename(temp_path, dest_path)
    except Exception:
        try:
            if out_file is not None:
                out_file.close()
        except Exception:
            pass
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise
    finally:
        socket_close_safe(sock)


def http_request(url_text, method="GET", headers=None, body=None):
    scheme, host_name, port, path = parse_url(url_text)
    sock = None
    body_bytes = b""
    if body is not None:
        if isinstance(body, bytes):
            body_bytes = body
        else:
            body_bytes = str(body).encode("utf-8")

    try:
        sock = open_http_socket(scheme, host_name, port)
        lines = [
            "{} {} HTTP/1.0".format(method, path),
            "Host: {}".format(host_name),
            "User-Agent: Machine-OEE",
            "Connection: close",
        ]
        if headers:
            for name, value in headers.items():
                lines.append("{}: {}".format(name, value))
        if body_bytes:
            lines.append("Content-Length: {}".format(len(body_bytes)))

        request = "\r\n".join(lines) + "\r\n\r\n"
        socket_send_bytes(sock, request.encode("utf-8"))
        if body_bytes:
            socket_send_bytes(sock, body_bytes)

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = socket_recv_bytes(sock, 128)
            if not chunk:
                break
            header_data += chunk
            if len(header_data) > 16384:
                break

        header_parts = header_data.split(b"\r\n\r\n", 1)
        raw_headers = header_parts[0].decode("utf-8", "ignore")
        body_prefix = header_parts[1] if len(header_parts) > 1 else b""
        header_lines = raw_headers.split("\r\n")
        status_line = header_lines[0] if header_lines else ""

        response_headers = {}
        for line in header_lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            response_headers[name.strip().lower()] = value.strip()

        try:
            status_code = int(status_line.split(" ")[1])
        except Exception:
            status_code = 0

        chunks = [body_prefix]
        while True:
            chunk = socket_recv_bytes(sock, 1024)
            if not chunk:
                break
            chunks.append(chunk)

        return status_code, response_headers, b"".join(chunks)
    finally:
        socket_close_safe(sock)


def install_staged_update():
    if os is None:
        raise OSError("Filesystem unavailable")

    try:
        os.remove(OTA_BACKUP_FILE)
    except OSError:
        pass

    try:
        os.rename(APP_RUNTIME_FILE, OTA_BACKUP_FILE)
    except OSError:
        pass

    os.rename(OTA_STAGED_FILE, APP_RUNTIME_FILE)


def fetch_ota_manifest():
    manifest_text = http_read_text(get_update_manifest_url())
    manifest = json.loads(manifest_text)
    if not isinstance(manifest, dict):
        raise ValueError("Update manifest is invalid")
    return manifest


def normalize_ota_entries(manifest):
    latest_version = str(manifest.get("latest", "")).strip()
    raw_entries = manifest.get("versions", [])
    entries = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", "")).strip()
        url = str(item.get("url", "")).strip()
        notes = str(item.get("notes", "")).strip()
        if not version or not url:
            continue
        entries.append({
            "version": version,
            "url": url,
            "notes": notes,
            "latest": version == latest_version,
        })
    return entries


def perform_software_update(entry):
    if not isinstance(entry, dict):
        raise ValueError("Missing update entry")
    update_url = str(entry.get("url", "")).strip()
    if not update_url:
        raise ValueError("Missing update file URL")

    if connect_wifi() is None:
        raise OSError("WiFi not connected")

    http_download_to_file(update_url, OTA_STAGED_FILE)
    install_staged_update()
    mark_data_dirty()
    save_state(force=True)


def base64_encode_bytes(data):
    if binascii is None:
        raise OSError("Base64 support unavailable")
    encoded = binascii.b2a_base64(data)
    if isinstance(encoded, bytes):
        return encoded.decode("utf-8").strip()
    return str(encoded).strip()


def base64_decode_text(text):
    if binascii is None:
        raise OSError("Base64 support unavailable")
    if isinstance(text, str):
        text = text.encode("utf-8")
    return binascii.a2b_base64(text)


def parse_github_error_message(response_text):
    message = ""
    try:
        response_obj = json.loads(response_text)
        if isinstance(response_obj, dict):
            message = str(response_obj.get("message", "")).strip()
            errors = response_obj.get("errors", [])
            if isinstance(errors, list) and errors:
                first_error = errors[0]
                if isinstance(first_error, dict):
                    details = str(first_error.get("message", "") or first_error.get("code", "")).strip()
                else:
                    details = str(first_error).strip()
                if details:
                    if message:
                        message = "{} ({})".format(message, details)
                    else:
                        message = details
    except Exception:
        message = ""
    if not message:
        message = " ".join(str(response_text).split())
    return format_status_message(message, 90)


def github_api_request(method, api_path, token_text, body_obj=None):
    if not token_text:
        raise OSError("GitHub token not set")
    headers = {
        "Authorization": "Bearer {}".format(token_text),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body_text = None
    if body_obj is not None:
        headers["Content-Type"] = "application/json"
        body_text = json.dumps(body_obj)
    url = "https://api.github.com{}".format(api_path)
    status_code, response_headers, response_body = http_request(url, method=method, headers=headers, body=body_text)
    response_text = response_body.decode("utf-8", "ignore") if response_body else ""
    return status_code, response_headers, response_text


def github_quote_path(path_text):
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/"
    pieces = []
    for char in str(path_text).replace("\\", "/"):
        if char in allowed:
            pieces.append(char)
        else:
            pieces.append("%{:02X}".format(ord(char)))
    return "".join(pieces)


def get_notes_repo_api_path(path_text=""):
    api_path = "/repos/{}/{}/contents".format(NOTES_REPO_OWNER, NOTES_REPO_NAME)
    path_text = str(path_text).strip().strip("/")
    if path_text:
        api_path += "/" + github_quote_path(path_text)
    return "{}?ref={}".format(api_path, NOTES_REPO_BRANCH)


def get_notes_repo_label():
    return "{}/{}".format(NOTES_REPO_OWNER, NOTES_REPO_NAME)


def get_stats_repo_api_path(path_text=""):
    api_path = "/repos/{}/{}/contents".format(STATS_REPO_OWNER, STATS_REPO_NAME)
    path_text = str(path_text).strip().strip("/")
    if path_text:
        api_path += "/" + github_quote_path(path_text)
    return "{}?ref={}".format(api_path, STATS_REPO_BRANCH)


def normalize_machine_options(entries):
    normalized = []
    seen = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        machine_id = str(item.get("id", "")).strip()
        if not machine_id or machine_id in seen:
            continue
        machine_name = str(item.get("name", machine_id)).strip() or machine_id
        normalized.append({
            "id": machine_id,
            "name": machine_name,
            "active": bool(item.get("active", False)),
        })
        seen[machine_id] = True
    return normalized


def ensure_machine_option_available(machine_id):
    global machine_options_cache
    machine_id = str(machine_id).strip()
    if not machine_id:
        return
    for item in machine_options_cache:
        if item.get("id") == machine_id:
            return
    machine_options_cache.append({
        "id": machine_id,
        "name": machine_id,
        "active": False,
    })


def get_machine_display_name(machine_id):
    machine_id = str(machine_id).strip()
    for item in machine_options_cache:
        if item.get("id") == machine_id:
            return str(item.get("name", machine_id))
    return machine_id


def format_machine_choice(machine_id):
    machine_id = str(machine_id).strip()
    if not machine_id:
        return "Not Set"
    return "{} ({})".format(get_machine_display_name(machine_id), machine_id)


def get_machine_index_repo_path():
    return "machines/index.json"


def load_machine_options_from_repo():
    global machine_options_cache
    if not github_stats_token:
        ensure_machine_option_available(stats_machine_id)
        return machine_options_cache
    if connect_wifi() is None:
        raise OSError("WiFi not connected")

    status_code, _headers, response_text = github_api_request(
        "GET", get_stats_repo_api_path(get_machine_index_repo_path()), github_stats_token
    )
    if status_code != 200:
        raise OSError("Machine index read failed ({}): {}".format(status_code, parse_github_error_message(response_text)))

    response_obj = json.loads(response_text)
    content_text = str(response_obj.get("content", ""))
    if not content_text:
        raise OSError("Machine index is empty")

    decoded = base64_decode_text(content_text).decode("utf-8", "ignore")
    options = normalize_machine_options(json.loads(decoded))
    if not options:
        raise OSError("No machine options found")

    machine_options_cache = options
    ensure_machine_option_available(stats_machine_id)
    return machine_options_cache


def get_notes_machine_path():
    return "machines/{}".format(stats_machine_id)


def list_notes_repo_entries():
    status_code, _headers, response_text = github_api_request(
        "GET", get_notes_repo_api_path(get_notes_machine_path()), github_stats_token
    )
    if status_code != 200:
        raise OSError("Notes read failed ({}): {}".format(status_code, parse_github_error_message(response_text)))

    try:
        response_obj = json.loads(response_text)
    except Exception:
        response_obj = []

    if isinstance(response_obj, dict):
        response_obj = [response_obj]

    entries = []
    for item in response_obj:
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")).lower() != "file":
            continue
        name = str(item.get("name", "")).strip()
        path_text = str(item.get("path", name)).strip()
        lower_name = name.lower()
        if not name or name.startswith("."):
            continue
        if not any(lower_name.endswith(ext) for ext in NOTES_TEXT_EXTENSIONS):
            continue
        entries.append({"name": name, "path": path_text})

    entries.sort(key=lambda item: item["name"].lower())
    return entries


def read_note_entry_text(entry):
    status_code, _headers, response_text = github_api_request(
        "GET", get_notes_repo_api_path(entry.get("path", "")), github_stats_token
    )
    if status_code != 200:
        raise OSError("Note read failed ({}): {}".format(status_code, parse_github_error_message(response_text)))

    response_obj = json.loads(response_text)
    content_text = str(response_obj.get("content", ""))
    if not content_text:
        return ""

    decoded = base64_decode_text(content_text).decode("utf-8", "ignore")
    decoded = decoded.replace("\r\n", "\n").replace("\r", "\n")

    file_name = str(entry.get("name", "")).lower()
    if file_name.endswith(".json"):
        try:
            return json_pretty_text(json.loads(decoded))
        except Exception:
            return decoded

    return decoded


def set_notes_view_state(title_text, body_text, status_text="", page_text=""):
    global notes_title_text, notes_body_text, notes_status_text, notes_page_text
    notes_title_text = str(title_text)
    notes_body_text = str(body_text)
    notes_status_text = str(status_text)
    notes_page_text = str(page_text)


def load_current_note_page():
    global notes_current_index
    if not github_stats_token:
        set_notes_view_state(
            "NOTES",
            "GitHub token not set.\nOpen SETTINGS > SOFTWARE UPDATE > STATS and import or save the token first.",
            "Repo: {}  Machine: {}".format(get_notes_repo_label(), stats_machine_id),
            "",
        )
        return

    if not notes_entries:
        set_notes_view_state(
            "NOTES",
            "No supported note files found.\nAdd numbered .txt, .md, .json, or .csv files to the private repo.",
            "Repo: {}  Machine: {}".format(get_notes_repo_label(), stats_machine_id),
            "0/0",
        )
        return

    if notes_current_index >= len(notes_entries):
        set_notes_view_state("", "", "", "")
        return

    if notes_current_index < 0:
        notes_current_index = 0

    entry = notes_entries[notes_current_index]
    entry_path = entry["path"]
    if entry_path not in notes_text_cache:
        notes_text_cache[entry_path] = read_note_entry_text(entry)

    set_notes_view_state(
        entry["name"],
        notes_text_cache.get(entry_path, ""),
        "Repo: {}  Machine: {}".format(get_notes_repo_label(), stats_machine_id),
        "{}/{}".format(notes_current_index + 1, len(notes_entries)),
    )


def open_notes_screen(reset_index=False):
    global notes_entries, notes_text_cache, notes_current_index

    if reset_index:
        notes_current_index = 0

    set_notes_mode(True)
    notes_entries = []
    notes_text_cache = {}

    if github_stats_token:
        try:
            notes_entries = list_notes_repo_entries()
        except Exception as err:
            set_notes_view_state(
                "NOTES",
                "",
                format_status_message("Notes load failed: {}".format(err), 82),
                "",
            )
            lv.scr_load(ui_SETTINGS)
            update_ui()
            return

    if notes_current_index > len(notes_entries):
        notes_current_index = len(notes_entries)

    load_current_note_page()
    lv.scr_load(ui_SETTINGS)
    update_ui()


def show_shift_stats_screen():
    set_notes_mode(False)
    lv.scr_load(ui_SETTINGS)
    update_ui()


def advance_notes_page():
    global notes_current_index
    if notes_current_index < len(notes_entries):
        notes_current_index += 1
    load_current_note_page()
    update_ui()


def retreat_notes_page():
    global notes_current_index
    if notes_current_index > 0:
        notes_current_index -= 1
    load_current_note_page()
    update_ui()


def import_stats_token_from_url(url_text):
    url_text = normalize_import_url(url_text)
    if not url_text:
        raise ValueError("Token URL required")
    if connect_wifi() is None:
        raise OSError("WiFi not connected")
    token_text = sanitize_imported_token(http_read_text(url_text))
    if not token_text:
        raise ValueError("Token file is empty")
    return url_text, token_text


def get_stats_status_path():
    return "machines/{}/status.json".format(stats_machine_id)


def request_device_reset():
    if machine is None:
        raise OSError("Reset unavailable")
    machine.reset()


def safe_pct(num, den):
    if den <= 0:
        return 0.0
    return (num / den) * 100.0


def get_shift():
    t = time.localtime()
    minutes = t[3] * 60 + t[4]
    for shift_name in SHIFT_NAMES:
        config = shift_settings[shift_name]
        if not config["enabled"]:
            continue
        if is_minute_in_shift_window(minutes, config["start"], config["end"]):
            return shift_name
    return None


def get_shift_display():
    shift_name = get_shift()
    if shift_name is None:
        return "OFF"
    return shift_name


def format_date_key(tuple_value):
    return "{:04d}-{:02d}-{:02d}".format(tuple_value[0], tuple_value[1], tuple_value[2])


def get_daily_production_key_for_epoch(epoch):
    now = time.localtime(epoch)
    minutes = now[3] * 60 + now[4]
    if minutes < DAILY_PRODUCTION_RESET_MINUTE:
        now = time.localtime(epoch - 86400)
    return format_date_key(now)


def get_daily_production_key():
    return get_daily_production_key_for_epoch(time.time())


def get_reset_day_key_for_epoch(epoch):
    now = time.localtime(epoch)
    minutes = now[3] * 60 + now[4]
    reset_minute = 8 * 60
    enabled_triggers = []
    for shift_name in SHIFT_NAMES:
        config = shift_settings[shift_name]
        if not config["enabled"]:
            continue
        enabled_triggers.append((config["start"] - shift_reset_lead_minutes) % (24 * 60))
    if enabled_triggers:
        reset_minute = min(enabled_triggers)
    if minutes < reset_minute:
        now = time.localtime(epoch - 86400)
    return format_date_key(now)


def get_reset_day_key():
    return get_reset_day_key_for_epoch(time.time())


def get_previous_reset_day_key():
    return get_reset_day_key_for_epoch(time.time() - 86400)


def get_shift_reset_key(shift_name, epoch=None):
    if epoch is None:
        epoch = time.time()

    config = shift_settings[shift_name]
    shift_tuple = time.localtime(epoch)
    midnight_epoch = epoch - (shift_tuple[3] * 3600 + shift_tuple[4] * 60 + shift_tuple[5])
    latest_key = None
    latest_reset_epoch = None

    for day_delta in (-2, -1, 0, 1):
        shift_midnight_epoch = midnight_epoch + (day_delta * 86400)
        reset_epoch = shift_midnight_epoch + (config["start"] * 60) - (shift_reset_lead_minutes * 60)
        if reset_epoch <= epoch and (latest_reset_epoch is None or reset_epoch > latest_reset_epoch):
            latest_reset_epoch = reset_epoch
            latest_key = format_date_key(time.localtime(shift_midnight_epoch))

    if latest_key is None:
        latest_key = format_date_key(time.localtime(midnight_epoch - 86400))
    return latest_key


def parse_date_key(date_key):
    try:
        return (
            int(date_key[0:4]),
            int(date_key[5:7]),
            int(date_key[8:10]),
        )
    except Exception:
        return None


def get_shift_end_epoch(shift_name, shift_key):
    config = shift_settings[shift_name]
    if not config["enabled"]:
        return None

    parts = parse_date_key(shift_key)
    if parts is None:
        return None

    midnight_epoch = time.mktime((parts[0], parts[1], parts[2], 0, 0, 0, 0, 0))
    end_epoch = midnight_epoch + (config["end"] * 60)
    if config["end"] <= config["start"]:
        end_epoch += 86400
    return end_epoch


def should_include_cycle_in_pph(shift_name, cycle_number, completion_epoch):
    if cycle_number <= PPH_IGNORE_INITIAL_CYCLES:
        return False

    shift_key = get_shift_reset_key(shift_name, completion_epoch)
    shift_end_epoch = get_shift_end_epoch(shift_name, shift_key)
    if shift_end_epoch is not None:
        cutoff_epoch = shift_end_epoch - (PPH_STOP_BEFORE_SHIFT_END_MINUTES * 60)
        if completion_epoch >= cutoff_epoch:
            return False

    return True


def clear_shift_bucket(bucket):
    bucket["good"] = 0
    bucket["bad"] = 0
    bucket["cycle_count"] = 0
    bucket["produced_parts"] = 0
    bucket["with_load_sum"] = 0.0
    bucket["with_load_count"] = 0
    bucket["pph_cycle_count"] = 0
    bucket["pph_produced_parts"] = 0
    bucket["pph_with_load_sum"] = 0.0
    bucket["pph_with_load_count"] = 0


def clone_shift_bucket(bucket):
    return {
        "good": int(bucket.get("good", 0)),
        "bad": int(bucket.get("bad", 0)),
        "cycle_count": int(bucket.get("cycle_count", bucket.get("total", 0))),
        "produced_parts": int(bucket.get("produced_parts", bucket.get("cycle_count", bucket.get("total", 0)))),
        "with_load_sum": float(bucket.get("with_load_sum", 0.0)),
        "with_load_count": int(bucket.get("with_load_count", 0)),
        "pph_cycle_count": int(bucket.get("pph_cycle_count", bucket.get("with_load_count", 0))),
        "pph_produced_parts": int(bucket.get("pph_produced_parts", bucket.get("produced_parts", bucket.get("cycle_count", 0)))),
        "pph_with_load_sum": float(bucket.get("pph_with_load_sum", bucket.get("with_load_sum", 0.0))),
        "pph_with_load_count": int(bucket.get("pph_with_load_count", bucket.get("with_load_count", 0))),
    }


def get_bucket_pph(bucket):
    eligible_cycles = int(bucket.get("pph_cycle_count", 0))
    total_parts = int(bucket.get("pph_produced_parts", bucket.get("produced_parts", bucket.get("cycle_count", 0))))
    total_time = float(bucket.get("pph_with_load_sum", bucket.get("with_load_sum", 0.0)))
    if eligible_cycles < PPH_DISPLAY_READY_CYCLES or total_parts <= 0 or total_time <= 0:
        return 0
    return int(round(total_parts / (total_time / 3600.0)))


def get_bucket_average_with_load(bucket):
    if bucket["with_load_count"] <= 0:
        return 0
    return bucket["with_load_sum"] / bucket["with_load_count"]


def refresh_boot_time_labels():
    boot_hour_value.set_text("{:02d}".format(set_hour))
    boot_min_value.set_text("{:02d}".format(set_minute))


def animate_boot_flag(force=False):
    global boot_flag_phase, boot_flag_last_ms
    now_ms = time.ticks_ms()
    if not force and time.ticks_diff(now_ms, boot_flag_last_ms) < BOOT_FLAG_FRAME_MS:
        return

    boot_flag_last_ms = now_ms
    boot_flag_phase = (boot_flag_phase + 1) % len(BOOT_FLAG_WAVE)
    wave_count = len(BOOT_FLAG_WAVE)

    if boot_flag_img is not None:
        boot_flag_img.set_x(BOOT_FLAG_IMAGE_BASE_X + BOOT_FLAG_WAVE[boot_flag_phase])
        return

    if not boot_flag_stripes or boot_flag_union is None:
        return

    for stripe_index, stripe in enumerate(boot_flag_stripes):
        offset = BOOT_FLAG_WAVE[(boot_flag_phase + stripe_index) % wave_count]
        stripe.set_x(offset)
        stripe.set_width(BOOT_FLAG_VIEW_WIDTH - offset if offset < 0 else BOOT_FLAG_VIEW_WIDTH + offset)

    union_offset = BOOT_FLAG_WAVE[(boot_flag_phase + 2) % wave_count]
    boot_flag_union.set_x(union_offset)
    boot_flag_union.set_width(95 - union_offset if union_offset < 0 else 95 + union_offset)


def get_graph_shift_pph(shift_name):
    return get_bucket_pph(graph_shift_stats[shift_name])


def get_pending_shift_average_with_load(shift_name):
    return get_bucket_average_with_load(pending_shift_stats[shift_name])


def get_completed_shift_pph(shift_name):
    return get_bucket_pph(completed_shift_stats[shift_name])


def get_completed_shift_average_with_load(shift_name):
    return get_bucket_average_with_load(completed_shift_stats[shift_name])


def normalize_daily_production_history(entries):
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key", ""))
        try:
            total = max(0, int(entry.get("total", 0)))
        except Exception:
            total = 0
        if key:
            normalized.append({"key": key, "total": total})
    normalized.sort(key=lambda item: item["key"])
    return normalized[-14:]


def archive_daily_production(key, total):
    global last_daily_production
    if not key:
        return

    total = max(0, int(total))
    last_daily_production = total

    replaced = False
    for entry in daily_production_history:
        if entry.get("key") == key:
            entry["total"] = total
            replaced = True
            break
    if not replaced:
        daily_production_history.append({"key": key, "total": total})
        daily_production_history.sort(key=lambda item: item["key"])
        while len(daily_production_history) > 14:
            daily_production_history.pop(0)


def get_total_daily_good_parts():
    return max(0, int(daily_production_count))


def get_average_daily_production():
    if not daily_production_history:
        return 0
    total = 0
    for entry in daily_production_history:
        total += max(0, int(entry.get("total", 0)))
    return int(round(total / len(daily_production_history)))


def json_pretty_text(value, level=0):
    indent = "  " * level
    next_indent = "  " * (level + 1)

    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = []
        for key, item in value.items():
            parts.append("{}{}: {}".format(next_indent, json.dumps(str(key)), json_pretty_text(item, level + 1)))
        return "{\n" + ",\n".join(parts) + "\n" + indent + "}"

    if isinstance(value, list):
        if not value:
            return "[]"
        parts = []
        for item in value:
            parts.append("{}{}".format(next_indent, json_pretty_text(item, level + 1)))
        return "[\n" + ",\n".join(parts) + "\n" + indent + "]"

    return json.dumps(value)


def build_machine_status_payload(existing=None):
    if not isinstance(existing, dict):
        existing = {}

    existing_machine = existing.get("machine", {})
    if not isinstance(existing_machine, dict):
        existing_machine = {}

    now_tuple = time.localtime()
    current_shift = get_shift()
    total_good_parts = int(good_count)
    shifts_payload = {}

    for shift_name in SHIFT_NAMES:
        live_avg_seconds = int(round(get_pending_shift_average_with_load(shift_name)))
        shifts_payload[shift_name] = {
            "live": 1 if current_shift == shift_name else 0,
            "off_time": 0 if current_shift == shift_name else 1,
            "avg_with_load": format_mmss(live_avg_seconds),
            "bad": int(pending_shift_stats[shift_name]["bad"]),
            "good": int(pending_shift_stats[shift_name]["good"]),
            "cycles": int(pending_shift_stats[shift_name]["cycle_count"]),
            "pph": int(get_graph_shift_pph(shift_name)),
            "total_parts": total_good_parts,
        }

    return {
        "machine": {
            "id": stats_machine_id,
            "name": existing_machine.get("name", existing.get("machine_name", stats_machine_id)),
            "active": bool(existing_machine.get("active", existing.get("active", True))),
            "configured": bool(existing_machine.get("configured", existing.get("configured", True))),
        },
        "software": {
            "app_version": APP_VERSION,
            "time_sync": get_time_sync_display(),
        },
        "status": {
            "last_update_local": "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
                now_tuple[0], now_tuple[1], now_tuple[2], now_tuple[3], now_tuple[4], now_tuple[5]
            ),
            "current_shift": current_shift if current_shift is not None else "OFF",
        },
        "shifts": shifts_payload,
    }


def upload_stats_to_github(manual=False):
    global stats_upload_dirty, last_stats_upload_ms
    if not stats_machine_id:
        raise OSError("Stats machine ID not set")
    if not github_stats_token:
        raise OSError("GitHub stats token not set")
    if connect_wifi() is None:
        raise OSError("WiFi not connected")

    api_path = get_stats_repo_api_path(get_stats_status_path())

    status_code, _headers, response_text = github_api_request("GET", api_path, github_stats_token)
    existing = {}
    existing_sha = None
    if status_code == 200:
        response_obj = json.loads(response_text)
        existing_sha = str(response_obj.get("sha", "")).strip() or None
        content_text = str(response_obj.get("content", ""))
        if content_text:
            decoded = base64_decode_text(content_text)
            try:
                existing = json.loads(decoded.decode("utf-8", "ignore"))
            except Exception:
                existing = {}
    elif status_code != 404:
        raise OSError("GitHub read failed ({}): {}".format(status_code, parse_github_error_message(response_text)))

    payload = build_machine_status_payload(existing)
    commit_body = {
        "message": "Update {} status from {}".format(stats_machine_id, APP_VERSION),
        "content": base64_encode_bytes(json_pretty_text(payload).encode("utf-8")),
        "branch": STATS_REPO_BRANCH,
    }
    if existing_sha:
        commit_body["sha"] = existing_sha

    status_code, _headers, _response_text = github_api_request("PUT", api_path, github_stats_token, commit_body)
    if status_code not in (200, 201):
        raise OSError("GitHub write failed ({}): {}".format(status_code, parse_github_error_message(_response_text)))

    stats_upload_dirty = False
    last_stats_upload_ms = time.ticks_ms()
    settings_menu_status.set_text("Stats uploaded: {}".format(stats_machine_id))
    if manual:
        save_state(force=True)


def maybe_upload_stats():
    global last_stats_upload_ms
    if not stats_upload_dirty or not stats_machine_id or not github_stats_token:
        return
    now_ms = time.ticks_ms()
    if time.ticks_diff(now_ms, last_stats_upload_ms) < STATS_UPLOAD_INTERVAL_MS:
        return
    try:
        upload_stats_to_github()
    except Exception as err:
        last_stats_upload_ms = now_ms
        settings_menu_status.set_text(format_status_message("Stats upload failed: {}".format(err)))
        print("Stats upload failed:", err)


def mark_data_dirty():
    global data_dirty, stats_upload_dirty
    data_dirty = True
    stats_upload_dirty = True


def get_state_file_path():
    return "machine_oee_state_{}.json".format(get_reset_day_key())


def build_config_state():
    return {
        "pph_goal": pph_goal,
        "parts_per_cycle": parts_per_cycle,
        "io_invert": io_invert,
        "door_switch_enabled": door_switch_enabled,
        "shift_reset_lock": shift_reset_lock,
        "shift_reset_lead_minutes": shift_reset_lead_minutes,
        "wifi_ssid": wifi_ssid,
        "wifi_password": wifi_password,
        "update_server_url": update_server_url,
        "stats_machine_id": stats_machine_id,
        "stats_token_import_url": stats_token_import_url,
        "github_stats_token": github_stats_token,
        "shift_settings": shift_settings,
    }


def save_config():
    if os is None or json is None:
        return
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(build_config_state(), f)
    except Exception as err:
        print("Config save failed:", err)


def load_config():
    global pph_goal, parts_per_cycle, io_invert, door_switch_enabled, shift_reset_lock
    global shift_reset_lead_minutes, wifi_ssid, wifi_password, update_server_url
    global stats_machine_id, stats_token_import_url, github_stats_token, shift_settings

    if os is None or json is None:
        return

    try:
        with open(CONFIG_FILE, "r") as f:
            state = json.load(f)
    except Exception:
        return

    try:
        pph_goal = int(state.get("pph_goal", pph_goal))
        parts_per_cycle = max(1, int(state.get("parts_per_cycle", parts_per_cycle)))
        io_invert = bool(state.get("io_invert", io_invert))
        door_switch_enabled = bool(state.get("door_switch_enabled", door_switch_enabled))
        shift_reset_lock = bool(state.get("shift_reset_lock", shift_reset_lock))
        shift_reset_lead_minutes = max(0, int(state.get("shift_reset_lead_minutes", shift_reset_lead_minutes)))
        wifi_ssid = str(state.get("wifi_ssid", wifi_ssid))
        wifi_password = str(state.get("wifi_password", wifi_password))
        update_server_url = str(state.get("update_server_url", update_server_url))
        stats_machine_id = str(state.get("stats_machine_id", stats_machine_id)).strip() or DEFAULT_STATS_MACHINE_ID
        stats_token_import_url = normalize_import_url(state.get("stats_token_import_url", stats_token_import_url))
        github_stats_token = str(state.get("github_stats_token", github_stats_token)).strip()
        ensure_machine_option_available(stats_machine_id)
        loaded_shift_settings = state.get("shift_settings", {})
        for shift_name in SHIFT_NAMES:
            shift_settings[shift_name] = normalize_shift_setting(shift_name, loaded_shift_settings.get(shift_name, shift_settings[shift_name]))
    except Exception:
        return


def ensure_config_file():
    if os is None:
        return
    try:
        with open(CONFIG_FILE, "r") as f:
            f.read(1)
    except Exception:
        save_config()


def prune_old_state_files():
    try:
        names = []
        for name in os.listdir():
            if name.startswith("machine_oee_state_") and name.endswith(".json"):
                names.append(name)
        names.sort()
        while len(names) > 2:
            oldest = names.pop(0)
            try:
                os.remove(oldest)
            except OSError:
                break
    except OSError:
        pass


def save_state(force=False):
    global data_dirty, last_save_ms
    now_ms = time.ticks_ms()
    if not force and not data_dirty and time.ticks_diff(now_ms, last_save_ms) < SAVE_INTERVAL_MS:
        return

    state = {
        "good_count": good_count,
        "bad_count": bad_count,
        "pph_goal": pph_goal,
        "parts_per_cycle": parts_per_cycle,
        "io_invert": io_invert,
        "door_switch_enabled": door_switch_enabled,
        "shift_reset_lock": shift_reset_lock,
        "shift_reset_lead_minutes": shift_reset_lead_minutes,
        "daily_production_count": daily_production_count,
        "daily_production_reset_key": daily_production_reset_key,
        "last_daily_production": last_daily_production,
        "daily_production_history": daily_production_history,
        "wifi_ssid": wifi_ssid,
        "wifi_password": wifi_password,
        "update_server_url": update_server_url,
        "stats_machine_id": stats_machine_id,
        "stats_token_import_url": stats_token_import_url,
        "github_stats_token": github_stats_token,
        "shift_settings": shift_settings,
        "set_hour": set_hour,
        "set_minute": set_minute,
        "time_is_set": time_is_set,
        "last_daily_reset_key": last_daily_reset_key,
        "shift_reset_keys": shift_reset_keys,
        "completed_shift_keys": completed_shift_keys,
        "graph_shift_stats": graph_shift_stats,
        "graph_cycle_anchor_epoch": graph_cycle_anchor_epoch,
        "pending_shift_stats": pending_shift_stats,
        "completed_shift_stats": completed_shift_stats,
        "shift_stats": pending_shift_stats,
    }

    try:
        with open(get_state_file_path(), "w") as f:
            json.dump(state, f)
        prune_old_state_files()
        data_dirty = False
        last_save_ms = now_ms
    except Exception as err:
        print("Save failed:", err)


def load_state():
    global good_count, bad_count, pph_goal, parts_per_cycle, io_invert
    global door_switch_enabled, shift_reset_lock
    global shift_reset_lead_minutes, daily_production_count, daily_production_reset_key
    global last_daily_production, daily_production_history, wifi_ssid, wifi_password, update_server_url
    global stats_machine_id, stats_token_import_url, github_stats_token
    global set_hour, set_minute, time_is_set, machine_high, machine_run_start_epoch, machine_run_confirmed
    global pending_machine_run_start_epoch, pending_cycle_shift
    global graph_shift_stats, pending_shift_stats, completed_shift_stats, graph_cycle_anchor_epoch
    global data_dirty, last_save_ms, last_daily_reset_key, shift_reset_keys, completed_shift_keys, shift_settings

    candidates = [get_state_file_path()]
    try:
        names = []
        for name in os.listdir():
            if name.startswith("machine_oee_state_") and name.endswith(".json"):
                names.append(name)
        names.sort(reverse=True)
        for name in names:
            if name not in candidates:
                candidates.append(name)
    except Exception:
        pass

    state = None
    for path in candidates:
        try:
            with open(path, "r") as f:
                state = json.load(f)
            break
        except Exception:
            pass

    if state is None:
        return

    try:
        good_count = int(state.get("good_count", good_count))
        bad_count = int(state.get("bad_count", bad_count))
        pph_goal = int(state.get("pph_goal", pph_goal))
        parts_per_cycle = max(1, int(state.get("parts_per_cycle", parts_per_cycle)))
        io_invert = bool(state.get("io_invert", io_invert))
        door_switch_enabled = bool(state.get("door_switch_enabled", door_switch_enabled))
        shift_reset_lock = bool(state.get("shift_reset_lock", shift_reset_lock))
        shift_reset_lead_minutes = max(0, int(state.get("shift_reset_lead_minutes", shift_reset_lead_minutes)))
        daily_production_count = max(0, int(state.get("daily_production_count", daily_production_count)))
        daily_production_reset_key = str(state.get("daily_production_reset_key", daily_production_reset_key))
        last_daily_production = max(0, int(state.get("last_daily_production", last_daily_production)))
        daily_production_history = normalize_daily_production_history(state.get("daily_production_history", daily_production_history))
        wifi_ssid = str(state.get("wifi_ssid", wifi_ssid))
        wifi_password = str(state.get("wifi_password", wifi_password))
        update_server_url = str(state.get("update_server_url", update_server_url))
        stats_machine_id = str(state.get("stats_machine_id", stats_machine_id)).strip() or DEFAULT_STATS_MACHINE_ID
        stats_token_import_url = normalize_import_url(state.get("stats_token_import_url", stats_token_import_url))
        github_stats_token = str(state.get("github_stats_token", github_stats_token)).strip()
        ensure_machine_option_available(stats_machine_id)
        set_hour = int(state.get("set_hour", set_hour))
        set_minute = int(state.get("set_minute", set_minute))
        time_is_set = bool(state.get("time_is_set", time_is_set))
        loaded_shift_settings = state.get("shift_settings", {})
        for shift_name in SHIFT_NAMES:
            shift_settings[shift_name] = normalize_shift_setting(shift_name, loaded_shift_settings.get(shift_name, shift_settings[shift_name]))
        last_daily_reset_key = state.get("last_daily_reset_key", "")
        loaded_shift_reset_keys = state.get("shift_reset_keys", {})
        loaded_completed_shift_keys = state.get("completed_shift_keys", {})
        loaded_graph_anchor_epoch = state.get("graph_cycle_anchor_epoch", {})
        for shift_name in SHIFT_NAMES:
            shift_reset_keys[shift_name] = loaded_shift_reset_keys.get(shift_name, shift_reset_keys[shift_name])
            completed_shift_keys[shift_name] = loaded_completed_shift_keys.get(shift_name, completed_shift_keys[shift_name])
            graph_cycle_anchor_epoch[shift_name] = loaded_graph_anchor_epoch.get(shift_name, graph_cycle_anchor_epoch[shift_name])

        loaded_graph_stats = state.get("graph_shift_stats", state.get("shift_stats", {}))
        loaded_pending_stats = state.get("pending_shift_stats", state.get("shift_stats", {}))
        loaded_completed_stats = state.get("completed_shift_stats", state.get("shift_stats", {}))
        for shift_name in SHIFT_NAMES:
            graph_shift_stats[shift_name] = clone_shift_bucket(loaded_graph_stats.get(shift_name, graph_shift_stats[shift_name]))
            pending_shift_stats[shift_name] = clone_shift_bucket(loaded_pending_stats.get(shift_name, pending_shift_stats[shift_name]))
            completed_shift_stats[shift_name] = clone_shift_bucket(loaded_completed_stats.get(shift_name, completed_shift_stats[shift_name]))
        raw_value = run_pin.value()
        machine_high = is_signal_active(raw_value)
        machine_run_confirmed = machine_high
        machine_run_start_epoch = time.time() if machine_high else None
        pending_machine_run_start_epoch = None
        pending_cycle_shift = None
    except Exception:
        return

    data_dirty = False
    last_save_ms = time.ticks_ms()
    return


def initialize_shift_reset_keys():
    for shift_name in SHIFT_NAMES:
        if not shift_reset_keys[shift_name]:
            shift_reset_keys[shift_name] = get_shift_reset_key(shift_name)


def clamp_counts():
    global good_count, bad_count
    if good_count < 0:
        good_count = 0
    if bad_count < 0:
        bad_count = 0


def add_good_part():
    global good_count, bad_count, daily_production_count
    good_count += 1
    daily_production_count += 1
    if bad_count > 0:
        bad_count -= 1
    shift_name = get_shift()
    if shift_name is not None:
        pending_shift_stats[shift_name]["good"] += 1
    mark_data_dirty()


def add_bad_part():
    global good_count, bad_count, daily_production_count
    if good_count > 0:
        good_count -= 1
    if daily_production_count > 0:
        daily_production_count -= 1
    bad_count += 1
    shift_name = get_shift()
    if shift_name is not None:
        pending_shift_stats[shift_name]["bad"] += 1
    mark_data_dirty()


def auto_complete_cycle(shift_name=None, include_pph=False):
    global good_count, daily_production_count
    produced = max(1, int(parts_per_cycle))
    good_count += produced
    daily_production_count += produced
    if shift_name is not None:
        graph_shift_stats[shift_name]["good"] += produced
        graph_shift_stats[shift_name]["cycle_count"] += 1
        graph_shift_stats[shift_name]["produced_parts"] += produced
        pending_shift_stats[shift_name]["good"] += produced
        pending_shift_stats[shift_name]["cycle_count"] += 1
        pending_shift_stats[shift_name]["produced_parts"] += produced
        if include_pph:
            graph_shift_stats[shift_name]["pph_cycle_count"] += 1
            graph_shift_stats[shift_name]["pph_produced_parts"] += produced
            pending_shift_stats[shift_name]["pph_cycle_count"] += 1
            pending_shift_stats[shift_name]["pph_produced_parts"] += produced
    mark_data_dirty()


def update_shift_totals():
    return


def reset_good_count():
    global good_count
    good_count = 0
    clamp_counts()
    mark_data_dirty()


def reset_bad_count():
    global bad_count
    bad_count = 0
    clamp_counts()
    mark_data_dirty()


def reset_graph_shift_data(shift_name):
    clear_shift_bucket(graph_shift_stats[shift_name])
    graph_cycle_anchor_epoch[shift_name] = None
    mark_data_dirty()


def reset_pending_shift_data(shift_name, update_key=True):
    clear_shift_bucket(pending_shift_stats[shift_name])
    if update_key:
        shift_reset_keys[shift_name] = get_shift_reset_key(shift_name)
    mark_data_dirty()


def reset_completed_shift_data(shift_name, clear_key=False):
    clear_shift_bucket(completed_shift_stats[shift_name])
    if clear_key:
        completed_shift_keys[shift_name] = ""
    mark_data_dirty()


def reset_shift_data(update_reset_key=True):
    global current_cycle_start_epoch, current_cycle_shift, current_cycle_with_load_seconds
    global current_machine_run_seconds, last_cycle_complete_epoch, last_daily_reset_key

    for shift_name in SHIFT_NAMES:
        reset_graph_shift_data(shift_name)
        reset_pending_shift_data(shift_name, update_key=False)
        reset_completed_shift_data(shift_name, clear_key=True)
        shift_reset_keys[shift_name] = ""

    current_cycle_start_epoch = None
    current_cycle_shift = None
    current_cycle_with_load_seconds = 0
    current_machine_run_seconds = 0
    last_cycle_complete_epoch = time.time()

    if update_reset_key:
        last_daily_reset_key = get_reset_day_key()

    mark_data_dirty()


def ensure_daily_reset():
    global last_daily_reset_key
    last_daily_reset_key = get_reset_day_key()


def reset_daily_production(manual=False):
    global daily_production_count, daily_production_reset_key
    daily_production_count = 0
    daily_production_reset_key = get_daily_production_key()
    mark_data_dirty()
    if manual:
        save_state(force=True)


def ensure_daily_production_reset():
    global daily_production_count, daily_production_reset_key
    current_key = get_daily_production_key()
    if not daily_production_reset_key:
        daily_production_reset_key = current_key
        return

    if daily_production_reset_key != current_key:
        archive_daily_production(daily_production_reset_key, daily_production_count)
        daily_production_count = 0
        daily_production_reset_key = current_key
        stats_reset_status.set_text("Daily production reset")
        mark_data_dirty()
        save_state(force=True)


def ensure_shift_period_reset():
    if shift_reset_lock:
        return
    changed = False
    for shift_name in SHIFT_NAMES:
        current_shift_key = get_shift_reset_key(shift_name)
        if shift_reset_keys[shift_name] != current_shift_key:
            reset_graph_shift_data(shift_name)
            reset_pending_shift_data(shift_name, update_key=True)
            changed = True
    if changed:
        save_state(force=True)


def finalize_completed_shifts():
    changed = False
    now_epoch = time.time()
    for shift_name in SHIFT_NAMES:
        shift_key = shift_reset_keys[shift_name]
        if not shift_key or completed_shift_keys[shift_name] == shift_key:
            continue

        shift_end_epoch = get_shift_end_epoch(shift_name, shift_key)
        if shift_end_epoch is None or now_epoch < shift_end_epoch:
            continue

        completed_shift_stats[shift_name] = clone_shift_bucket(pending_shift_stats[shift_name])
        completed_shift_keys[shift_name] = shift_key
        changed = True

    if changed:
        mark_data_dirty()
        save_state(force=True)


def show_goal_popup():
    goal_textarea.set_text(str(pph_goal))
    goal_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    goal_popup.move_foreground()


def hide_goal_popup():
    goal_popup.add_flag(lv.obj.FLAG.HIDDEN)


def show_count_popup(target_name, current_value):
    global count_edit_target
    count_edit_target = target_name
    if target_name == "good":
        count_popup_title.set_text("SET GOOD COUNT")
    else:
        count_popup_title.set_text("SET BAD COUNT")
    count_textarea.set_text(str(current_value))
    count_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    count_popup.move_foreground()


def hide_count_popup():
    global count_edit_target
    count_edit_target = None
    count_popup.add_flag(lv.obj.FLAG.HIDDEN)


def apply_manual_count(target_name, new_value):
    global good_count, bad_count

    if new_value < 0:
        new_value = 0

    if target_name == "good":
        good_count = new_value
    elif target_name == "bad":
        bad_count = new_value

    clamp_counts()
    mark_data_dirty()


def hide_settings_number_popup():
    global settings_number_target
    settings_number_target = None
    if settings_number_popup is not None:
        settings_number_popup.add_flag(lv.obj.FLAG.HIDDEN)


def show_settings_number_popup(target_name, title_text, current_value, max_length=6):
    global settings_number_target
    ensure_settings_number_popup()
    settings_number_target = target_name
    settings_number_title.set_text(title_text)
    settings_number_textarea.set_max_length(max_length)
    settings_number_textarea.set_text(str(current_value))
    settings_number_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    settings_number_popup.move_foreground()


def hide_wifi_scan_popup():
    if wifi_scan_popup is not None:
        wifi_scan_popup.add_flag(lv.obj.FLAG.HIDDEN)


def hide_wifi_password_popup():
    if wifi_password_popup is not None:
        wifi_password_popup.add_flag(lv.obj.FLAG.HIDDEN)


def hide_shift_hours_popup():
    if shift_hours_popup is not None:
        shift_hours_popup.add_flag(lv.obj.FLAG.HIDDEN)


def hide_invert_popup():
    if invert_popup is not None:
        invert_popup.add_flag(lv.obj.FLAG.HIDDEN)


def hide_io_check_popup():
    if io_check_popup is not None:
        io_check_popup.add_flag(lv.obj.FLAG.HIDDEN)


def ensure_software_update_popup():
    global software_update_popup, software_update_status, software_update_list
    global software_update_refresh, software_update_ok, software_update_stats, software_update_close

    if software_update_popup is not None:
        return

    software_update_popup = lv.obj(ui_SETTINGS_MENU)
    software_update_popup.set_size(640, 360)
    software_update_popup.center()
    stabilize_widget(software_update_popup)
    software_update_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    software_update_popup.add_flag(lv.obj.FLAG.HIDDEN)

    software_update_title = lv.label(software_update_popup)
    software_update_title.set_text("SOFTWARE UPDATE")
    software_update_title.align(lv.ALIGN.TOP_MID, 0, 12)
    software_update_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    software_update_hint = lv.label(software_update_popup)
    software_update_hint.set_text("Refresh versions, tap one to select, then press OK")
    software_update_hint.align(lv.ALIGN.TOP_LEFT, 18, 52)
    software_update_hint.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(software_update_hint, 600, lv.TEXT_ALIGN.LEFT)

    software_update_status = lv.label(software_update_popup)
    software_update_status.set_text("Current: {}  Source: GitHub".format(APP_VERSION))
    software_update_status.align(lv.ALIGN.TOP_LEFT, 18, 82)
    software_update_status.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(software_update_status, 600, lv.TEXT_ALIGN.LEFT)

    software_update_list = lv.list(software_update_popup)
    software_update_list.set_size(600, 170)
    software_update_list.align(lv.ALIGN.TOP_MID, 0, 130)
    stabilize_widget(software_update_list)
    software_update_list.set_style_bg_color(lv.color_hex(0x2D2D2D), lv.PART.MAIN | lv.STATE.DEFAULT)
    software_update_list.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)

    software_update_refresh = make_button(software_update_popup, "REFRESH", -210, 150, 110, 40, 0x04BE2D)
    software_update_stats = make_button(software_update_popup, "STATS", -70, 150, 110, 40, 0x465AC4)
    software_update_ok = make_button(software_update_popup, "OK", 70, 150, 110, 40, 0x0A0ACC)
    software_update_close = make_button(software_update_popup, "CLOSE", 210, 150, 110, 40, 0xC32331)
    software_update_refresh.add_event_cb(software_update_refresh_event, lv.EVENT.ALL, None)
    software_update_stats.add_event_cb(software_update_stats_event, lv.EVENT.ALL, None)
    software_update_ok.add_event_cb(software_update_ok_event, lv.EVENT.ALL, None)
    software_update_close.add_event_cb(software_update_close_event, lv.EVENT.ALL, None)


def hide_software_update_popup():
    if software_update_popup is not None:
        software_update_popup.add_flag(lv.obj.FLAG.HIDDEN)


def hide_stats_config_popup():
    if stats_config_popup is not None:
        stats_config_popup.add_flag(lv.obj.FLAG.HIDDEN)


def refresh_stats_config_machine_button():
    if stats_config_machine_button_label is None:
        return
    machine_id = str(stats_config_machine_value).strip() or DEFAULT_STATS_MACHINE_ID
    machine_name = get_machine_display_name(machine_id)
    stats_config_machine_button_label.set_text("Machine\n{}".format(machine_name))
    stats_config_machine_button_label.center()


def stats_config_focus_import_url_event(e):
    if e.get_code() == lv.EVENT.CLICKED or e.get_code() == lv.EVENT.FOCUSED:
        if stats_config_kb is not None and stats_config_import_url_textarea is not None:
            stats_config_kb.set_textarea(stats_config_import_url_textarea)


def stats_config_focus_token_event(e):
    if e.get_code() == lv.EVENT.CLICKED or e.get_code() == lv.EVENT.FOCUSED:
        if stats_config_kb is not None and stats_config_token_textarea is not None:
            stats_config_kb.set_textarea(stats_config_token_textarea)


def ensure_stats_config_popup():
    global stats_config_popup, stats_config_machine_button, stats_config_machine_button_label
    global stats_config_import_url_textarea
    global stats_config_token_textarea, stats_config_status, stats_config_kb
    global stats_config_save, stats_config_import, stats_config_upload, stats_config_close

    if stats_config_popup is not None:
        return

    stats_config_popup = lv.obj(ui_SETTINGS_MENU)
    stats_config_popup.set_size(640, 420)
    stats_config_popup.center()
    stabilize_widget(stats_config_popup)
    stats_config_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    stats_config_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    stats_config_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    stats_config_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    stats_config_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    stats_config_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    stats_config_popup.add_flag(lv.obj.FLAG.HIDDEN)

    stats_title = lv.label(stats_config_popup)
    stats_title.set_text("GITHUB STATS")
    stats_title.align(lv.ALIGN.TOP_MID, 0, 12)
    stats_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    stats_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    stats_info = lv.label(stats_config_popup)
    stats_info.set_text("Stats: {}/{}   Notes: {}/{}".format(STATS_REPO_OWNER, STATS_REPO_NAME, NOTES_REPO_OWNER, NOTES_REPO_NAME))
    stats_info.align(lv.ALIGN.TOP_LEFT, 18, 50)
    stats_info.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(stats_info, 600, lv.TEXT_ALIGN.LEFT)

    machine_label = lv.label(stats_config_popup)
    machine_label.set_text("Machine")
    machine_label.align(lv.ALIGN.TOP_LEFT, 18, 76)
    machine_label.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)

    stats_config_machine_button, stats_config_machine_button_label = make_settings_button(
        stats_config_popup,
        "Machine\nMatsuura",
        0,
        -87,
    )
    stats_config_machine_button.set_size(300, 82)
    stats_config_machine_button.add_event_cb(machine_picker_open_event, lv.EVENT.ALL, None)
    refresh_stats_config_machine_button()

    import_url_label = lv.label(stats_config_popup)
    import_url_label.set_text("PC Token URL")
    import_url_label.align(lv.ALIGN.TOP_LEFT, 18, 144)
    import_url_label.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)

    stats_config_import_url_textarea = lv.textarea(stats_config_popup)
    stats_config_import_url_textarea.set_size(600, 40)
    stats_config_import_url_textarea.align(lv.ALIGN.TOP_LEFT, 18, 170)
    stats_config_import_url_textarea.set_one_line(True)
    stats_config_import_url_textarea.set_placeholder_text("http://192.168.1.50:8766")
    stabilize_widget(stats_config_import_url_textarea)
    stats_config_import_url_textarea.add_event_cb(stats_config_focus_import_url_event, lv.EVENT.ALL, None)

    token_label = lv.label(stats_config_popup)
    token_label.set_text("GitHub Token")
    token_label.align(lv.ALIGN.TOP_LEFT, 18, 214)
    token_label.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)

    stats_config_token_textarea = lv.textarea(stats_config_popup)
    stats_config_token_textarea.set_size(600, 40)
    stats_config_token_textarea.align(lv.ALIGN.TOP_LEFT, 18, 240)
    stats_config_token_textarea.set_one_line(True)
    stats_config_token_textarea.set_password_mode(True)
    stats_config_token_textarea.set_placeholder_text("github_pat_...")
    stabilize_widget(stats_config_token_textarea)
    stats_config_token_textarea.add_event_cb(stats_config_focus_token_event, lv.EVENT.ALL, None)

    stats_config_status = lv.label(stats_config_popup)
    stats_config_status.set_text("")
    stats_config_status.align(lv.ALIGN.TOP_LEFT, 18, 286)
    stats_config_status.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(stats_config_status, 600, lv.TEXT_ALIGN.LEFT)

    stats_config_kb = lv.keyboard(stats_config_popup)
    stats_config_kb.set_size(600, 70)
    stats_config_kb.align(lv.ALIGN.BOTTOM_MID, 0, -14)
    stats_config_kb.set_textarea(stats_config_token_textarea)
    stabilize_widget(stats_config_kb)

    stats_config_save = make_button(stats_config_popup, "SAVE", -180, -82, 100, 40, 0x04BE2D)
    stats_config_import = make_button(stats_config_popup, "IMPORT", -60, -82, 100, 40, 0x0A0ACC)
    stats_config_upload = make_button(stats_config_popup, "UPLOAD", 60, -82, 100, 40, 0x465AC4)
    stats_config_close = make_button(stats_config_popup, "CLOSE", 180, -82, 100, 40, 0xC32331)
    stats_config_save.add_event_cb(stats_config_save_event, lv.EVENT.ALL, None)
    stats_config_import.add_event_cb(stats_config_import_event, lv.EVENT.ALL, None)
    stats_config_upload.add_event_cb(stats_config_upload_event, lv.EVENT.ALL, None)
    stats_config_close.add_event_cb(stats_config_close_event, lv.EVENT.ALL, None)


def show_stats_config_popup():
    global stats_config_machine_value
    ensure_stats_config_popup()
    stats_config_machine_value = stats_machine_id
    refresh_stats_config_machine_button()
    stats_config_import_url_textarea.set_text(stats_token_import_url)
    stats_config_token_textarea.set_text(github_stats_token)
    stats_config_kb.set_textarea(stats_config_token_textarea)
    ensure_machine_option_available(stats_machine_id)
    stats_config_status.set_text(
        "Machine: {}  Status: {}  Notes: {}/".format(
            format_machine_choice(stats_machine_id),
            get_stats_status_path(),
            get_notes_machine_path(),
        )
    )
    hide_software_update_popup()
    stats_config_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    stats_config_popup.move_foreground()


def clear_software_update_list():
    global software_update_callbacks, software_update_selected_entry
    global software_update_selected_btn, software_update_entry_buttons
    software_update_callbacks = []
    software_update_selected_entry = None
    software_update_selected_btn = None
    software_update_entry_buttons = []
    try:
        if software_update_list is not None:
            software_update_list.clean()
    except Exception:
        pass


def set_software_update_entry_button_style(btn, selected):
    if btn is None:
        return
    if selected:
        btn.set_style_bg_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_border_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_border_width(2, lv.PART.MAIN | lv.STATE.DEFAULT)
    else:
        btn.set_style_bg_color(lv.color_hex(0x2D2D2D), lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_border_color(lv.color_hex(0x555555), lv.PART.MAIN | lv.STATE.DEFAULT)
        btn.set_style_border_width(1, lv.PART.MAIN | lv.STATE.DEFAULT)


def select_software_update_entry(entry, btn):
    global software_update_selected_entry, software_update_selected_btn
    if software_update_selected_btn is not None:
        set_software_update_entry_button_style(software_update_selected_btn, False)
    software_update_selected_entry = entry
    software_update_selected_btn = btn
    set_software_update_entry_button_style(btn, True)
    software_update_status.set_text("Selected: {}  Press OK to install".format(entry.get("version", "")))


def make_software_update_entry_event(entry, btn):
    def _event(e):
        if e.get_code() != lv.EVENT.CLICKED:
            return
        select_software_update_entry(entry, btn)
    return _event


def hide_machine_picker_popup():
    if machine_picker_popup is not None:
        machine_picker_popup.add_flag(lv.obj.FLAG.HIDDEN)


def clear_machine_picker_list():
    global machine_picker_callbacks
    machine_picker_callbacks = []
    try:
        if machine_picker_list is not None:
            machine_picker_list.clean()
    except Exception:
        pass


def select_machine_option(entry):
    global stats_config_machine_value
    machine_id = str(entry.get("id", "")).strip()
    if not machine_id:
        return
    stats_config_machine_value = machine_id
    refresh_stats_config_machine_button()
    if stats_config_status is not None:
        stats_config_status.set_text("Selected machine: {}".format(format_machine_choice(machine_id)))
    hide_machine_picker_popup()


def make_machine_picker_event(entry):
    def _event(e):
        if e.get_code() != lv.EVENT.CLICKED:
            return
        select_machine_option(entry)
    return _event


def ensure_machine_picker_popup():
    global machine_picker_popup, machine_picker_list, machine_picker_status
    global machine_picker_close, machine_picker_refresh

    if machine_picker_popup is not None:
        return

    machine_picker_popup = lv.obj(ui_SETTINGS_MENU)
    machine_picker_popup.set_size(520, 360)
    machine_picker_popup.center()
    stabilize_widget(machine_picker_popup)
    machine_picker_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    machine_picker_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    machine_picker_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    machine_picker_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    machine_picker_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    machine_picker_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    machine_picker_popup.add_flag(lv.obj.FLAG.HIDDEN)

    picker_title = lv.label(machine_picker_popup)
    picker_title.set_text("SELECT MACHINE")
    picker_title.align(lv.ALIGN.TOP_MID, 0, 12)
    picker_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    picker_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    machine_picker_status = lv.label(machine_picker_popup)
    machine_picker_status.set_text("")
    machine_picker_status.align(lv.ALIGN.TOP_LEFT, 18, 50)
    machine_picker_status.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
    stabilize_value_label(machine_picker_status, 480, lv.TEXT_ALIGN.LEFT)

    machine_picker_list = lv.list(machine_picker_popup)
    machine_picker_list.set_size(480, 210)
    machine_picker_list.align(lv.ALIGN.TOP_MID, 0, 84)
    stabilize_widget(machine_picker_list)

    machine_picker_refresh = make_button(machine_picker_popup, "REFRESH", -90, 148, 120, 40, 0x04BE2D)
    machine_picker_close = make_button(machine_picker_popup, "CLOSE", 90, 148, 120, 40, 0xC32331)
    machine_picker_refresh.add_event_cb(machine_picker_refresh_event, lv.EVENT.ALL, None)
    machine_picker_close.add_event_cb(machine_picker_close_event, lv.EVENT.ALL, None)


def refresh_machine_picker_popup():
    clear_machine_picker_list()
    ensure_machine_option_available(stats_config_machine_value)

    try:
        options = load_machine_options_from_repo()
        machine_picker_status.set_text("Loaded {} machines".format(len(options)))
    except Exception as err:
        options = machine_options_cache
        machine_picker_status.set_text(format_status_message("Using saved list: {}".format(err), 72))

    for entry in options:
        button = machine_picker_list.add_btn(lv.SYMBOL.DRIVE, format_machine_choice(entry.get("id", "")))
        button.clear_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
        callback = make_machine_picker_event(entry)
        machine_picker_callbacks.append(callback)
        button.add_event_cb(callback, lv.EVENT.ALL, None)


def show_machine_picker_popup():
    ensure_machine_picker_popup()
    refresh_machine_picker_popup()
    machine_picker_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    machine_picker_popup.move_foreground()


def machine_picker_open_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_machine_picker_popup()


def machine_picker_refresh_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    refresh_machine_picker_popup()


def machine_picker_close_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_machine_picker_popup()


def ensure_settings_number_popup():
    global settings_number_popup, settings_number_title, settings_number_textarea, settings_number_kb
    if settings_number_popup is not None:
        return

    settings_number_popup = lv.obj(ui_SETTINGS_MENU)
    settings_number_popup.set_size(320, 360)
    settings_number_popup.center()
    stabilize_widget(settings_number_popup)
    settings_number_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    settings_number_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    settings_number_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    settings_number_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    settings_number_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    settings_number_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    settings_number_popup.add_flag(lv.obj.FLAG.HIDDEN)

    settings_number_title = lv.label(settings_number_popup)
    settings_number_title.set_text("SET VALUE")
    settings_number_title.align(lv.ALIGN.TOP_MID, 0, 12)
    settings_number_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    settings_number_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    settings_number_textarea = lv.textarea(settings_number_popup)
    settings_number_textarea.set_size(250, 50)
    settings_number_textarea.align(lv.ALIGN.TOP_MID, 0, 48)
    settings_number_textarea.set_one_line(True)
    settings_number_textarea.set_max_length(6)
    settings_number_textarea.set_text("0")
    stabilize_widget(settings_number_textarea)

    settings_number_kb = lv.btnmatrix(settings_number_popup)
    settings_number_kb.set_map([
        "1", "2", "3", "\n",
        "4", "5", "6", "\n",
        "7", "8", "9", "\n",
        "CLR", "0", "BKSP", "\n",
        "OK", "CANCEL", ""
    ])
    settings_number_kb.set_size(280, 210)
    settings_number_kb.align(lv.ALIGN.BOTTOM_MID, 0, -12)
    stabilize_widget(settings_number_kb)
    settings_number_kb.add_event_cb(settings_number_kb_event, lv.EVENT.ALL, None)


def ensure_wifi_scan_popup():
    global wifi_scan_popup, wifi_scan_status, wifi_scan_refresh, wifi_scan_close, wifi_list
    if wifi_scan_popup is not None:
        return

    wifi_scan_popup = lv.obj(ui_SETTINGS_MENU)
    wifi_scan_popup.set_size(520, 360)
    wifi_scan_popup.center()
    stabilize_widget(wifi_scan_popup)
    wifi_scan_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_scan_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_scan_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_scan_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_scan_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_scan_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    wifi_scan_popup.add_flag(lv.obj.FLAG.HIDDEN)

    wifi_scan_title = lv.label(wifi_scan_popup)
    wifi_scan_title.set_text("WIFI SETTINGS")
    wifi_scan_title.align(lv.ALIGN.TOP_MID, 0, 12)
    wifi_scan_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_scan_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    wifi_scan_status = lv.label(wifi_scan_popup)
    wifi_scan_status.set_text("Tap refresh to scan")
    wifi_scan_status.align(lv.ALIGN.TOP_LEFT, 18, 54)
    wifi_scan_status.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)

    wifi_scan_refresh = make_button(wifi_scan_popup, "REFRESH", -120, -92, 110, 44, 0x0A0ACC)
    wifi_scan_close = make_button(wifi_scan_popup, "CLOSE", 120, -92, 110, 44, 0xC32331)
    wifi_scan_refresh.add_event_cb(wifi_scan_refresh_event, lv.EVENT.ALL, None)
    wifi_scan_close.add_event_cb(wifi_scan_close_event, lv.EVENT.ALL, None)

    wifi_list = lv.list(wifi_scan_popup)
    wifi_list.set_size(470, 200)
    wifi_list.align(lv.ALIGN.BOTTOM_MID, 0, -14)
    stabilize_widget(wifi_list)
    wifi_list.set_style_bg_color(lv.color_hex(0x2D2D2D), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_list.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)


def ensure_wifi_password_popup():
    global wifi_password_popup, wifi_password_ssid, wifi_password_status
    global wifi_password_textarea, wifi_password_connect, wifi_password_cancel
    if wifi_password_popup is not None:
        return

    wifi_password_popup = lv.obj(ui_SETTINGS_MENU)
    wifi_password_popup.set_size(620, 360)
    wifi_password_popup.center()
    stabilize_widget(wifi_password_popup)
    wifi_password_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_password_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_password_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_password_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_password_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_password_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    wifi_password_popup.add_flag(lv.obj.FLAG.HIDDEN)

    wifi_password_title = lv.label(wifi_password_popup)
    wifi_password_title.set_text("CONNECT WIFI")
    wifi_password_title.align(lv.ALIGN.TOP_MID, 0, 12)
    wifi_password_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    wifi_password_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    wifi_password_ssid = lv.label(wifi_password_popup)
    wifi_password_ssid.set_text("SSID: ")
    wifi_password_ssid.align(lv.ALIGN.TOP_LEFT, 18, 52)
    wifi_password_ssid.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)

    wifi_password_status = lv.label(wifi_password_popup)
    wifi_password_status.set_text("")
    wifi_password_status.align(lv.ALIGN.TOP_LEFT, 18, 82)
    wifi_password_status.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)

    wifi_password_textarea = lv.textarea(wifi_password_popup)
    wifi_password_textarea.set_size(580, 42)
    wifi_password_textarea.align(lv.ALIGN.TOP_MID, 0, 114)
    wifi_password_textarea.set_one_line(True)
    wifi_password_textarea.set_password_mode(True)
    wifi_password_textarea.set_placeholder_text("Password")
    stabilize_widget(wifi_password_textarea)

    wifi_password_kb = lv.keyboard(wifi_password_popup)
    wifi_password_kb.set_size(580, 140)
    wifi_password_kb.align(lv.ALIGN.BOTTOM_MID, 0, -12)
    wifi_password_kb.set_textarea(wifi_password_textarea)
    stabilize_widget(wifi_password_kb)

    wifi_password_connect = make_button(wifi_password_popup, "CONNECT", -120, -22, 120, 40, 0x04BE2D)
    wifi_password_cancel = make_button(wifi_password_popup, "CANCEL", 120, -22, 120, 40, 0xC32331)
    wifi_password_connect.add_event_cb(wifi_password_connect_event, lv.EVENT.ALL, None)
    wifi_password_cancel.add_event_cb(wifi_password_cancel_event, lv.EVENT.ALL, None)


def ensure_shift_hours_popup():
    global shift_hours_popup, shift_hours_widgets, shift_hours_save, shift_hours_cancel
    if shift_hours_popup is not None:
        return

    shift_hours_popup = lv.obj(ui_SETTINGS_MENU)
    shift_hours_popup.set_size(660, 360)
    shift_hours_popup.center()
    stabilize_widget(shift_hours_popup)
    shift_hours_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    shift_hours_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    shift_hours_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    shift_hours_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    shift_hours_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    shift_hours_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    shift_hours_popup.add_flag(lv.obj.FLAG.HIDDEN)

    shift_hours_title = lv.label(shift_hours_popup)
    shift_hours_title.set_text("SHIFT HOURS")
    shift_hours_title.align(lv.ALIGN.TOP_MID, 0, 12)
    shift_hours_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    shift_hours_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    shift_hours_header = lv.label(shift_hours_popup)
    shift_hours_header.set_text("Enable      Start                End")
    shift_hours_header.align(lv.ALIGN.TOP_LEFT, 148, 50)
    shift_hours_header.set_style_text_color(lv.color_hex(0xAAAAAA), lv.PART.MAIN | lv.STATE.DEFAULT)

    shift_hours_widgets = {
        "A": make_shift_hours_row(shift_hours_popup, "A", 96),
        "B": make_shift_hours_row(shift_hours_popup, "B", 154),
        "C": make_shift_hours_row(shift_hours_popup, "C", 212),
    }

    shift_hours_save = make_button(shift_hours_popup, "SAVE", -120, 126, 120, 44, 0x04BE2D)
    shift_hours_cancel = make_button(shift_hours_popup, "CANCEL", 120, 126, 120, 44, 0xC32331)
    shift_hours_save.add_event_cb(shift_hours_save_event, lv.EVENT.ALL, None)
    shift_hours_cancel.add_event_cb(shift_hours_cancel_event, lv.EVENT.ALL, None)


def ensure_invert_popup():
    global invert_popup, invert_checkbox, invert_save, invert_cancel
    if invert_popup is not None:
        return

    invert_popup = lv.obj(ui_SETTINGS_MENU)
    invert_popup.set_size(340, 220)
    invert_popup.center()
    stabilize_widget(invert_popup)
    invert_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    invert_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    invert_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    invert_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    invert_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    invert_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    invert_popup.add_flag(lv.obj.FLAG.HIDDEN)

    invert_title = lv.label(invert_popup)
    invert_title.set_text("CYCLE START INVERT")
    invert_title.align(lv.ALIGN.TOP_MID, 0, 16)
    invert_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    invert_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    invert_checkbox = lv.checkbox(invert_popup)
    invert_checkbox.set_text("Invert IO44 active state")
    invert_checkbox.align(lv.ALIGN.CENTER, 0, -12)
    stabilize_widget(invert_checkbox)

    invert_save = make_button(invert_popup, "SAVE", -90, 72, 100, 42, 0x04BE2D)
    invert_cancel = make_button(invert_popup, "CANCEL", 90, 72, 100, 42, 0xC32331)
    invert_save.add_event_cb(invert_save_event, lv.EVENT.ALL, None)
    invert_cancel.add_event_cb(invert_cancel_event, lv.EVENT.ALL, None)


def ensure_io_check_popup():
    global io_check_popup, io_check_label, io_check_close
    if io_check_popup is not None:
        return

    io_check_popup = lv.obj(ui_SETTINGS_MENU)
    io_check_popup.set_size(320, 180)
    io_check_popup.center()
    stabilize_widget(io_check_popup)
    io_check_popup.set_style_bg_color(lv.color_hex(0x222222), lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_popup.set_style_bg_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_popup.set_style_border_color(lv.color_hex(0x0A0ACC), lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_popup.set_style_border_width(3, lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_popup.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_popup.clear_flag(lv.obj.FLAG.SCROLLABLE)
    io_check_popup.add_flag(lv.obj.FLAG.HIDDEN)

    io_check_title = lv.label(io_check_popup)
    io_check_title.set_text("IO CHECK")
    io_check_title.align(lv.ALIGN.TOP_MID, 0, 16)
    io_check_title.set_style_text_color(lv.color_hex(0xFCA903), lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_title.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    io_check_label = lv.label(io_check_popup)
    io_check_label.set_text("IO44 = LOW")
    io_check_label.align(lv.ALIGN.CENTER, 0, -10)
    io_check_label.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN | lv.STATE.DEFAULT)
    io_check_label.set_style_text_font(safe_font("font_montserrat_20"), lv.PART.MAIN | lv.STATE.DEFAULT)

    io_check_close = make_button(io_check_popup, "CLOSE", 0, 54, 100, 40, 0xC32331)
    io_check_close.add_event_cb(io_check_close_event, lv.EVENT.ALL, None)


def hide_all_settings_popups():
    hide_settings_number_popup()
    hide_wifi_scan_popup()
    hide_wifi_password_popup()
    hide_shift_hours_popup()
    hide_invert_popup()
    hide_io_check_popup()
    hide_software_update_popup()
    hide_stats_config_popup()
    hide_machine_picker_popup()


def refresh_io_check_label():
    if io_check_label is None:
        return
    set_cached_label_text(
        "io_check_popup_label",
        io_check_label,
        "IO44 = {}".format("LOW" if run_pin.value() == 0 else "HIGH"),
    )


def get_ui_refresh_interval_ms():
    current_screen = lv.scr_act()
    if current_screen == ui_SETTINGS_MENU:
        return UI_REFRESH_SETTINGS_MS
    if current_screen == ui_SETTINGS:
        return UI_REFRESH_SETTINGS_MS
    if machine_high or current_cycle_start_epoch is not None:
        return UI_REFRESH_ACTIVE_MS
    return UI_REFRESH_IDLE_MS


def show_software_update_popup():
    ensure_software_update_popup()
    refresh_software_update_popup()
    software_update_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    software_update_popup.move_foreground()


def refresh_software_update_popup():
    global software_update_entries
    ensure_software_update_popup()
    clear_software_update_list()
    software_update_entries = []

    software_update_status.set_text("Checking GitHub for versions...")
    maybe_update_ui()

    if connect_wifi() is None:
        software_update_status.set_text("WiFi not connected")
        return

    try:
        manifest = fetch_ota_manifest()
        software_update_entries = normalize_ota_entries(manifest)
        if not software_update_entries:
            software_update_status.set_text("No OTA versions found on GitHub")
            return

        software_update_status.set_text("Current: {}  Tap a version to select".format(APP_VERSION))
        download_icon = ""
        try:
            download_icon = lv.SYMBOL.DOWN
        except Exception:
            download_icon = ""

        for entry in software_update_entries:
            label = entry["version"]
            if entry.get("latest"):
                label += "  latest"
            if entry["version"] == APP_VERSION:
                label += "  current"
            btn = software_update_list.add_btn(download_icon, label)
            stabilize_button(btn)
            set_software_update_entry_button_style(btn, False)
            software_update_entry_buttons.append(btn)
            callback = make_software_update_entry_event(entry, btn)
            software_update_callbacks.append(callback)
            btn.add_event_cb(callback, lv.EVENT.ALL, None)
    except Exception as err:
        software_update_status.set_text("GitHub update check failed: {}".format(err))


def maybe_update_ui():
    global last_ui_refresh_ms
    now_ms = time.ticks_ms()
    if time.ticks_diff(now_ms, last_ui_refresh_ms) < get_ui_refresh_interval_ms():
        return
    last_ui_refresh_ms = now_ms
    update_ui()


def refresh_shift_hours_popup():
    ensure_shift_hours_popup()
    for shift_name in SHIFT_NAMES:
        config = shift_settings[shift_name]
        widgets = shift_hours_widgets[shift_name]
        if config["enabled"]:
            widgets["enabled"].add_state(lv.STATE.CHECKED)
        else:
            widgets["enabled"].clear_state(lv.STATE.CHECKED)
        widgets["start"].set_selected(dropdown_index_from_minutes(config["start"]))
        widgets["end"].set_selected(dropdown_index_from_minutes(config["end"]))


def show_shift_hours_popup():
    ensure_shift_hours_popup()
    refresh_shift_hours_popup()
    shift_hours_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    shift_hours_popup.move_foreground()


def apply_signal_mode():
    global machine_high, machine_run_start_epoch, machine_run_confirmed
    global pending_machine_run_start_epoch, pending_cycle_shift
    raw_value = run_pin.value()
    machine_high = is_signal_active(raw_value)
    machine_run_confirmed = machine_high
    machine_run_start_epoch = time.time() if machine_high else None
    pending_machine_run_start_epoch = None
    pending_cycle_shift = None


def clear_pending_cycle_start():
    global pending_machine_run_start_epoch, pending_cycle_shift
    pending_machine_run_start_epoch = None
    pending_cycle_shift = None


def start_pending_cycle(active_shift):
    global pending_machine_run_start_epoch, pending_cycle_shift
    if pending_machine_run_start_epoch is None:
        pending_machine_run_start_epoch = time.time()
        if active_shift is not None:
            pending_cycle_shift = active_shift
        else:
            pending_cycle_shift = OFF_SHIFT_CYCLE


def confirm_pending_cycle_start():
    global machine_high, machine_run_start_epoch, machine_run_confirmed
    global current_cycle_start_epoch, current_cycle_shift, current_machine_run_seconds
    if pending_machine_run_start_epoch is None:
        return False
    now_epoch = time.time()
    elapsed = max(0, int(now_epoch - pending_machine_run_start_epoch))
    if elapsed <= MIN_CYCLE_SECONDS:
        return False
    machine_high = True
    machine_run_start_epoch = pending_machine_run_start_epoch
    machine_run_confirmed = True
    current_machine_run_seconds = elapsed
    current_cycle_shift = pending_cycle_shift
    if current_cycle_start_epoch is None:
        current_cycle_start_epoch = pending_machine_run_start_epoch
    clear_pending_cycle_start()
    return True


def apply_shift_settings_from_popup():
    global current_cycle_start_epoch, current_cycle_shift, current_cycle_with_load_seconds, last_daily_reset_key
    for shift_name in SHIFT_NAMES:
        widgets = shift_hours_widgets[shift_name]
        shift_settings[shift_name] = {
            "enabled": widgets["enabled"].has_state(lv.STATE.CHECKED),
            "start": minutes_from_dropdown(widgets["start"]),
            "end": minutes_from_dropdown(widgets["end"]),
        }
        shift_reset_keys[shift_name] = get_shift_reset_key(shift_name)
    current_cycle_start_epoch = None
    current_cycle_shift = None
    current_cycle_with_load_seconds = 0
    last_daily_reset_key = get_reset_day_key()
    ensure_shift_period_reset()
    finalize_completed_shifts()
    settings_menu_status.set_text("Shift hours saved")
    mark_data_dirty()
    hide_shift_hours_popup()
    update_ui()
    save_config()
    save_state(force=True)


def show_invert_popup():
    ensure_invert_popup()
    if io_invert:
        invert_checkbox.add_state(lv.STATE.CHECKED)
    else:
        invert_checkbox.clear_state(lv.STATE.CHECKED)
    invert_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    invert_popup.move_foreground()


def apply_invert_setting():
    global io_invert, pending_machine_run_start_epoch, pending_cycle_shift
    io_invert = invert_checkbox.has_state(lv.STATE.CHECKED)
    apply_signal_mode()
    pending_machine_run_start_epoch = None
    pending_cycle_shift = None
    settings_menu_status.set_text("Cycle input invert {}".format("ON" if io_invert else "OFF"))
    mark_data_dirty()
    hide_invert_popup()
    update_ui()
    save_config()
    save_state(force=True)


def clear_wifi_list():
    global wifi_network_callbacks
    wifi_network_callbacks = []
    if wifi_list is None:
        return
    try:
        wifi_list.clean()
    except Exception:
        pass


def make_wifi_network_event(ssid_text):
    def _event(e):
        if e.get_code() != lv.EVENT.CLICKED:
            return
        open_wifi_password_popup(ssid_text)
    return _event


def refresh_wifi_scan_popup():
    ensure_wifi_scan_popup()
    global wifi_scan_results
    clear_wifi_list()
    wifi_scan_status.set_text("Scanning...")
    update_ui()
    wifi_scan_results = scan_wifi_networks()
    if not wifi_scan_results:
        wifi_scan_status.set_text("No networks found")
        return

    wifi_scan_status.set_text("Found {} networks".format(len(wifi_scan_results)))
    wifi_icon = ""
    try:
        wifi_icon = lv.SYMBOL.WIFI
    except Exception:
        wifi_icon = ""

    for ssid_text in wifi_scan_results:
        btn = wifi_list.add_btn(wifi_icon, ssid_text)
        stabilize_button(btn)
        callback = make_wifi_network_event(ssid_text)
        wifi_network_callbacks.append(callback)
        btn.add_event_cb(callback, lv.EVENT.ALL, None)


def show_wifi_scan_popup():
    ensure_wifi_scan_popup()
    refresh_wifi_scan_popup()
    wifi_scan_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    wifi_scan_popup.move_foreground()


def open_wifi_password_popup(ssid_text):
    ensure_wifi_password_popup()
    global selected_wifi_ssid
    selected_wifi_ssid = ssid_text
    wifi_password_ssid.set_text("SSID: {}".format(ssid_text))
    wifi_password_status.set_text("")
    if ssid_text == wifi_ssid and wifi_password:
        wifi_password_textarea.set_text(wifi_password)
    else:
        wifi_password_textarea.set_text("")
    hide_wifi_scan_popup()
    wifi_password_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    wifi_password_popup.move_foreground()


def connect_to_wifi_credentials(ssid_text, password_text):
    if network is None or not ssid_text:
        return None
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        if wlan.isconnected():
            wlan.disconnect()
            time.sleep(0.2)
    except Exception:
        pass
    try:
        wlan.connect(ssid_text, password_text)
        start_ms = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_ms) > WIFI_TIMEOUT_MS:
                return None
            time.sleep(0.2)
        return wlan
    except Exception as err:
        print("WiFi connect failed:", err)
        return None


def connect_selected_wifi():
    global wifi_ssid, wifi_password
    password_text = wifi_password_textarea.get_text()
    wifi_password_status.set_text("Connecting...")
    wlan = connect_to_wifi_credentials(selected_wifi_ssid, password_text)
    if wlan is None:
        wifi_password_status.set_text("Connection failed")
        settings_menu_status.set_text("WiFi connect failed")
        return

    wifi_ssid = selected_wifi_ssid
    wifi_password = password_text
    mark_data_dirty()
    sync_time_from_wifi()
    wifi_password_status.set_text("Connected")
    settings_menu_status.set_text("WiFi connected: {}".format(selected_wifi_ssid))
    update_ui()
    save_config()
    save_state(force=True)
    hide_wifi_password_popup()
    show_wifi_scan_popup()


def trigger_good_flash():
    global good_flash_until
    good_flash_until = time.ticks_add(time.ticks_ms(), BUTTON_FLASH_MS)
    set_button_visual(ui_Button1, ui_GOOD_PART, 0x04BE2D, 0x04BE2D, 0x111111, 8)


def trigger_bad_flash():
    global bad_flash_until
    bad_flash_until = time.ticks_add(time.ticks_ms(), BUTTON_FLASH_MS)
    set_button_visual(ui_Button2, ui_GOOD_PART1, 0xC32331, 0xC32331, 0xFFFFFF, 8)


def update_button_feedback():
    global good_flash_until, bad_flash_until
    now_ms = time.ticks_ms()

    if good_flash_until is not None and time.ticks_diff(now_ms, good_flash_until) >= 0:
        set_button_visual(ui_Button1, ui_GOOD_PART, 0x313030, 0x04BE2D, 0x04BE2D, 8)
        good_flash_until = None

    if bad_flash_until is not None and time.ticks_diff(now_ms, bad_flash_until) >= 0:
        set_button_visual(ui_Button2, ui_GOOD_PART1, 0x313030, 0xC32331, 0xC32331, 8)
        bad_flash_until = None


def update_stats_screen():
    set_cached_label_text(
        "total_daily_production",
        ui_Total_Daily_Production,
        get_total_daily_good_parts(),
    )

    for shift_name in SHIFT_NAMES:
        stats = completed_shift_stats[shift_name]
        widgets = stats_widgets[shift_name]
        set_cached_label_text("stats_{}_good".format(shift_name), widgets["good"], "Good: {}".format(stats["good"]))
        set_cached_label_text("stats_{}_bad".format(shift_name), widgets["bad"], "Bad: {}".format(stats["bad"]))
        set_cached_label_text("stats_{}_total".format(shift_name), widgets["total"], "Cycles: {}".format(stats["cycle_count"]))
        set_cached_label_text("stats_{}_avg_title".format(shift_name), widgets["avg_title"], "Avg W/Load:")
        set_cached_label_text(
            "stats_{}_avg_value".format(shift_name),
            widgets["avg_value"],
            format_mmss(get_completed_shift_average_with_load(shift_name)),
        )
        set_cached_label_text("stats_{}_pph".format(shift_name), widgets["pph"], "PPH: {}".format(get_completed_shift_pph(shift_name)))


def update_notes_screen():
    set_cached_label_text("notes_title", notes_title_label, notes_title_text if notes_title_text else " ")
    set_cached_label_text("notes_body", notes_body_label, notes_body_text if notes_body_text else " ")
    set_cached_label_text("notes_status", notes_status_label, notes_status_text)
    set_cached_label_text("notes_page", notes_page_label, notes_page_text)


def update_main_screen_ui(current_shift):
    set_cached_label_text("good_count", ui_Good_Count_bar, good_count)
    set_cached_label_text("bad_count", ui_Label8, bad_count)
    set_cached_label_text("bad_pct", ui_BAD_PARTS_PRC, "{:.1f}".format(safe_pct(bad_count, good_count)))
    set_cached_label_text("pph_goal", ui_PPH_GOAL_NUMBER, pph_goal)

    pph_a = get_graph_shift_pph("A")
    pph_b = get_graph_shift_pph("B")
    pph_c = get_graph_shift_pph("C")

    set_cached_label_text("pph_a", ui_PPH_GOAL_NUMBER_A, pph_a)
    set_cached_label_text("pph_b", ui_PPH_GOAL_NUMBER_B, pph_b)
    set_cached_label_text("pph_c", ui_PPH_GOAL_NUMBER_C, pph_c)

    pct_a = max(0, min(100, int(round(safe_pct(pph_a, pph_goal)))))
    pct_b = max(0, min(100, int(round(safe_pct(pph_b, pph_goal)))))
    pct_c = max(0, min(100, int(round(safe_pct(pph_c, pph_goal)))))

    set_cached_arc_value("pct_a", ui_SHIFT_A_GRAPH, pct_a)
    set_cached_arc_value("pct_b", ui_SHIFT_B_GRAPH, pct_b)
    set_cached_arc_value("pct_c", ui_SHIFT_C_GRAPH, pct_c)

    set_cached_label_text("cycle_with_load", ui_with_load_cycle_current, format_mmss(current_cycle_with_load_seconds))
    if current_shift is None:
        set_cached_label_text("avg_with_load", ui_AVRG_W_LOAD_TIME, "0m 0s")
    else:
        set_cached_label_text("avg_with_load", ui_AVRG_W_LOAD_TIME, format_mmss(get_pending_shift_average_with_load(current_shift)))
    set_cached_label_text("machine_cycle_time", ui_machine_cycle_time, format_mmss(current_machine_run_seconds))
    set_cached_label_text("avg_load_time", ui_AVRG_LOAD_TIME_NUMBER, "0m 0s")
    set_cached_label_text("avg_idle_time", ui_AVRG_IDLE_TIME_NUMBER, "0m 0s")
    set_door_switch_visibility()


def update_settings_menu_ui(now_tuple):
    set_cached_label_text(
        "settings_wifi_text",
        ui_WiFi_Settings_Text,
        "WiFi\n{}".format(wifi_ssid if wifi_ssid else "Not Set"),
    )
    set_cached_label_text(
        "settings_shift_text",
        ui_Shift_Hours_Text,
        "Shift Hours\n{}{}{}".format(
            "A" if shift_settings["A"]["enabled"] else "-",
            "B" if shift_settings["B"]["enabled"] else "-",
            "C" if shift_settings["C"]["enabled"] else "-",
        ),
    )
    set_cached_label_text(
        "settings_parts_cycle_text",
        ui_Parts_Per_Cycle_Text,
        "Parts/Cycle\n{}".format(parts_per_cycle),
    )
    set_cached_label_text(
        "settings_invert_text",
        ui_Invert_Cycle_Start_IO_Text,
        "Cycle Invert\n{}".format("ON" if io_invert else "OFF"),
    )
    set_cached_label_text(
        "settings_reset_text",
        ui_Reset_Rules_Text,
        "Reset Lead\n{} min".format(shift_reset_lead_minutes),
    )
    set_cached_label_text(
        "settings_io_check_text",
        ui_IO_Check_Text,
        "IO Check\n{}".format("LOW" if run_pin.value() == 0 else "HIGH"),
    )
    set_cached_label_text(
        "settings_door_switch_text",
        ui_Door_Switch_Enable_Lable,
        "Door Switch\n{}".format("ON" if door_switch_enabled else "OFF"),
    )
    set_cached_label_text(
        "settings_shift_lock_text",
        ui_Shift_Data_Reset_Lock_Text,
        "Shift Reset\n{}".format("LOCKED" if shift_reset_lock else "UNLOCKED"),
    )
    set_cached_label_text("settings_time", ui_Time, format_hhmmss(now_tuple[3], now_tuple[4], now_tuple[5]))
    set_cached_label_text("settings_time_sync", ui_Time_Sync, get_time_sync_display())
    refresh_io_check_label()


def update_ui():
    current_shift = get_shift()
    now_tuple = time.localtime()
    current_screen = lv.scr_act()

    if current_screen == ui_MAIN_SCREEN:
        update_main_screen_ui(current_shift)
    elif current_screen == ui_SETTINGS:
        if notes_mode_active:
            update_notes_screen()
        else:
            update_stats_screen()
    elif current_screen == ui_SETTINGS_MENU:
        update_settings_menu_ui(now_tuple)


def sync_live_timers():
    global current_machine_run_seconds, current_cycle_with_load_seconds
    global current_cycle_start_epoch, current_cycle_shift, machine_run_confirmed
    now = time.time()
    active_shift = get_shift()

    if machine_high and machine_run_start_epoch is not None:
        current_machine_run_seconds = max(0, int(now - machine_run_start_epoch))

    if active_shift != current_cycle_shift and not machine_high:
        current_cycle_start_epoch = None
        current_cycle_shift = None

    if (
        current_cycle_start_epoch is None
        or current_cycle_shift != active_shift
        or current_cycle_shift not in pending_shift_stats
    ):
        current_cycle_with_load_seconds = 0
    else:
        current_cycle_with_load_seconds = max(0, int(now - current_cycle_start_epoch))


def reset_graph_hold_state(shift_name):
    graph_reset_press_ms[shift_name] = None


def reset_graph_now(shift_name):
    if shift_reset_lock:
        stats_reset_status.set_text("Shift reset locked")
        return
    reset_graph_shift_data(shift_name)
    if get_shift() == shift_name:
        graph_cycle_anchor_epoch[shift_name] = time.time()
    set_cached_label_text("pph_{}".format(shift_name.lower()), {
        "A": ui_PPH_GOAL_NUMBER_A,
        "B": ui_PPH_GOAL_NUMBER_B,
        "C": ui_PPH_GOAL_NUMBER_C,
    }[shift_name], "0")
    stats_reset_status.set_text("Shift {} graph reset".format(shift_name))
    update_ui()
    save_state(force=True)


def graph_reset_hold_event(shift_name, e):
    code = e.get_code()
    if code == lv.EVENT.PRESSED:
        graph_reset_press_ms[shift_name] = time.ticks_ms()
    elif code == lv.EVENT.PRESSING:
        press_ms = graph_reset_press_ms[shift_name]
        if press_ms is not None and time.ticks_diff(time.ticks_ms(), press_ms) >= GRAPH_RESET_HOLD_MS:
            reset_graph_hold_state(shift_name)
            reset_graph_now(shift_name)
    elif code == lv.EVENT.RELEASED or code == lv.EVENT.PRESS_LOST:
        reset_graph_hold_state(shift_name)


def graph_a_reset_event(e):
    graph_reset_hold_event("A", e)


def graph_b_reset_event(e):
    graph_reset_hold_event("B", e)


def graph_c_reset_event(e):
    graph_reset_hold_event("C", e)


def count_label_reset_hold_event(target_name, e):
    global good_label_reset_press_ms, bad_label_reset_press_ms

    code = e.get_code()
    if target_name == "good":
        press_ms = good_label_reset_press_ms
    else:
        press_ms = bad_label_reset_press_ms

    if code == lv.EVENT.PRESSED:
        if target_name == "good":
            good_label_reset_press_ms = time.ticks_ms()
        else:
            bad_label_reset_press_ms = time.ticks_ms()
    elif code == lv.EVENT.PRESSING:
        if press_ms is not None and time.ticks_diff(time.ticks_ms(), press_ms) >= PARTS_RESET_HOLD_MS:
            if target_name == "good":
                reset_good_count()
                good_label_reset_press_ms = None
            else:
                reset_bad_count()
                bad_label_reset_press_ms = None
            update_ui()
            save_state(force=True)
    elif code == lv.EVENT.RELEASED or code == lv.EVENT.PRESS_LOST:
        if target_name == "good":
            good_label_reset_press_ms = None
        else:
            bad_label_reset_press_ms = None


def good_label_reset_event(e):
    count_label_reset_hold_event("good", e)


def bad_label_reset_event(e):
    count_label_reset_hold_event("bad", e)


def change_screen_gesture_event(e):
    global last_gesture_ms
    if e.get_code() != lv.EVENT.GESTURE:
        return

    now_ms = time.ticks_ms()
    if time.ticks_diff(now_ms, last_gesture_ms) < GESTURE_COOLDOWN_MS:
        return

    indev = lv.indev_get_act()
    if indev is None:
        return

    direction = indev.get_gesture_dir()
    current_screen = lv.scr_act()

    if direction == lv.DIR.RIGHT and current_screen == ui_MAIN_SCREEN:
        hide_goal_popup()
        hide_count_popup()
        show_shift_stats_screen()
        last_gesture_ms = now_ms
    elif direction == lv.DIR.LEFT and current_screen == ui_SETTINGS and notes_mode_active:
        advance_notes_page()
        last_gesture_ms = now_ms
    elif direction == lv.DIR.RIGHT and current_screen == ui_SETTINGS and notes_mode_active:
        retreat_notes_page()
        last_gesture_ms = now_ms
    elif direction == lv.DIR.RIGHT and current_screen == ui_SETTINGS and not notes_mode_active:
        load_main_screen_with_guard()
        last_gesture_ms = now_ms
    elif direction == lv.DIR.RIGHT and current_screen == ui_SETTINGS_MENU:
        hide_all_settings_popups()
        load_main_screen_with_guard()
        last_gesture_ms = now_ms


def notes_button_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    open_notes_screen(reset_index=True)


def notes_main_button_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    load_main_screen_with_guard()


def daily_production_hold_event(e):
    global daily_production_press_ms

    code = e.get_code()
    if code == lv.EVENT.PRESSED:
        daily_production_press_ms = time.ticks_ms()
        stats_reset_status.set_text("Hold {}s to reset daily".format((DAILY_PRODUCTION_RESET_HOLD_MS + 999) // 1000))
        update_ui()
    elif code == lv.EVENT.PRESSING:
        if (
            daily_production_press_ms is not None
            and time.ticks_diff(time.ticks_ms(), daily_production_press_ms) >= DAILY_PRODUCTION_RESET_HOLD_MS
        ):
            daily_production_press_ms = None
            reset_daily_production(manual=True)
            stats_reset_status.set_text("Daily production reset")
            update_ui()
    elif code == lv.EVENT.RELEASED or code == lv.EVENT.PRESS_LOST:
        if daily_production_press_ms is not None:
            stats_reset_status.set_text("")
        daily_production_press_ms = None
        update_ui()


def door_switch_toggle_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    global door_switch_enabled
    door_switch_enabled = not door_switch_enabled
    mark_data_dirty()
    set_door_switch_visibility()
    settings_menu_status.set_text("Door switch {}".format("enabled" if door_switch_enabled else "disabled"))
    update_ui()
    save_config()
    save_state(force=True)


def shift_reset_lock_toggle_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    global shift_reset_lock
    was_locked = shift_reset_lock
    shift_reset_lock = not shift_reset_lock
    if was_locked and not shift_reset_lock:
        for shift_name in SHIFT_NAMES:
            shift_reset_keys[shift_name] = get_shift_reset_key(shift_name)
    mark_data_dirty()
    settings_menu_status.set_text("Shift reset {}".format("locked" if shift_reset_lock else "unlocked"))
    update_ui()
    save_config()
    save_state(force=True)


def set_good_count_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_count_popup("good", good_count)


def set_bad_count_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_count_popup("bad", bad_count)


def count_kb_event(e):
    if e.get_code() != lv.EVENT.VALUE_CHANGED:
        return

    selected_btn = count_kb.get_selected_btn()
    if selected_btn < 0:
        return

    txt = count_kb.get_btn_text(selected_btn)
    if txt is None:
        return

    current = count_textarea.get_text()

    if txt == "CLR":
        count_textarea.set_text("")
    elif txt == "BKSP":
        count_textarea.del_char()
    elif txt == "OK":
        if count_edit_target is not None:
            target_name = count_edit_target
            if current:
                try:
                    new_value = int(current)
                except ValueError:
                    new_value = 0
            else:
                new_value = 0
            hide_count_popup()
            apply_manual_count(target_name, new_value)
            stats_reset_status.set_text("Count updated")
            update_ui()
            save_state(force=True)
    elif txt == "CANCEL":
        hide_count_popup()
    elif txt and txt[0].isdigit():
        if len(current) < 6:
            count_textarea.add_text(txt)


def settings_number_kb_event(e):
    global parts_per_cycle, shift_reset_lead_minutes
    if e.get_code() != lv.EVENT.VALUE_CHANGED:
        return

    selected_btn = settings_number_kb.get_selected_btn()
    if selected_btn < 0:
        return

    txt = settings_number_kb.get_btn_text(selected_btn)
    if txt is None:
        return

    current = settings_number_textarea.get_text()
    if txt == "CLR":
        settings_number_textarea.set_text("")
    elif txt == "BKSP":
        settings_number_textarea.del_char()
    elif txt == "OK":
        try:
            new_value = int(current) if current else 0
        except ValueError:
            new_value = 0

        if settings_number_target == "parts_per_cycle":
            parts_per_cycle = max(1, new_value)
            settings_menu_status.set_text("Parts per cycle set to {}".format(parts_per_cycle))
        elif settings_number_target == "reset_lead_minutes":
            shift_reset_lead_minutes = max(0, new_value)
            settings_menu_status.set_text("Reset lead set to {} min".format(shift_reset_lead_minutes))
            for shift_name in SHIFT_NAMES:
                shift_reset_keys[shift_name] = get_shift_reset_key(shift_name)
            ensure_shift_period_reset()
            finalize_completed_shifts()
        mark_data_dirty()
        hide_settings_number_popup()
        update_ui()
        save_config()
        save_state(force=True)
    elif txt == "CANCEL":
        hide_settings_number_popup()
    elif txt and txt[0].isdigit():
        if len(current) < 6:
            settings_number_textarea.add_text(txt)


# =========================================================
# EVENT HANDLERS
# =========================================================
def settings_button_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_goal_popup()
    hide_count_popup()
    hide_all_settings_popups()
    lv.scr_load(ui_SETTINGS_MENU)
    update_ui()


def wifi_settings_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_wifi_scan_popup()


def wifi_scan_refresh_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    refresh_wifi_scan_popup()


def wifi_scan_close_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_wifi_scan_popup()


def wifi_password_connect_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    connect_selected_wifi()


def wifi_password_cancel_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_wifi_password_popup()
    show_wifi_scan_popup()


def shift_hours_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_shift_hours_popup()


def shift_hours_save_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    apply_shift_settings_from_popup()


def shift_hours_cancel_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_shift_hours_popup()


def parts_per_cycle_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_settings_number_popup("parts_per_cycle", "SET PARTS / CYCLE", parts_per_cycle, 3)


def invert_cycle_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_invert_popup()


def invert_save_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    apply_invert_setting()


def invert_cancel_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_invert_popup()


def reset_rules_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_settings_number_popup("reset_lead_minutes", "RESET LEAD (MIN)", shift_reset_lead_minutes, 4)


def io_check_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    ensure_io_check_popup()
    refresh_io_check_label()
    io_check_popup.clear_flag(lv.obj.FLAG.HIDDEN)
    io_check_popup.move_foreground()


def io_check_close_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_io_check_popup()


def software_update_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_software_update_popup()


def software_update_refresh_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    refresh_software_update_popup()


def software_update_stats_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_stats_config_popup()


def software_update_ok_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    if not isinstance(software_update_selected_entry, dict):
        software_update_status.set_text("Select a version first")
        return
    software_update_install_event(software_update_selected_entry)


def software_update_install_event(entry):
    if not isinstance(entry, dict):
        return
    if entry.get("version") == APP_VERSION:
        software_update_status.set_text("{} is already installed".format(APP_VERSION))
        return

    software_update_status.set_text("Installing {}...".format(entry.get("version", "")))
    try:
        perform_software_update(entry)
        software_update_status.set_text("Update staged. Rebooting...")
        settings_menu_status.set_text("{} update staged".format(entry.get("version", "Software")))
        time.sleep(1)
        request_device_reset()
    except Exception as err:
        software_update_status.set_text("Update failed: {}".format(err))
        settings_menu_status.set_text("Software update failed")


def software_update_close_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_software_update_popup()


def apply_stats_config_from_popup():
    global stats_machine_id, stats_token_import_url, github_stats_token
    new_machine_id = str(stats_config_machine_value).strip()
    new_import_url = normalize_import_url(stats_config_import_url_textarea.get_text())
    new_token = str(stats_config_token_textarea.get_text()).strip()
    if not new_machine_id:
        raise ValueError("Machine ID required")
    stats_machine_id = new_machine_id
    stats_token_import_url = new_import_url
    github_stats_token = new_token
    ensure_machine_option_available(stats_machine_id)
    mark_data_dirty()
    settings_menu_status.set_text("Machine saved: {}".format(stats_machine_id))
    stats_config_status.set_text(
        "Saved: {}  Status: {}  Notes: {}/".format(
            format_machine_choice(stats_machine_id),
            get_stats_status_path(),
            get_notes_machine_path(),
        )
    )
    update_ui()
    save_config()
    save_state(force=True)


def stats_config_save_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    try:
        apply_stats_config_from_popup()
    except Exception as err:
        stats_config_status.set_text(str(err))


def stats_config_import_event(e):
    global stats_machine_id, stats_token_import_url, github_stats_token
    if e.get_code() != lv.EVENT.CLICKED:
        return
    try:
        new_machine_id = str(stats_config_machine_value).strip()
        if not new_machine_id:
            raise ValueError("Machine ID required")
        stats_config_status.set_text("Importing token...")
        import_url, imported_token = import_stats_token_from_url(stats_config_import_url_textarea.get_text())
        stats_machine_id = new_machine_id
        stats_token_import_url = import_url
        github_stats_token = imported_token
        ensure_machine_option_available(stats_machine_id)
        stats_config_import_url_textarea.set_text(stats_token_import_url)
        stats_config_token_textarea.set_text(github_stats_token)
        mark_data_dirty()
        settings_menu_status.set_text("Stats token imported")
        stats_config_status.set_text(
            "Token imported. Machine: {}  Notes: {}/".format(
                format_machine_choice(stats_machine_id),
                get_notes_machine_path(),
            )
        )
        update_ui()
        save_config()
        save_state(force=True)
    except Exception as err:
        stats_config_status.set_text(format_status_message("Import failed: {}".format(err), 78))
        settings_menu_status.set_text(format_status_message("Token import failed: {}".format(err)))
        print("Token import failed:", err)


def stats_config_upload_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    try:
        apply_stats_config_from_popup()
        stats_config_status.set_text("Uploading...")
        upload_stats_to_github(manual=True)
        stats_config_status.set_text("Upload complete")
    except Exception as err:
        stats_config_status.set_text(format_status_message("Upload failed: {}".format(err), 78))
        settings_menu_status.set_text(format_status_message("Stats upload failed: {}".format(err)))
        print("Stats upload failed:", err)


def stats_config_close_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    hide_stats_config_popup()
    show_software_update_popup()


def good_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    if main_screen_button_guard_active():
        return
    trigger_good_flash()
    add_good_part()
    clamp_counts()
    update_ui()
    save_state(force=True)


def bad_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    if main_screen_button_guard_active():
        return
    trigger_bad_flash()
    add_bad_part()
    clamp_counts()
    update_ui()
    save_state(force=True)


def goal_button_event(e):
    if e.get_code() != lv.EVENT.CLICKED:
        return
    show_goal_popup()


def goal_kb_event(e):
    global pph_goal
    if e.get_code() != lv.EVENT.VALUE_CHANGED:
        return

    selected_btn = goal_kb.get_selected_btn()
    if selected_btn < 0:
        return

    txt = goal_kb.get_btn_text(selected_btn)
    if txt is None:
        return

    current = goal_textarea.get_text()

    if txt == "CLR":
        goal_textarea.set_text("")
    elif txt == "BKSP":
        goal_textarea.del_char()
    elif txt == "OK":
        if current:
            try:
                new_goal = int(current)
            except ValueError:
                new_goal = 1
            if new_goal <= 0:
                new_goal = 1
            pph_goal = new_goal
            mark_data_dirty()
            save_config()
            save_state(force=True)
            update_ui()
        hide_goal_popup()
    elif txt == "CANCEL":
        hide_goal_popup()
    elif txt and txt[0].isdigit():
        if len(current) < 4:
            goal_textarea.add_text(txt)


def hour_plus_event(e):
    global set_hour
    if e.get_code() != lv.EVENT.CLICKED:
        return
    set_hour = (set_hour + 1) % 24
    refresh_boot_time_labels()


def hour_minus_event(e):
    global set_hour
    if e.get_code() != lv.EVENT.CLICKED:
        return
    set_hour = (set_hour - 1) % 24
    refresh_boot_time_labels()


def min_plus_event(e):
    global set_minute
    if e.get_code() != lv.EVENT.CLICKED:
        return
    set_minute = (set_minute + 1) % 60
    refresh_boot_time_labels()


def min_minus_event(e):
    global set_minute
    if e.get_code() != lv.EVENT.CLICKED:
        return
    set_minute = (set_minute - 1) % 60
    refresh_boot_time_labels()


def time_ok_event(e):
    global time_is_set, current_cycle_start_epoch, current_cycle_shift
    global last_cycle_complete_epoch, time_source_label, machine_run_confirmed
    global pending_machine_run_start_epoch, pending_cycle_shift
    if e.get_code() != lv.EVENT.CLICKED:
        return

    rtc = RTC()
    rtc.datetime((DEFAULT_YEAR, DEFAULT_MONTH, DEFAULT_DAY, 0, set_hour, set_minute, 0, 0))
    now = time.time()
    current_cycle_start_epoch = None
    current_cycle_shift = None
    machine_run_confirmed = False
    pending_machine_run_start_epoch = None
    pending_cycle_shift = None
    last_cycle_complete_epoch = now
    time_is_set = True
    time_source_label = "Default"
    mark_data_dirty()
    save_state(force=True)
    sync_live_timers()
    update_ui()
    load_main_screen_with_guard()


ui_Button1.add_event_cb(good_event, lv.EVENT.ALL, None)
ui_Button2.add_event_cb(bad_event, lv.EVENT.ALL, None)
ui_SHIFT_A_RESET_TOUCH.add_event_cb(graph_a_reset_event, lv.EVENT.ALL, None)
ui_SHIFT_B_RESET_TOUCH.add_event_cb(graph_b_reset_event, lv.EVENT.ALL, None)
ui_SHIFT_C_RESET_TOUCH.add_event_cb(graph_c_reset_event, lv.EVENT.ALL, None)
ui_SETTING_BUTTON.add_event_cb(settings_button_event, lv.EVENT.ALL, None)
ui_PPH_GOAL_SETTING.add_event_cb(goal_button_event, lv.EVENT.ALL, None)
goal_kb.add_event_cb(goal_kb_event, lv.EVENT.ALL, None)
count_kb.add_event_cb(count_kb_event, lv.EVENT.ALL, None)
stats_daily_reset_touch.add_event_cb(daily_production_hold_event, lv.EVENT.ALL, None)
ui_Good_Label_Reset_Touch.add_event_cb(good_label_reset_event, lv.EVENT.ALL, None)
ui_Bad_Label_Reset_Touch.add_event_cb(bad_label_reset_event, lv.EVENT.ALL, None)
ui_Good_Count_Edit.add_event_cb(set_good_count_event, lv.EVENT.ALL, None)
ui_Bad_Count_Edit.add_event_cb(set_bad_count_event, lv.EVENT.ALL, None)
ui_NOTE_BUTTON.add_event_cb(notes_button_event, lv.EVENT.ALL, None)
ui_WiFi_Settings.add_event_cb(wifi_settings_event, lv.EVENT.ALL, None)
ui_Shift_Hours_Settings.add_event_cb(shift_hours_event, lv.EVENT.ALL, None)
ui_Parts_Per_Cycle.add_event_cb(parts_per_cycle_event, lv.EVENT.ALL, None)
ui_Invert_Cycle_Start_IO.add_event_cb(invert_cycle_event, lv.EVENT.ALL, None)
ui_Reset_Rules.add_event_cb(reset_rules_event, lv.EVENT.ALL, None)
ui_IO_Check.add_event_cb(io_check_event, lv.EVENT.ALL, None)
ui_Door_Switch_Enable_Button.add_event_cb(door_switch_toggle_event, lv.EVENT.ALL, None)
ui_Software_Update.add_event_cb(software_update_event, lv.EVENT.ALL, None)
ui_Reset_Shift_Data_Lock_Button.add_event_cb(shift_reset_lock_toggle_event, lv.EVENT.ALL, None)
notes_main_button.add_event_cb(notes_main_button_event, lv.EVENT.ALL, None)

ui_MAIN_SCREEN.add_event_cb(change_screen_gesture_event, lv.EVENT.GESTURE, None)
ui_SETTINGS.add_event_cb(change_screen_gesture_event, lv.EVENT.GESTURE, None)
ui_SETTINGS_MENU.add_event_cb(change_screen_gesture_event, lv.EVENT.GESTURE, None)

btn_hour_plus.add_event_cb(hour_plus_event, lv.EVENT.ALL, None)
btn_hour_minus.add_event_cb(hour_minus_event, lv.EVENT.ALL, None)
btn_min_plus.add_event_cb(min_plus_event, lv.EVENT.ALL, None)
btn_min_minus.add_event_cb(min_minus_event, lv.EVENT.ALL, None)
btn_time_ok.add_event_cb(time_ok_event, lv.EVENT.ALL, None)

lv.scr_load(startup_scr)
load_state()
load_config()
ensure_config_file()
apply_signal_mode()
set_door_switch_visibility()
initialize_shift_reset_keys()
if time_is_set:
    ensure_daily_reset()
    ensure_daily_production_reset()
    ensure_shift_period_reset()
    finalize_completed_shifts()
refresh_boot_time_labels()
animate_boot_flag(force=True)
sync_live_timers()
update_ui()
if time_is_set:
    startup_target_screen = ui_MAIN_SCREEN
else:
    startup_target_screen = boot_scr


# =========================================================
# MAIN LOOP
# =========================================================
while True:
    try:
        if startup_splash_active:
            animate_boot_flag()
            if startup_target_screen is not None and time.ticks_diff(time.ticks_ms(), startup_splash_start_ms) >= STARTUP_SPLASH_MS:
                lv.scr_load(startup_target_screen)
                startup_splash_active = False
        elif time_is_set:
            maybe_run_boot_wifi_sync()
            ensure_daily_reset()
            ensure_daily_production_reset()
            ensure_shift_period_reset()
            finalize_completed_shifts()
            raw = run_pin.value()
            now_ms = time.ticks_ms()

            if raw != last_raw:
                last_change_ms = now_ms
                last_raw = raw
            elif time.ticks_diff(now_ms, last_change_ms) >= DEBOUNCE_MS:
                active_shift = get_shift()
                signal_active = is_signal_active(raw)
                if signal_active:
                    if not machine_high:
                        start_pending_cycle(active_shift)
                        confirm_pending_cycle_start()
                else:
                    clear_pending_cycle_start()
                if (not signal_active) and machine_high:
                    machine_high = False
                    now_epoch = time.time()
                    completed_cycle_shift = current_cycle_shift

                    if machine_run_start_epoch is not None and machine_run_confirmed:
                        current_machine_run_seconds = max(0, int(now_epoch - machine_run_start_epoch))

                        if current_cycle_start_epoch is not None and completed_cycle_shift in pending_shift_stats:
                            cycle_with_load_seconds = max(0, now_epoch - current_cycle_start_epoch)
                            current_cycle_with_load_seconds = int(cycle_with_load_seconds)
                            cycle_number = int(graph_shift_stats[completed_cycle_shift]["cycle_count"]) + 1
                            include_pph = should_include_cycle_in_pph(completed_cycle_shift, cycle_number, now_epoch)

                            graph_cycle_start_epoch = current_cycle_start_epoch
                            graph_anchor_epoch = graph_cycle_anchor_epoch[completed_cycle_shift]
                            if graph_anchor_epoch is not None and graph_anchor_epoch > graph_cycle_start_epoch:
                                graph_cycle_start_epoch = graph_anchor_epoch
                            graph_cycle_with_load_seconds = max(0, now_epoch - graph_cycle_start_epoch)

                            graph_cycle_anchor_epoch[completed_cycle_shift] = now_epoch
                            pending_shift_stats[completed_cycle_shift]["with_load_sum"] += cycle_with_load_seconds
                            pending_shift_stats[completed_cycle_shift]["with_load_count"] += 1
                            if include_pph:
                                graph_shift_stats[completed_cycle_shift]["pph_with_load_sum"] += graph_cycle_with_load_seconds
                                graph_shift_stats[completed_cycle_shift]["pph_with_load_count"] += 1
                                pending_shift_stats[completed_cycle_shift]["pph_with_load_sum"] += cycle_with_load_seconds
                                pending_shift_stats[completed_cycle_shift]["pph_with_load_count"] += 1
                            mark_data_dirty()

                            auto_complete_cycle(completed_cycle_shift, include_pph=include_pph)
                        elif current_cycle_start_epoch is not None:
                            auto_complete_cycle(None)
                            current_cycle_with_load_seconds = 0
                        else:
                            current_cycle_with_load_seconds = 0

                        last_cycle_complete_epoch = now_epoch
                        if active_shift is not None and completed_cycle_shift == active_shift:
                            current_cycle_start_epoch = now_epoch
                            current_cycle_shift = active_shift
                        else:
                            current_cycle_start_epoch = None
                            current_cycle_shift = None
                    else:
                        if current_cycle_start_epoch is None:
                            current_cycle_shift = None

                    machine_run_start_epoch = None
                    machine_run_confirmed = False

                    clamp_counts()
                    update_ui()
                    save_state(force=True)

            sync_live_timers()
            update_button_feedback()
            maybe_update_ui()
            maybe_upload_stats()
            save_state()
        else:
            maybe_run_boot_wifi_sync()

        time.sleep(0.05)

    except KeyboardInterrupt:
        break
