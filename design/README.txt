HAWKS AI V8 Web Design Package

内容:
- design_tokens.json: カラー・レイアウト定義
- hawks_v8_final.css: 完成デザインCSS
- apply_hawks_v8_design.py: /opt/hawks-ai/app.py へ反映するパッチ
- README.txt: 実行手順

server-01 推奨手順:
1. 4ファイルを /opt/hawks-ai/design/ に配置
2. cd /opt/hawks-ai/design
3. python3 apply_hawks_v8_design.py
4. python3 -m py_compile /opt/hawks-ai/app.py && echo "PYTHON OK"
5. docker cp /opt/hawks-ai/app.py hawks-app:/app/app.py
6. docker restart hawks-app

パッチ実行前に /home/user/hawks-backup/ へタイムスタンプ付きバックアップを作成します。
