import collections
import itertools
import os
import nltk

exclude_chars = {'.', ',', '?', '!', ':', ';', '``', '\'\''}
def contains_excluded_char(pattern):
    return any(any(c in token for c in exclude_chars) for token in pattern)

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
    all_postag = []
    max_pattern_length = 7
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                sentences = nltk.sent_tokenize(text)
                for sentence in sentences:
                    token = nltk.word_tokenize(sentence)
                    pos_tag = nltk.pos_tag(token)
                    # tagged = [pos for word, pos in pos_tag]
                    all_words = all_words + token
                    all_postag = all_postag + pos_tag
        except FileNotFoundError:
            print(f"エラー: ファイル '{file_path}' が見つかりません。パスを確認してください。")
            continue
        except Exception as e:
            print(f"ファイル '{file_path}' の読み込み中にエラーが発生しました: {e}")
            continue

    if not all_words:
        print("エラー: 処理できる単語が見つかりませんでした。ファイルが空か、読み込みエラーが発生した可能性があります。")
        return []

    pattern_counts = collections.defaultdict(int)
    for length in range(max_pattern_length, min_pattern_length - 1, -1):
        for start in range(len(all_postag) - length + 1):
            segment = all_postag[start : start + length]
            # 各位置で 0（word） or 1（label）を選ぶ全組み合わせ
            for choice in itertools.product([0, 1], repeat=length):
                pattern = tuple(item[c] for item, c in zip(segment, choice))
                if contains_excluded_char(pattern):
                    continue
                pattern_counts[pattern] += 1

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
            if pattern_tuple and pattern_tuple[0] not in ['.']:
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

# I want to do something.
# You think that cow want to eat grass.