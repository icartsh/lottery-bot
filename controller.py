import os
import sys
import time

from dotenv import load_dotenv

import auth
import common
import lotto645
import win720
import notification


def _clean_env(value):
    """플레이스홀더(YOUR_...) 값은 미설정으로 취급한다."""
    if value and value.strip().startswith("YOUR_"):
        return None
    return value


def _setup_and_login():
    load_dotenv(override=True)
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')

    webhook_url = _clean_env(os.environ.get('SLACK_WEBHOOK_URL')) \
        or _clean_env(os.environ.get('DISCORD_WEBHOOK_URL'))

    auth_ctrl = auth.AuthController()
    auth_ctrl.login(username, password)

    return auth_ctrl, username, webhook_url


def _buy_lotto645(auth_ctrl: auth.AuthController) -> dict:
    count = int(os.environ.get('COUNT', 5))
    manual_numbers = common.parse_manual_numbers(os.environ.get('MANUAL_NUMBERS'))

    response = lotto645.Lotto645().buy_lotto645(auth_ctrl, count, manual_numbers)
    response['balance'] = auth_ctrl.get_user_balance()
    return response


def _check_lotto645(auth_ctrl: auth.AuthController) -> dict:
    item = lotto645.Lotto645().check_winning(auth_ctrl)
    item['balance'] = auth_ctrl.get_user_balance()
    return item


def _buy_win720(auth_ctrl: auth.AuthController, username: str) -> dict:
    response = win720.Win720().buy_Win720(auth_ctrl, username)
    response['balance'] = auth_ctrl.get_user_balance()
    return response


def _check_win720(auth_ctrl: auth.AuthController) -> dict:
    item = win720.Win720().check_winning(auth_ctrl)
    item['balance'] = auth_ctrl.get_user_balance()
    return item


def buy():
    auth_ctrl, username, webhook_url = _setup_and_login()
    notify = notification.Notification()

    notify.send_lotto_buying_message(_buy_lotto645(auth_ctrl), webhook_url)

    time.sleep(10)

    # 연금복권은 새 세션으로 구매해야 안정적이다
    auth_ctrl.http_client.session.cookies.clear()
    auth_ctrl, username, webhook_url = _setup_and_login()

    notify.send_win720_buying_message(_buy_win720(auth_ctrl, username), webhook_url)


def check():
    auth_ctrl, _, webhook_url = _setup_and_login()
    notify = notification.Notification()

    notify.send_lotto_winning_message(_check_lotto645(auth_ctrl), webhook_url)

    time.sleep(10)

    notify.send_win720_winning_message(_check_win720(auth_ctrl), webhook_url)


def lotto_buy():
    auth_ctrl, _, webhook_url = _setup_and_login()
    notification.Notification().send_lotto_buying_message(_buy_lotto645(auth_ctrl), webhook_url)


def win720_buy():
    auth_ctrl, username, webhook_url = _setup_and_login()
    notification.Notification().send_win720_buying_message(_buy_win720(auth_ctrl, username), webhook_url)


def lotto_check():
    auth_ctrl, _, webhook_url = _setup_and_login()
    notification.Notification().send_lotto_winning_message(_check_lotto645(auth_ctrl), webhook_url)


def win720_check():
    auth_ctrl, _, webhook_url = _setup_and_login()
    notification.Notification().send_win720_winning_message(_check_win720(auth_ctrl), webhook_url)


COMMANDS = {
    "buy": buy,
    "check": check,
    "buy_lotto": lotto_buy,
    "buy_win720": win720_buy,
    "check_lotto": lotto_check,
    "check_win720": win720_check,
}


def run():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python controller.py [{'|'.join(COMMANDS)}]")
        return

    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    run()
