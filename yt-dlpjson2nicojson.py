#!/usr/bin/env python3
"""
ニコニコ動画コメントデータ変換スクリプト
使用方法: python convert.py [input.json] [output.json]
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from itertools import groupby


def get_fork(comment: Dict[str, Any]) -> str:
    """コメントのforkタイプを判定"""
    commands = comment.get("commands", [])
    
    if len(commands) == 0:
        return "owner"
    elif "184" in commands:
        return "main"
    else:
        return "easy"


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
        with open(input_path, "r", encoding="utf-8") as f:
            comments = json.load(f)
        
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
