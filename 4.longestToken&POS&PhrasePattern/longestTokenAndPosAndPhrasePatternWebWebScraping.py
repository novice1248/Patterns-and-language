import collections
import re
import spacy
from spacy.matcher import Matcher
import requests
from bs4 import BeautifulSoup

def scrape_text_from_url(url):
    """
    指定されたURLからHTMLを取得し、主要なテキストコンテンツを抽出する。
    """
    print(f"Loading text from URL: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        text = ' '.join(soup.stripped_strings)
        return text
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to retrieve URL '{url}'. {e}")
        return ""
    except Exception as e:
        print(f"エラー: An unexpected error occurred while processing URL '{url}'. {e}")
        return ""

def _find_longest_patterns_generic(sequence, min_length, examples_map=None):
    """
    サフィックス/LCP配列を用いてシーケンスから最長の繰り返しパターンを見つける汎用関数。
    """
    if not sequence or len(sequence) < min_length:
        return []
    print(f"Building suffix array for sequence of length {len(sequence)}...")
    suffix_array = sorted(range(len(sequence)), key=lambda i: sequence[i:])
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
    results = []
    for pattern_str, (count, example) in final_patterns.items():
        results.append((pattern_str, count, example))
    results.sort(key=lambda x: (len(x[0].split()), x[1]), reverse=True)
    return results

def find_longest_token_patterns(urls, min_pattern_length=2):
    """
    複数のURLからテキストをスクレイピングし、最長一致する「トークン（単語）」パターンを抽出します。
    """
    print("\n--- Starting analysis of Token patterns ---")
    all_words = []
    for url in urls:
        text = scrape_text_from_url(url)
        if text:
            words = re.findall(r'\b\w+\b', text.lower())
            all_words.extend(words)
    return _find_longest_patterns_generic(tuple(all_words), min_pattern_length)

def find_longest_generalized_patterns(urls, min_pattern_length=3):
    """
    複数のURLからテキストをスクレイピングし、spaCyで一般化して最長の構文パターンを抽出します。
    """
    print("\n--- Starting analysis of noun/verb phrases + words patterns ---")
    try:
        nlp = spacy.load("en_core_web_sm", disable=["ner"])
    except OSError:
        print("Error: spaCy's model 'en_core_web_sm' is not found.")
        print("Command: Please run `python -m spacy download en_core_web_sm`")
        return []

    texts_to_process = []
    for url in urls:
        scraped_text = scrape_text_from_url(url)
        if scraped_text:
            texts_to_process.append(scraped_text)

    if not texts_to_process:
        print("Failed to extract text from the URL. Stopping the process.")
        return []

    print("Performing language analysis with spaCy... (Processing may take longer for large texts)")
    doc_tokens_generalized = []

    for doc in nlp.pipe(texts_to_process):
        matcher = Matcher(nlp.vocab)
        verb_pattern = [{"POS": "ADV", "OP": "*"}, {"POS": "AUX", "OP": "*"}, {"POS": "VERB", "OP": "+"}]
        matcher.add("VERB_PHRASE", [verb_pattern])

        noun_chunks = list(doc.noun_chunks)
        verb_matches = matcher(doc)
        noun_chunk_tokens = {i for chunk in noun_chunks for i in range(chunk.start, chunk.end)}

        filtered_verb_spans = []
        for match_id, start, end in verb_matches:
            if not any(i in noun_chunk_tokens for i in range(start, end)):
                filtered_verb_spans.append(doc[start:end])

        phrase_lookup = {}
        for chunk in noun_chunks:
            phrase_lookup[chunk.start] = ("NOUN_PHRASE", chunk)
        for span in filtered_verb_spans:
            phrase_lookup[span.start] = ("VERB_PHRASE", span)

        i = 0
        while i < len(doc):
            if i in phrase_lookup:
                label, span = phrase_lookup[i]
                doc_tokens_generalized.append((label, span.text.strip()))
                i = span.end
            else:
                token = doc[i]
                if not token.is_punct and not token.is_space:
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


if __name__ == "__main__":
    urls_to_analyze = []
    print("Please enter the URLs of the web pages you want to analyze, one per line.")
    print("To finish input, press Enter without typing anything.")

    while True:
        url = input(f"URL {len(urls_to_analyze) + 1}: ")
        if not url:
            break
        urls_to_analyze.append(url)

    if not urls_to_analyze:
        print("Don't input URL. Stopping the process")
    else:
        print(f"\nAnalyzing the following {len(urls_to_analyze)} URLs:")
        for u in urls_to_analyze:
            print(f"- {u}")

        token_patterns = find_longest_token_patterns(urls_to_analyze, min_pattern_length=3)
        print("\n--- ✅ output: longest token (word) patterns ---")
        if token_patterns:
            for i, (pattern, count, _) in enumerate(token_patterns[:20]):
                print(f"{i+1}. '{pattern}' (x{count})")
        else:
            print("No matching Token patterns were found.")
        print("-" * 40)

        generalized_patterns = find_longest_generalized_patterns(urls_to_analyze, min_pattern_length=3)
        print("\n--- ✅ output: longest generalized (phrases + POS) patterns ---")
        if generalized_patterns:
            for i, (pattern, count, example) in enumerate(generalized_patterns[:20]):
                print(f"{i+1}. '{pattern}' (x{count})")
                if example:
                    print(f"   └ ex: \"{example}\"")
        else:
            print("No matching patterns were found.")
        print("-" * 40)
