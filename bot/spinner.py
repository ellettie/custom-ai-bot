import sys, itertools, time, threading

SPINNER_FRAMES = "⠋⠙⠸⠴⠦⠧⠇⠏"
MSG            = " Starting… "
INTERVAL       = 0.08

CSI = "\x1b["                                # Control Sequence Introducer
ERASE_LINE = CSI + "2K"

class Spinner:
    def __init__(self):
        self._stop    = threading.Event()
        self._frames  = itertools.cycle(SPINNER_FRAMES)
        self._lock    = threading.Lock()     # 同時書き込み防止

    # ---- low-level helpers ----
    def _goto_start(self):
        sys.stdout.write("\r")               # カーソルを行頭へ
    def _erase(self):
        sys.stdout.write(ERASE_LINE)         # 行をまるごと消す

    # ---- public ----
    def draw(self):
        with self._lock:
            self._goto_start()
            self._erase()
            sys.stdout.write(next(self._frames) + MSG)
            sys.stdout.flush()

    def erase(self):
        with self._lock:
            self._goto_start()
            self._erase()
            sys.stdout.flush()

    def start(self):
        print()                              # 1 行確保
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        return t

    def stop(self):
        self._stop.set()
        self.erase()                         # 消し残り防止

    def _run(self):
        while not self._stop.is_set():
            self.draw()
            time.sleep(INTERVAL)