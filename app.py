from flask import Flask, render_template, url_for
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('cafe_management.db')
    conn.row_factory = sqlite3.Row  # 辞書形式で取得
    return conn

# 商品一覧
@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT
            商品ID, 品目名, 在庫数, 最低在庫数
        FROM 商品
    ''').fetchall()
    conn.close()
    return render_template('index.html', products=products)

# 入庫画面（Aではまだ「表示だけ」の仮画面）
@app.route('/entry/<int:product_id>')
def entry(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT 商品ID, 品目名, 在庫数
        FROM 商品
        WHERE 商品ID = ?
    ''', (product_id,)).fetchone()
    conn.close()

    if product is None:
        return "商品が見つかりませんでした。", 404

    return render_template('entry.html', product=product)

from flask import request, redirect

@app.route('/entry/<int:product_id>', methods=['POST'])
def entry_post(product_id):
    quantity = int(request.form['quantity'])

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO 入出庫 (商品ID, 区分ID, 日時, ユーザーID, 数)
        VALUES (?, 1, datetime('now', 'localtime'), 1, ?)
    ''', (product_id, quantity))

    conn.execute('''
        UPDATE 商品
        SET 在庫数 = 在庫数 + ?
        WHERE 商品ID = ?
    ''', (quantity, product_id))

    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/exit/<int:product_id>')
def exit(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT 商品ID, 品目名, 在庫数
        FROM 商品
        WHERE 商品ID = ?
    ''', (product_id,)).fetchone()
    conn.close()

    if product is None:
        return "商品が見つかりませんでした。", 404

    return render_template('exit.html', product=product)

@app.route('/exit/<int:product_id>', methods=['POST'])
def exit_post(product_id):
    quantity = int(request.form['quantity'])

    conn = get_db_connection()

    # 現在の在庫数取得
    current_stock = conn.execute('''
        SELECT 在庫数
        FROM 商品
        WHERE 商品ID = ?
    ''', (product_id,)).fetchone()['在庫数']

    # 在庫不足チェック（★ここが重要！）
    if quantity > current_stock:
        conn.close()
        return render_template('error.html',message='出庫数が在庫数を超えています。')

    # 入出庫テーブルに記録（区分ID = 2 → 出庫）
    conn.execute('''
        INSERT INTO 入出庫 (商品ID, 区分ID, 日時, ユーザーID, 数)
        VALUES (?, 2, datetime('now', 'localtime'), 1, ?)
    ''', (product_id, quantity))

    # 商品テーブルの在庫を減算
    conn.execute('''
        UPDATE 商品
        SET 在庫数 = 在庫数 - ?
        WHERE 商品ID = ?
    ''', (quantity, product_id))

    conn.commit()
    conn.close()

    return redirect(url_for('index'))




if __name__ == '__main__':
    app.run(debug=True)

