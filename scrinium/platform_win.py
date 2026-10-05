"""Windows integration: single instance, tray icon, autostart, notifications.

Everything here is raw ``ctypes`` on purpose. v1's 32 MB builds were the
result of pulling in ``pystray`` + ``Pillow`` just to show an icon; the tray
below costs a few KB and keeps the one-file exe around 13 MB.

Every function degrades gracefully: on a non-Windows platform, or when a call
fails, they return a harmless default instead of raising.
"""

from __future__ import annotations

import os
import sys
import threading

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    # Gives the taskbar its own icon/branding instead of the generic python.exe.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Scrinium.DownloadSorter.2"
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# single instance
# ---------------------------------------------------------------------------
class SingleInstance:
    """Named mutex. `acquire()` is False when another Scrinium is running."""

    def __init__(self, name: str = "Global\\Scrinium.SingleInstance"):
        self.name = name
        self._handle = None
        self.ok = False

    def acquire(self) -> bool:
        if not IS_WINDOWS:
            self.ok = True
            return True
        try:
            k32 = ctypes.windll.kernel32
            k32.CreateMutexW(None, False, self.name)
            self._handle = k32.GetLastError() == 183      # ERROR_ALREADY_EXISTS
            self.ok = not self._handle
        except Exception:
            self.ok = True
        return self.ok

    def release(self) -> None:
        self._handle = None


# ---------------------------------------------------------------------------
# autostart (HKCU Run key - no admin rights needed)
# ---------------------------------------------------------------------------
def autostart_command(exe: str | None = None) -> str:
    """The command Windows should run to start Scrinium.

    `exe` overrides which binary gets registered. That matters because
    `sys.executable` is the *installer* when installer.py runs - without
    an override the autostart entry would point at Scrinium-Setup.exe and
    Windows would run the installer on every logon.
    """
    if exe:
        return f'"{os.path.abspath(exe)}"'
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.abspath(sys.argv[0])
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exe}" "{script}"'


def is_autostart_enabled() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        import winreg

        key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            value, _ = winreg.QueryValueEx(k, "Scrinium")
            return bool(value)
    except OSError:
        return False


def set_autostart(enabled: bool, exe: str | None = None) -> bool:
    """Enable or disable autostart. `exe` = which binary to register."""
    if not IS_WINDOWS:
        return False
    try:
        import winreg

        key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, "Scrinium", 0, winreg.REG_SZ,
                                  autostart_command(exe))
            else:
                try:
                    winreg.DeleteValue(k, "Scrinium")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# tray icon
# ---------------------------------------------------------------------------
# ctypes.wintypes has no WNDCLASS, and the WNDCLASS layout differs between
# 32- and 64-bit builds (cbClsExtra/cbWndExtra are int vs c_int), so declare it
# with the pointer-sized types explicitly.
class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(
            ctypes.c_long, wintypes.HWND, ctypes.c_uint,
            ctypes.c_ulong, ctypes.c_long)),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


LRESULT = ctypes.WINFUNCTYPE(
    ctypes.c_long, wintypes.HWND, ctypes.c_uint, ctypes.c_ulong, ctypes.c_long)


def _setup_prototypes() -> None:
    """Declare the real signatures once.

    Without this, ctypes defaults every restype to c_long, which truncates a
    64-bit HWND/HINSTANCE to 32 bits. Window and icon creation then silently
    return 0 and the tray never appears.
    """
    if not IS_WINDOWS:
        return
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    try:
        k.GetModuleHandleW.restype = wintypes.HMODULE
        k.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        u.CreateWindowExW.restype = wintypes.HWND
        u.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
        ]
        u.RegisterClassW.restype = ctypes.c_ushort
        u.RegisterClassW.argtypes = [ctypes.c_void_p]
        u.LoadImageW.restype = wintypes.HANDLE
        u.LoadImageW.argtypes = [
            wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
            ctypes.c_int, ctypes.c_int, wintypes.UINT,
        ]
        u.LoadIconW.restype = wintypes.HICON
        u.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        u.DestroyWindow.argtypes = [wintypes.HWND]
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.PeekMessageW.argtypes = [
            ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT,
        ]
        u.TrackPopupMenu.restype = wintypes.UINT
        u.TrackPopupMenu.argtypes = [
            wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, wintypes.HWND, wintypes.LPVOID,
        ]
        ctypes.windll.shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        ctypes.windll.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
    except Exception:
        pass


_setup_prototypes()


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
    ]


class TrayIcon:
    """Minimal Win32 shell tray icon with a right-click menu.

    Messages are pumped by ``run()`` on the Tk main thread (Tk already owns the
    message loop), so this does not need its own thread.
    """

    WM_APP = 0x8000
    WM_TRAY = WM_APP + 1
    WM_COMMAND = 0x0111
    WM_DESTROY = 0x0002
    WM_RBUTTONUP = 0x0205
    WM_LBUTTONDBLCLK = 0x0203
    WS_POPUP = 0x80000000
    HWND_MESSAGE = -3
    NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
    NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
    MF_STRING = 0x0000
    MF_CHECKED = 0x0008
    TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x0002, 0x0100
    IMAGE_ICON = 1
    LR_LOADFROMFILE, LR_DEFAULTSIZE = 0x0010, 0x0040

    ID_OPEN, ID_SORT, ID_AUTOSTART, ID_QUIT = 1001, 1002, 1003, 1004

    def __init__(self, title: str, tip: str, icon_path: str | None = None):
        self.title = title
        self._tip = tip
        self.icon_path = icon_path
        self.visible = False
        self._hwnd = None
        self._notified = None
        self._wndc = None                 # keep the WNDCLASS + proc alive
        self.on_open = lambda: None
        self.on_sort = lambda: None
        self.on_quit = lambda: None
        self.on_toggle_autostart = lambda enabled: None

    # ---- internals --------------------------------------------------------
    def _register_class(self) -> bool:
        wc = WNDCLASS()
        self._wndc = LRESULT(self._wndproc)      # hold a ref or it gets GC'd
        wc.lpfnWndProc = self._wndc
        wc.hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "ScriniumTray"
        if not ctypes.windll.user32.RegisterClassW(ctypes.byref(wc)):
            return False
        return True

    def _load_icon(self):
        if self.icon_path and os.path.exists(self.icon_path):
            hicon = ctypes.windll.user32.LoadImageW(
                None, self.icon_path, self.IMAGE_ICON, 0, 0,
                self.LR_LOADFROMFILE | self.LR_DEFAULTSIZE)
            if hicon:
                return hicon
        # fall back to the default app icon
        return ctypes.windll.user32.LoadIconW(None, 32512)     # IDI_APPLICATION

    def _shell_notify(self, op, data):
        ctypes.windll.shell32.Shell_NotifyIconW(op, ctypes.byref(data))

    # ---- public API -------------------------------------------------------
    def build(self) -> bool:
        """Create the hidden message window and add the icon.

        Returns False (never raises) when there is no interactive desktop -
        e.g. a headless session or a service. The caller should simply continue
        without a tray icon.
        """
        if not IS_WINDOWS:
            return False
        try:
            if not self._register_class():
                return False
            hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
            self._hwnd = ctypes.windll.user32.CreateWindowExW(
                0, "ScriniumTray", self.title, self.WS_POPUP,
                0, 0, 0, 0, None, None, hinst, None)
            if not self._hwnd:
                return False

            data = NOTIFYICONDATAW()
            data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            data.hWnd = self._hwnd
            data.uID = 1
            data.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
            data.uCallbackMessage = self.WM_TRAY
            data.hIcon = self._load_icon()
            data.szTip = self._tip
            self._notified = data
            if not self._shell_notify(self.NIM_ADD, data):
                return False
            self.visible = True
            return True
        except Exception:
            self.visible = False
            return False

    def set_tip(self, text: str) -> None:
        self._tip = text
        if self.visible and self._notified is not None:
            self._notified.szTip = text
            self._shell_notify(self.NIM_MODIFY, self._notified)

    def hide(self) -> None:
        if self.visible and self._notified is not None:
            self._shell_notify(self.NIM_DELETE, self._notified)
            self.visible = False

    def _show_menu(self):
        h = ctypes.windll.user32
        menu = h.CreatePopupMenu()
        h.AppendMenuW(menu, self.MF_STRING, self.ID_OPEN, "Scrinium öffnen")
        h.AppendMenuW(menu, self.MF_STRING, self.ID_SORT, "Jetzt sortieren")
        checked = 0x0008 if is_autostart_enabled() else 0      # MF_CHECKED
        h.AppendMenuW(menu, self.MF_STRING | checked, self.ID_AUTOSTART,
                      "Mit Windows starten")
        h.AppendMenuW(menu, self.MF_STRING, self.ID_QUIT, "Beenden")
        h.SetForegroundWindow(self._hwnd)
        cmd = h.TrackPopupMenu(
            menu, self.TPM_RIGHTBUTTON | self.TPM_RETURNCMD, -1, -1, 0, None, None)
        h.PostMessageW(self._hwnd, 0, 0, 0)
        h.DestroyMenu(menu)
        if cmd == self.ID_OPEN:
            self.on_open()
        elif cmd == self.ID_SORT:
            self.on_sort()
        elif cmd == self.ID_AUTOSTART:
            self.on_toggle_autostart(not is_autostart_enabled())
        elif cmd == self.ID_QUIT:
            self.on_quit()

    def _wndproc(self, hwnd, msg, wparam, lparam):
        u = ctypes.windll.user32
        if msg == self.WM_TRAY:
            if lparam in (self.WM_RBUTTONUP, 0x0207):        # 0x207 = WM_CONTEXTMENU
                self._show_menu()
            elif lparam == self.WM_LBUTTONDBLCLK:
                self.on_open()
            return 0
        if msg == self.WM_COMMAND:
            return 0
        return u.DefWindowProcW(hwnd, msg, wparam, lparam)

    def pump(self) -> None:
        """Drain tray messages. Call from the Tk tick - cheap when idle."""
        if not IS_WINDOWS or not self._hwnd:
            return
        msg = wintypes.MSG()
        while ctypes.windll.user32.PeekMessageW(
                ctypes.byref(msg), None, 0, 0, 1):          # PM_REMOVE
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))


# ---------------------------------------------------------------------------
# notifications
# ---------------------------------------------------------------------------
def notify(title: str, message: str, sound: bool = False) -> bool:
    """Balloon tip via Shell_NotifyIcon. Returns False when unavailable."""
    if not IS_WINDOWS:
        return False
    try:
        class NID(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
                ("uTimeoutOrVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
            ]

        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        hwnd = ctypes.windll.user32.CreateWindowExW(
            0, "STATIC", "", 0, 0, 0, 0, 0, 0, hinst, None)
        n = NID()
        n.cbSize = ctypes.sizeof(NID)
        n.hWnd = hwnd
        n.uID = 0
        n.uFlags = 0x00000001                                # NIF_INFO
        n.szInfo = message
        n.szInfoTitle = title
        n.dwInfoFlags = 0x00000001 | (0x00000010 if sound else 0)   # INFO | SOUND
        ok = ctypes.windll.shell32.Shell_NotifyIconW(0, ctypes.byref(n))
        ctypes.windll.user32.DestroyWindow(hwnd)
        return bool(ok)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# misc
# ---------------------------------------------------------------------------
def open_in_explorer(path: str) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        os.startfile(path)                     # noqa: S606 - Windows shell open
        return True
    except (OSError, AttributeError):
        return False


def icon_path() -> str | None:
    """Locate the bundled .ico (frozen one-file build or source tree)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))
    for cand in (os.path.join(base, "assets", "scrinium.ico"),
                 os.path.join(base, "assets", "scrinium.png"),
                 os.path.join(base, "scrinium.ico")):
        if os.path.exists(cand):
            return cand
    return None