"""Slack API (chat.postMessage) で指定チャンネルにメッセージを投稿する。

対象:
  ワークスペース: API-test
  チャンネル名: all-api-test

使い方:
  1. config/slack.json に bot_token と channel_id を自分で記入する
  2. python post_slack_message.py
  3. 文面を変える場合: python post_slack_message.py "投稿したいメッセージ"

Bot には chat:write スコープが必要です。
チャンネルに Bot がいないときは、Slack で /invite @ボット名 を実行してください。
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("config") / "slack.json"
DEFAULT_MESSAGE = "API連携のテスト投稿です。"
POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"

ERROR_HINTS = {
    "not_in_channel": "Bot がチャンネルに参加していません。Slack で /invite @ボット名 を実行してください。",
    "channel_not_found": "チャンネルIDが見つかりません。all-api-test のチャンネルIDを確認してください。",
    "invalid_auth": "トークンが無効です。Bot User OAuth Token を確認してください。",
    "not_authed": "トークンがありません。config/slack.json の bot_token を記入してください。",
    "missing_scope": "権限が足りません。Bot に chat:write スコープを付けて、アプリを再インストールしてください。",
    "is_archived": "チャンネルがアーカイブされています。",
    "msg_too_long": "メッセージが長すぎます。",
}


def load_settings(path: Path = CONFIG_PATH) -> tuple[str, str]:
    """config フォルダの設定ファイルからトークンとチャンネルIDを読む。"""
    try:
        with path.open(encoding="utf-8") as file:
            config = json.load(file)
    except FileNotFoundError:
        raise SystemExit(f"設定ファイルが見つかりません: {path}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(f"設定ファイルの形式が正しくありません: {error}") from error

    token = str(config.get("bot_token", "")).strip()
    channel_id = str(config.get("channel_id", "")).strip()
    if not token:
        raise SystemExit(
            f"bot_token が空です。{path} に Bot User OAuth Token を記入してください。"
        )
    if not token.startswith("xoxb-"):
        raise SystemExit(
            "bot_token は Bot User OAuth Token（xoxb- で始まる文字列）を記入してください。"
        )
    if not channel_id:
        raise SystemExit(
            f"channel_id が空です。{path} に all-api-test のチャンネルIDを記入してください。"
        )
    return token, channel_id


def post_message(token: str, channel_id: str, text: str) -> dict:
    """chat.postMessage を呼び、Slack の JSON 応答を返す。"""
    payload = json.dumps({"channel": channel_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        POST_MESSAGE_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"APIリクエストに失敗しました (HTTP {error.code}): {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise SystemExit(f"Slack に接続できませんでした: {error.reason}") from error

    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Slack の応答を解釈できませんでした: {body}") from error


def raise_if_failed(data: dict) -> None:
    """Slack は失敗時も HTTP 200 を返すため、ok を確認する。"""
    if data.get("ok"):
        return
    error_code = str(data.get("error", "unknown_error"))
    hint = ERROR_HINTS.get(error_code)
    message = f"投稿に失敗しました: {error_code}"
    if hint:
        message = f"{message}\n{hint}"
    raise SystemExit(message)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    token, channel_id = load_settings()
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:]).strip()
    else:
        text = DEFAULT_MESSAGE
    if not text:
        raise SystemExit("投稿するメッセージが空です。")

    result = post_message(token, channel_id, text)
    raise_if_failed(result)

    print("投稿しました。")
    print(f"チャンネルID: {result.get('channel', channel_id)}")
    print(f"メッセージ: {text}")
    print(f"タイムスタンプ: {result.get('ts', '')}")


if __name__ == "__main__":
    main()
