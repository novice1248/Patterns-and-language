import collections
import os

def find_longest_matching_patterns(file_paths, min_pattern_length=2):
    """
    複数のファイルから最長一致する文章パターンを、パターンの長さ、そして出現回数の多い順に抽出します。

    Args:
        file_paths (list): 読み込むテキストファイルのパスのリスト。
        min_pattern_length (int): 考慮する最小のパターン長（単語数）。

    Returns:
        list: (パターン, 出現回数) のタプルのリスト。パターンの長さ、出現回数の順でソートされます。
    """
    all_words = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().lower()  # 小文字に統一して比較
                # ここでは簡単な単語分割を使用しますが、より高度なトークナイザ（例: NLTKのword_tokenize）も利用可能
                words = [word for word in text.split() if word.isalnum()] # 英数字のみを抽出
                all_words.extend(words)
        except FileNotFoundError:
            print(f"エラー: ファイル '{file_path}' が見つかりません。パスを確認してください。")
            continue
        except Exception as e:
            print(f"ファイル '{file_path}' の読み込み中にエラーが発生しました: {e}")
            continue

    if not all_words:
        print("エラー: 処理できる単語が見つかりませんでした。ファイルが空か、読み込みエラーが発生した可能性があります。")
        return []

    # 全てのN-gramを生成し、出現回数をカウント
    pattern_counts = collections.defaultdict(int)
    for length in range(len(all_words), min_pattern_length - 1, -1):
        for i in range(len(all_words) - length + 1):
            pattern_tuple = tuple(all_words[i : i + length])
            pattern_counts[pattern_tuple] += 1

    # 重複するパターンを排除し、最長の一致パターンを特定
    final_patterns = {}
    for pattern_tuple, count in pattern_counts.items():
        if count > 1: # 複数回出現するパターンのみを対象
            pattern_str = " ".join(pattern_tuple)
            
            skip_current_pattern = False
            for existing_pattern_str in list(final_patterns.keys()):
                if pattern_str in existing_pattern_str and len(pattern_str) < len(existing_pattern_str):
                    skip_current_pattern = True
                    break
            if skip_current_pattern:
                continue

            patterns_to_remove = []
            for existing_pattern_str in list(final_patterns.keys()):
                if existing_pattern_str in pattern_str and len(existing_pattern_str) < len(pattern_str):
                    patterns_to_remove.append(existing_pattern_str)
            for p in patterns_to_remove:
                del final_patterns[p]
            
            if pattern_str not in final_patterns or \
               (len(pattern_str) > len(final_patterns[pattern_str][1])) or \
               (len(pattern_str) == len(final_patterns[pattern_str][1]) and count > final_patterns[pattern_str][0]):
                final_patterns[pattern_str] = (count, pattern_tuple)


    # (出現回数, パターン文字列) のリストを作成し、ソート
    results = []
    for pattern_str, (count, _) in final_patterns.items():
        if count > 1: # 複数回出現するものだけを最終結果に含める
            results.append((pattern_str, count))

    # ▼▼▼ 修正箇所 ▼▼▼
    # パターンが長い順、次に出現回数が多い順にソート
    results.sort(key=lambda x: (len(x[0].split()), x[1]), reverse=True)
    # ▲▲▲ 修正箇所 ▲▲▲

    return results

# --- 使用例 ---
if __name__ == "__main__":
    # ここに分析したいファイルのパスを直接指定してください
    # スクリプトからの相対パス、または絶対パスで指定できます
    # 例:
    file_paths_to_analyze = [
        '../SampleText/TeacherAndParentArrestedForStealingExams.txt',
        '../SampleText/HowtoPlanthePerfectRoadTrip.txt',
        '../SampleText/TrumpWantsRealSugarInCoke,BuyersWantNone.txt',
        '../SampleText/WorldsMostExpensiveCheeseSoldFor42,000.txt',
    ]

    if not file_paths_to_analyze:
        print("処理するテキストファイルが指定されていません。`file_paths_to_analyze` リストにファイルパスを追加してください。")
    else:
        print(f"以下のファイルを分析します: {file_paths_to_analyze}")
        longest_patterns = find_longest_matching_patterns(file_paths_to_analyze)

        print("\n--- output: longest word token patterns ---")
        if longest_patterns:
            for i, (pattern, count) in enumerate(longest_patterns):
                print(f"{i+1}. {pattern} (x{count})")
        else:
            print("一致するパターンは見つかりませんでした。")