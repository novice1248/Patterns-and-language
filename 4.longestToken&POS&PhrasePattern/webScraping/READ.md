### 1. バックエンドのセットアップと起動

```bash
# バックエンドのディレクトリに移動
cd path/to/your/webscraping/backend

# 仮想環境を作成して有効化
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate    # Windows

# ライブラリをインストール
pip install fastapi "uvicorn[standard]" python-multipart spacy requests beautifulsoup4

# spaCyの言語モデルをダウンロード
python -m spacy download en_core_web_sm

# バックエンドサーバーを起動
uvicorn main:app --reload

2. フロントエンドのセットアップと起動
# フロントエンドのディレクトリに移動
cd path/to/your/webscraping/frontend

# ライブラリをインストール
npm install

# 開発サーバーを起動
npm start
