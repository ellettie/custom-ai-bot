import argparse
import logging
import bot

def main():
    parser = argparse.ArgumentParser(description="起動時のログレベルを設定")
    parser.add_argument(
        "--log-level", "-l",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="ログ出力のレベル (既定: WARNING)"
    )
    args = parser.parse_args()

    # 文字列から logging.LEVEL へ変換
    level = getattr(logging, args.log_level.upper(), logging.WARNING)
    bot.run(level)

if __name__ == "__main__":
    main()
