import collections
import re
import spacy
from spacy.matcher import Matcher # Matcherをインポート

def _find_longest_patterns_generic(sequence, min_length, examples_map=None):
    """
    サフィックス/LCP配列を用いてシーケンスから最長の繰り返しパターンを見つける汎用関数。
    """
    if not sequence or len(sequence) < min_length:
        return []

    # Step 1: サフィックス配列の構築
    print(f"Building suffix array for sequence of length {len(sequence)}...")
    suffix_array = sorted(range(len(sequence)), key=lambda i: sequence[i:])

    # Step 2: LCP配列の構築
    print("Building LCP arrays...")
    lcp_array = [0] * len(sequence)
    for i in range(1, len(sequence)):
        idx1, idx2 = suffix_array[i-1], suffix_array[i]
        lcp = 0
        while (idx1 + lcp < len(sequence) and
               idx2 + lcp < len(sequence) and
               sequence[idx1 + lcp] == sequence[idx2 + lcp]):
            lcp += 1
        lcp_array[i] = lcp

    # Step 3: LCP配列から繰り返しパターンを抽出
    print("Extracting repeated patterns...")
    repeated_patterns = collections.defaultdict(int)
    for i in range(1, len(lcp_array)):
        lcp = lcp_array[i]
        if lcp < min_length:
            continue

        pattern = sequence[suffix_array[i] : suffix_array[i] + lcp]
        count = 2
        for j in range(i + 1, len(lcp_array)):
            if lcp_array[j] >= lcp:
                count += 1
            else:
                break
        
        repeated_patterns[pattern] = max(repeated_patterns.get(pattern, 0), count)

    # Step 4: 最長パターンをフィルタリング
    print("Filtering longest patterns...")
    final_patterns = {}
    joiner = " "
    
    sorted_patterns = sorted(repeated_patterns.items(), key=lambda item: len(item[0]), reverse=True)

    for pattern_seq, count in sorted_patterns:
        pattern_str = joiner.join(pattern_seq)

        is_sub_pattern = False
        for existing_pattern in final_patterns.keys():
            if pattern_str in existing_pattern:
                is_sub_pattern = True
                break
        
        if not is_sub_pattern:
            example_text = ""
            if examples_map and pattern_seq in examples_map and examples_map[pattern_seq]:
                example_text = examples_map[pattern_seq][0]
            final_patterns[pattern_str] = (count, example_text)

    # Step 5: 結果をソート
    results = []
    for pattern_str, (count, example) in final_patterns.items():
        results.append((pattern_str, count, example))
    
    results.sort(key=lambda x: (len(x[0].split()), x[1]), reverse=True)
    return results


def find_longest_token_patterns(file_paths, min_pattern_length=2):
    """
    複数のファイルから最長一致する「トークン（単語）」パターンを抽出します。
    """
    print("\n--- Starting analysis of Token patterns ---")
    all_words = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                words = re.findall(r'\b\w+\b', f.read().lower())
                all_words.extend(words)
        except Exception as e:
            print(f"Error: Failed to load the file '{file_path}'.: {e}")
            continue
    
    return _find_longest_patterns_generic(tuple(all_words), min_pattern_length)


def find_longest_generalized_patterns(file_paths, min_pattern_length=3):
    """
    spaCyを使って名詞句と動詞句を一般化し、最長の構文パターンを抽出します。
    """
    print("\n--- Starting analysis of noun/verb phrases + words patterns ---")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Error: spaCy's model 'en_core_web_sm' is not found.")
        print("Command: Please run `python -m spacy download en_core_web_sm`")
        return []

    all_text = ""
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_text += f.read().replace('\n', ' ') + " "
        except Exception as e:
            print(f"Error: Failed to load the file '{file_path}'.: {e}")
            continue
    all_text = re.sub(r'\s+', ' ', all_text)

    print("Performing language analysis with spaCy... (Processing may take longer for large texts)")
    doc = nlp(all_text)

    # 1. Matcherを準備し、動詞句のパターンを定義
    matcher = Matcher(nlp.vocab)
    verb_pattern = [{"POS": "ADV", "OP": "*"}, {"POS": "AUX", "OP": "*"}, {"POS": "VERB", "OP": "+"}]
    matcher.add("VERB_PHRASE", [verb_pattern])

    # 2. 名詞句と動詞句をそれぞれ抽出
    noun_chunks = list(doc.noun_chunks)
    verb_matches = matcher(doc)

    # 3. 重複を解決（名詞句を優先）
    noun_chunk_tokens = {i for chunk in noun_chunks for i in range(chunk.start, chunk.end)}
    
    filtered_verb_spans = []
    for match_id, start, end in verb_matches:
        if not any(i in noun_chunk_tokens for i in range(start, end)):
            filtered_verb_spans.append(doc[start:end])

    # 4. すべての句を一つの辞書にまとめる
    phrase_lookup = {}
    for chunk in noun_chunks:
        phrase_lookup[chunk.start] = ("NOUN_PHRASE", chunk)
    for span in filtered_verb_spans:
        phrase_lookup[span.start] = ("VERB_PHRASE", span)

    # 5. 句と単語を組み合わせた一般化シーケンスを作成
    doc_tokens_generalized = []
    i = 0
    while i < len(doc):
        if i in phrase_lookup:
            label, span = phrase_lookup[i]
            doc_tokens_generalized.append((label, span.text.strip()))
            i = span.end
        else:
            token = doc[i]
            if not token.is_punct and not token.is_space:
                # ▼▼▼【修正】元の単語(token.lower_)から品詞タグ(token.pos_)に戻します ▼▼▼
                doc_tokens_generalized.append((token.pos_, token.text))
            i += 1

    generalized_sequence = tuple(item[0] for item in doc_tokens_generalized)
    
    examples_map = collections.defaultdict(list)
    for i in range(len(doc_tokens_generalized)):
        for length in range(min_pattern_length, len(doc_tokens_generalized) - i + 1):
            pattern_gen = tuple(item[0] for item in doc_tokens_generalized[i:i+length])
            pattern_text = " ".join(item[1] for item in doc_tokens_generalized[i:i+length])
            
            if len(examples_map[pattern_gen]) < 5:
                examples_map[pattern_gen].append(pattern_text)

    print(f"Analyzing patterns with generalized sequence length {len(generalized_sequence)}.")
    return _find_longest_patterns_generic(generalized_sequence, min_pattern_length, examples_map)


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

        # 1. トークン（単語）パターンの解析と出力
        token_patterns = find_longest_token_patterns(file_paths_to_analyze, min_pattern_length=2)
        print("\n--- ✅ output: longest token (word) patterns ---")
        if token_patterns:
            for i, (pattern, count, _) in enumerate(token_patterns):
                print(f"{i+1}. '{pattern}' (x{count})")
        else:
            print("No matching Token patterns were found.")
        print("-" * 40)

        # 2. 一般化（名詞句/動詞句 + 品詞）パターンの解析と出力
        generalized_patterns = find_longest_generalized_patterns(file_paths_to_analyze, min_pattern_length=3)
        print("\n--- ✅ output: longest generalized (phrases + POS) patterns ---")
        if generalized_patterns:
            for i, (pattern, count, example) in enumerate(generalized_patterns):
                print(f"{i+1}. '{pattern}' (x{count})")
                if example:
                    print(f"   └ ex: \"{example}\"")
        else:
            print("No matching patterns were found.")
        print("-" * 40)