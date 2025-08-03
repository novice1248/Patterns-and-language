import collections

def find_longest_matching_patterns_efficient(file_paths, min_pattern_length=2):
    """
    複数のファイルから最長一致する文章パターンを効率的に抽出します。
    サフィックス配列とLCP配列のアプローチを利用して高速化しています。

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
                text = f.read().lower()
                words = [word for word in text.split() if word.isalnum()]
                all_words.extend(words)
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found. Please check the path.")
            continue
        except Exception as e:
            print(f"Error: Failed to load the file '{file_path}'.: {e}")
            continue

    if len(all_words) < min_pattern_length:
        return []

    # --- Step 1: サフィックス配列の構築 ---
    # すべてのサフィックス（接尾辞）の開始インデックスを辞書順にソートして保持
    # 注: Pythonのソートは比較に時間がかかるため、巨大なテキストではここがボトルネックになり得る
    #     より高速なSA-ISなどのアルゴリズムも存在するが、可読性のためシンプルな実装に
    print("Building suffix array...")
    suffix_array = sorted(range(len(all_words)), key=lambda i: all_words[i:])
    
    # --- Step 2: LCP配列の構築 ---
    # LCP (Longest Common Prefix) 配列は、ソート済みサフィックス配列で隣り合う要素同士が
    # 先頭から何単語一致しているかを保持する
    print("Building LCP array...")
    lcp_array = [0] * len(all_words)
    for i in range(1, len(all_words)):
        idx1 = suffix_array[i-1]
        idx2 = suffix_array[i]
        lcp = 0
        while (idx1 + lcp < len(all_words) and
               idx2 + lcp < len(all_words) and
               all_words[idx1 + lcp] == all_words[idx2 + lcp]):
            lcp += 1
        lcp_array[i] = lcp

    # --- Step 3: LCP配列から繰り返しパターンを抽出 ---
    print("Extracting repeated patterns...")
    repeated_patterns = collections.defaultdict(int)
    for i in range(1, len(lcp_array)):
        lcp = lcp_array[i]
        if lcp >= min_pattern_length:
            # LCP値がkである場合、長さkのパターンが少なくとも2回出現している
            pattern_tuple = tuple(all_words[suffix_array[i] : suffix_array[i] + lcp])
            
            # 出現回数を正確にカウントする
            # LCPがkの箇所が連続している間、そのパターンは繰り返し出現している
            count = 2
            for j in range(i + 1, len(lcp_array)):
                if lcp_array[j] >= lcp:
                    count += 1
                else:
                    break
            
            # すでにより多くの回数でカウントされている場合は更新しない
            if repeated_patterns[pattern_tuple] < count:
                 repeated_patterns[pattern_tuple] = count

    # --- Step 4: 最長パターンをフィルタリング ---
    # サブパターン（より長いパターンに含まれる短いパターン）を除外する
    print("Filtering longest patterns...")
    
    # パターンを長さの降順でソート
    sorted_patterns = sorted(repeated_patterns.items(), key=lambda item: len(item[0]), reverse=True)
    
    final_patterns = {}
    for pattern_tuple, count in sorted_patterns:
        pattern_str = " ".join(pattern_tuple)
        is_sub_pattern = False
        # すでに追加済みの、より長いパターンに含まれていないかチェック
        for existing_pattern in final_patterns.keys():
            if pattern_str in existing_pattern:
                is_sub_pattern = True
                break
        
        if not is_sub_pattern:
            final_patterns[pattern_str] = count

    # --- Step 5: 結果をソート ---
    results = list(final_patterns.items())
    results.sort(key=lambda x: (len(x[0].split()), x[1]), reverse=True)

    return results

# --- 使用例 ---
if __name__ == "__main__":
    file_paths_to_analyze = [
        '../SampleText/TeacherAndParentArrestedForStealingExams.txt',
        '../SampleText/HowtoPlanthePerfectRoadTrip.txt',
        '../SampleText/TrumpWantsRealSugarInCoke,BuyersWantNone.txt',
        '../SampleText/WorldsMostExpensiveCheeseSoldFor42,000.txt',
    ]

    if not file_paths_to_analyze:
        print("Error: No text files specified for processing. Please add file paths to the `file_paths_to_analyze` list.")
    else:
        print(f"Analyzing the following files: {file_paths_to_analyze}")
        # 効率化された関数を呼び出す
        longest_patterns = find_longest_matching_patterns_efficient(file_paths_to_analyze)

        print("\n--- output: longest word token patterns ---")
        if longest_patterns:
            for i, (pattern, count) in enumerate(longest_patterns):
                print(f"{i+1}. {pattern} (x{count})")
        else:
            print("No matching patterns were found.")