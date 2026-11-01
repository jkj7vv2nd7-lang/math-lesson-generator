@echo off
chcp 65001 >nul
title 数学教材ジェネレーター
cd /d "%~dp0"

echo ==================================================
echo   数学教材ジェネレーター
echo ==================================================
echo.
echo   この黒い画面はアプリ本体です。
echo   使い終わるまで、閉じないでください。
echo.
echo   準備ができると、ブラウザが自動で開きます。
echo   開かない場合は、ブラウザで次のアドレスを開いてください。
echo     http://127.0.0.1:5000
echo.
echo   起動の途中で、赤い文字の注意書きが出ることが
echo   ありますが、正常です。心配いりません。
echo.
echo   終わるときは、この画面を閉じるか、
echo   キーボードの Ctrl + C を押してください。
echo ==================================================
echo.

python --version >nul 2>nul
if errorlevel 1 goto nopython

echo 準備をしています。少しお待ちください…
echo （初回だけ、部品の準備に数分かかることがあります）
python -m pip install -r requirements.txt --quiet --disable-pip-version-check >nul 2>nul
if errorlevel 1 goto piperror

echo 準備ができました。アプリを起動します…
echo.
python app.py

echo.
echo アプリを終了しました。この画面は閉じてかまいません。
pause
exit /b 0

:nopython
echo.
echo ==================================================
echo   Python が見つかりませんでした。
echo ==================================================
echo   このアプリを使うには、先に Python の
echo   インストールが必要です。
echo   公式サイト https://www.python.org/ から
echo   Python をインストールしてください。
echo   インストールのときは「Add python.exe to PATH」に
echo   チェックを入れるのがおすすめです。
echo   そのあと、もう一度 start.bat を
echo   ダブルクリックしてください。
echo ==================================================
echo.
pause
exit /b 1

:piperror
echo.
echo ==================================================
echo   準備（部品のインストール）に失敗しました。
echo ==================================================
echo   インターネット接続を確認してから、
echo   もう一度 start.bat をダブルクリックして
echo   みてください。
echo   それでも直らない場合は、フォルダ内の
echo   「はじめにお読みください」をご確認ください。
echo ==================================================
echo.
pause
exit /b 1
