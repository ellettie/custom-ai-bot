import argparse
import logging
import bot

def setup_logging(level: int) -> None:
    """コンソールとファイルへ同じフォーマット・レベルで出力する root logger を構築します。"""
    # 既存ハンドラを初期化
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    # File (毎回新規作成)
    file_handler = logging.FileHandler("discord.log", encoding="utf-8", mode="w")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    logging.basicConfig(level=level, handlers=[file_handler])

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
