import collections
import re
import spacy
from spacy.matcher import Matcher
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

# --------------------------------------------------
# FastAPIアプリの初期化とCORS設定
# --------------------------------------------------
app = FastAPI()

# フロントエンドからのアクセスを許可する設定
origins = [
    "http://localhost",
    "http://localhost:3000", # create-react-appのデフォルトポート
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# 元の分析ロジック（変更なし）
# --------------------------------------------------
def scrape_text_from_url(url: str):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        return ' '.join(soup.stripped_strings)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def _find_longest_patterns_generic(sequence, min_length, examples_map=None):
    if not sequence or len(sequence) < min_length:
        return []
    suffix_array = sorted(range(len(sequence)), key=lambda i: sequence[i:])
    lcp_array = [0] * len(sequence)
    for i in range(1, len(sequence)):
        idx1, idx2 = suffix_array[i-1], suffix_array[i]
        lcp = 0
        while (idx1 + lcp < len(sequence) and idx2 + lcp < len(sequence) and sequence[idx1 + lcp] == sequence[idx2 + lcp]):
            lcp += 1
        lcp_array[i] = lcp
    repeated_patterns = collections.defaultdict(int)
    for i in range(1, len(lcp_array)):
        lcp = lcp_array[i]
        if lcp < min_length: continue
        pattern = sequence[suffix_array[i] : suffix_array[i] + lcp]
        count = 2
        for j in range(i + 1, len(lcp_array)):
            if lcp_array[j] >= lcp: count += 1
            else: break
        repeated_patterns[pattern] = max(repeated_patterns.get(pattern, 0), count)
    final_patterns = {}
    joiner = " "
    sorted_patterns = sorted(repeated_patterns.items(), key=lambda item: len(item[0]), reverse=True)
    for pattern_seq, count in sorted_patterns:
        pattern_str = joiner.join(pattern_seq)
        is_sub_pattern = any(pattern_str in existing_pattern for existing_pattern in final_patterns.keys())
        if not is_sub_pattern:
            example_text = ""
            if examples_map and pattern_seq in examples_map and examples_map[pattern_seq]:
                example_text = examples_map[pattern_seq][0]
            final_patterns[pattern_str] = (count, example_text)
    results = [{"pattern": pattern_str, "count": count, "example": example} for pattern_str, (count, example) in final_patterns.items()]
    results.sort(key=lambda x: (len(x["pattern"].split()), x["count"]), reverse=True)
    return results

def find_longest_token_patterns(urls: List[str], min_pattern_length=3):
    all_words = []
    for url in urls:
        text = scrape_text_from_url(url)
        if text:
            all_words.extend(re.findall(r'\b\w+\b', text.lower()))
    return _find_longest_patterns_generic(tuple(all_words), min_pattern_length)

def find_longest_generalized_patterns(urls: List[str], min_pattern_length=3):
    try:
        nlp = spacy.load("en_core_web_sm", disable=["ner"])
    except OSError:
        return {"error": "spaCy model not found. Please run 'python -m spacy download en_core_web_sm'"}
    
    texts_to_process = [text for url in urls if (text := scrape_text_from_url(url))]
    if not texts_to_process:
        return []

    doc_tokens_generalized = []
    for doc in nlp.pipe(texts_to_process):
        matcher = Matcher(nlp.vocab)
        verb_pattern = [{"POS": "ADV", "OP": "*"}, {"POS": "AUX", "OP": "*"}, {"POS": "VERB", "OP": "+"}]
        matcher.add("VERB_PHRASE", [verb_pattern])
        
        noun_chunks = list(doc.noun_chunks)
        verb_matches = matcher(doc)
        noun_chunk_tokens = {i for chunk in noun_chunks for i in range(chunk.start, chunk.end)}
        
        filtered_verb_spans = [doc[start:end] for _, start, end in verb_matches if not any(i in noun_chunk_tokens for i in range(start, end))]
        
        phrase_lookup = {chunk.start: ("NOUN_PHRASE", chunk) for chunk in noun_chunks}
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
                
    return _find_longest_patterns_generic(generalized_sequence, min_pattern_length, examples_map)

# --------------------------------------------------
# APIのリクエスト/レスポンスのデータモデル定義
# --------------------------------------------------
class UrlsRequest(BaseModel):
    urls: List[str] = Field(..., example=["https://en.wikipedia.org/wiki/Web_scraping"])

class PatternResult(BaseModel):
    pattern: str
    count: int
    example: str

class AnalysisResponse(BaseModel):
    token_patterns: List[PatternResult]
    generalized_patterns: List[PatternResult]

# --------------------------------------------------
# APIエンドポイントの定義
# --------------------------------------------------
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_urls(request: UrlsRequest):
    """
    URLリストを受け取り、トークンパターンと一般化パターンを分析して返す
    """
    token_patterns = find_longest_token_patterns(request.urls, min_pattern_length=3)
    generalized_patterns = find_longest_generalized_patterns(request.urls, min_pattern_length=3)
    
    return {
        "token_patterns": token_patterns[:20],  # 結果を20件に制限
        "generalized_patterns": generalized_patterns[:20]
    }
