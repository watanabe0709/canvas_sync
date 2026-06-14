# Canvas to Notion Auto-Sync 🎓🚀

Canvas LMS（K-LMS）の未提出課題を自動的に取得し、Notionのタスク管理データベースに自動登録するPythonスクリプトです。
macOSの `launchd` を使用することで、PCを開いた時や指定した時間にバックグラウンドで完全自動実行されます。

## ✨ 機能 (Features)

- **自動取得**: 今後7日間に期限を迎える未提出の課題・クイズをCanvas APIから取得します。
- **重複防止**: すでにNotionに登録されている課題はスキップされるため、タスクが二重に登録されることはありません。
- **Notion連携**: 課題名、期日、科目名、URLをNotionのデータベースに自動入力し、「日次」「課題」などのラベルも自動付与します。
- **完全自動化**: Mac標準の `launchd` を用いて、ユーザーが意識することなく裏側で定期実行されます。

## 🛠️ 必要条件 (Prerequisites)

- macOS環境 (自動化に `launchd` を使用するため)
- Python 3.x
- Canvas LMSの無期限アクセストークン
- Notion APIのインテグレーショントークン
- NotionのデータベースID

## 🚀 セットアップ (Setup)

### 1. リポジトリのクローンと環境構築
```bash
# 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# 必要なライブラリのインストール
pip install requests python-dotenv