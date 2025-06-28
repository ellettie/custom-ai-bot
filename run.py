import argparse
import logging
import bot
from typing import Literal, Optional

_FormatStyle = Literal["%", "{", "$"]

class ColorLogFormatter(logging.Formatter):
    BOLD = "\x1b[1m"
    GREY = "\x1b[38;2;150;150;150m"
    PURPLE = "\x1b[38;2;170;120;255m"
    """ログレベルに応じてコンソール出力に色を付けるFormatter"""
    LOG_COLORS = {
        logging.DEBUG: "\x1b[38;2;150;150;150m",  # Grey
        logging.INFO: "\x1b[38;2;100;150;255m",  # Blue
        logging.WARNING: "\x1b[38;2;255;255;0m",   # Yellow
        logging.ERROR: "\x1b[38;2;255;100;100m", # Red
        logging.CRITICAL: "\x1b[31;1m", # Bold Red
    }
    RESET = "\x1b[0m"

    def __init__(self, fmt: Optional[str] = "%(asctime)s %(levelname)-8s %(name)s: %(message)s", datefmt: Optional[str] = None, style: _FormatStyle = '%'):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def format(self, record: logging.LogRecord) -> str:
        # 副作用を避けるため、元の値を保持
        original_levelname = record.levelname
        original_name = record.name

        # 1. levelnameを装飾 (太字 + レベル色)
        log_color = self.LOG_COLORS.get(record.levelno, "")
        record.levelname = f"{self.BOLD}{log_color}{original_levelname:<8}{self.RESET}"

        # 2. name (ファイル名) を装飾 (紫色)
        record.name = f"{self.PURPLE}{original_name}{self.RESET}"

        # 3. super().format()で基本的なフォーマットを適用
        formatted_message = super().format(record)

        # 4. asctime部分を装飾 (グレー)
        time_part, rest_part = formatted_message.split(record.levelname, 1)
        decorated_time = f"{self.BOLD}{self.GREY}{time_part.strip()}{self.RESET}"
        final_message = f"{decorated_time} {record.levelname}{rest_part}"

        # 5. recordオブジェクトを元に戻す
        record.levelname = original_levelname
        record.name = original_name

        return final_message

def setup_logging(level: int) -> None:
    """コンソール(色付き)とファイル(色なし)へ出力する root logger を構築します。"""
    # 既存ハンドラを初期化
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # --- ファイルハンドラ (色なし) ---
    file_formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    file_handler = logging.FileHandler("discord.log", encoding="utf-8", mode="w")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    # --- コンソールハンドラ (色付き) ---
    console_formatter = ColorLogFormatter()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(console_formatter)
    stream_handler.setLevel(level)

    logging.basicConfig(level=level, handlers=[file_handler, stream_handler])

def main() -> None:
    parser = argparse.ArgumentParser(description="起動時のログレベルを設定")
    parser.add_argument(
        "--log-level", "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="ログ出力のレベル (既定: INFO)"
    )
    args = parser.parse_args()
    level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(level)
    bot.run(level)

if __name__ == "__main__":
    main()
