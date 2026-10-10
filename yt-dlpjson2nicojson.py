#!/usr/bin/env python3
"""
ニコニコ動画コメントデータ変換スクリプト
yt-dlpで取得したニコニコのコメントJSON、またはYouTubeのlive_chat.jsonを変換する
使用方法: python yt-dlpjson2nicojson.py [input.json] [output.json]
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from itertools import groupby
from datetime import datetime, timezone, timedelta


def get_fork(comment: Dict[str, Any]) -> str:
    """コメントのforkタイプを判定"""
    commands = comment.get("commands", [])
    
    if len(commands) == 0:
        return "owner"
    elif "184" in commands:
        return "main"
    else:
        return "easy"


def get_message_text(message: Dict[str, Any]) -> str:
    """YouTubeのmessage(runs形式)をテキストに変換"""
    if "simpleText" in message:
        return message["simpleText"]
    texts = []
    for run in message.get("runs", []):
        if "text" in run:
            texts.append(run["text"])
        elif "emoji" in run:
            emoji = run["emoji"]
            shortcuts = emoji.get("shortcuts", [])
            texts.append(shortcuts[0] if shortcuts else emoji.get("emojiId", ""))
    return "".join(texts)


def load_youtube_live_chat(lines: List[str]) -> List[Dict[str, Any]]:
    """YouTubeのlive_chat.json(JSON Lines)をニコニコのコメント形式に変換"""
    jst = timezone(timedelta(hours=9))
    renderer_keys = ("liveChatTextMessageRenderer", "liveChatPaidMessageRenderer")
    comments = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        replay = entry.get("replayChatItemAction", {})
        vpos_ms = int(replay.get("videoOffsetTimeMsec", 0))

        for action in replay.get("actions", []):
            item = action.get("addChatItemAction", {}).get("item", {})
            renderer = next((item[k] for k in renderer_keys if k in item), None)
            if renderer is None:
                continue

            body = get_message_text(renderer.get("message", {}))
            if not body:
                continue

            timestamp_usec = int(renderer.get("timestampUsec", 0))
            posted_at = datetime.fromtimestamp(timestamp_usec / 1_000_000, tz=jst)

            comments.append({
                "body": body,
                "commands": ["184"],
                "id": renderer.get("id", ""),
                "isMyPost": False,
                "isPremium": False,
                "nicoruCount": 0,
                "nicoruId": None,
                "postedAt": posted_at.isoformat(timespec="seconds"),
                "score": 0,
                "source": "leaf",
                "userId": renderer.get("authorExternalChannelId", ""),
                "vposMs": vpos_ms,
            })

    comments.sort(key=lambda c: c["vposMs"])
    for no, comment in enumerate(comments, start=1):
        comment["no"] = no
    return comments


def load_comments(input_path: Path) -> List[Dict[str, Any]]:
    """入力ファイルを読み込み、形式を判定してコメントリストを返す"""
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 複数行のJSON Lines → YouTube live chat
        return load_youtube_live_chat(text.splitlines())

    if isinstance(data, list):
        # ニコニコのコメントJSON
        return data
    # 1行だけのYouTube live chat
    return load_youtube_live_chat(text.splitlines())


def convert_comments(comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """コメントリストを新形式に変換"""
    
    # スレッドID（固定値）
    thread_id = "1693580826"
    
    # fork別にソートしてグループ化
    sorted_comments = sorted(comments, key=get_fork)
    grouped = groupby(sorted_comments, key=get_fork)
    
    # スレッド配列を作成
    threads = []
    for fork_type, group_comments in grouped:
        comment_list = list(group_comments)
        thread = {
            "commentCount": len(comment_list),
            "comments": comment_list,
            "fork": fork_type,
            "id": thread_id
        }
        threads.append(thread)
    
    # globalCommentsのカウント（mainフォークのコメント数）
    main_comments = [c for c in comments if get_fork(c) == "main"]
    global_comment_count = len(main_comments)
    
    # 最終的な出力構造
    output = {
        "data": {
            "globalComments": [
                {
                    "count": global_comment_count,
                    "id": thread_id
                }
            ],
            "threads": threads
        },
        "meta": {
            "status": 200
        }
    }
    
    return output


def main():
    """メイン処理"""
    # 引数の取得
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # 入力ファイルの存在確認
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"エラー: 入力ファイル '{input_file}' が見つかりません", file=sys.stderr)
        sys.exit(1)
    
    try:
        # JSONファイルを読み込み
        comments = load_comments(input_path)
        
        # 変換処理
        output = convert_comments(comments)
        
        # JSONファイルに出力
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
        
        print(f"変換完了: {output_file}")
        
    except json.JSONDecodeError as e:
        print(f"エラー: JSONの解析に失敗しました - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 変換に失敗しました - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
