from flask import Flask, render_template, url_for, request, redirect
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps



app = Flask(__name__)
app.secret_key = 'abc123xyz-secret!'

# 🔹DBへのパスを絶対パスで固定（Render対策）
db_path = os.path.join(os.path.dirname(__file__), 'cafe_management.db')

def get_db_connection():
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# 🔹初期DB作成（Render初回用）
def init_db():
    conn = get_db_connection()

    # 商品テーブル作成
    conn.execute('''
        CREATE TABLE IF NOT EXISTS 商品 (
            商品ID INTEGER PRIMARY KEY AUTOINCREMENT,
            品目名 TEXT NOT NULL,
            在庫数 INTEGER NOT NULL,
            最低在庫数 INTEGER NOT NULL
        )
    ''')

    # ユーザーテーブル作成
    conn.execute('''
    CREATE TABLE IF NOT EXISTS ユーザー (
        ユーザーID INTEGER PRIMARY KEY AUTOINCREMENT,
        名前 TEXT NOT NULL,
        パスワード TEXT NOT NULL
    )
''')


    # 入出庫テーブル作成
    conn.execute('''
        CREATE TABLE IF NOT EXISTS 入出庫 (
            入出庫ID INTEGER PRIMARY KEY AUTOINCREMENT,
            商品ID INTEGER NOT NULL,
            区分ID INTEGER NOT NULL,
            日時 TEXT NOT NULL,
            ユーザーID INTEGER NOT NULL,
            数 INTEGER NOT NULL
        )
    ''')
       # 初期ユーザー登録（重複登録防止）
    cur = conn.execute('SELECT COUNT(*) as count FROM ユーザー')
    if cur.fetchone()['count'] == 0:
        users = [
            ("Aさん", "passwordA"),
            ("Bさん", "passwordB"),
            ("Cさん", "passwordC"),
            ("Dさん", "passwordD"),
            ("Eさん", "passwordE"),
            ("Fさん", "passwordF")
        ]
        for name, pwd in users:
            hashed = generate_password_hash(pwd)
            conn.execute(
                "INSERT INTO ユーザー (名前, パスワード) VALUES (?, ?)",
                (name, hashed)
            )




    conn.commit()
    conn.close()

# ⭐最初に1回だけDBを用意
init_db()


# ★★---ここへログイン機能追加！---★★

from flask import request, redirect, session, flash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM ユーザー WHERE 名前 = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['パスワード'], password):
            session['user_id'] = user['ユーザーID']
            flash('ログイン成功！')
            return redirect(url_for('index'))
        else:
            flash('ユーザー名またはパスワードが違います')
        return render_template('login.html', username=username)


    return render_template('login.html')

# ログイン必須デコレーター
def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view





# 🔹商品一覧
@app.route('/')
@login_required
def index():

    conn = get_db_connection()

    # ★ログイン中のユーザー名を取得！
    user = conn.execute(
        'SELECT 名前 FROM ユーザー WHERE ユーザーID = ?',
        (session['user_id'],)
    ).fetchone()

    products = conn.execute('''
        SELECT 商品ID, 品目名, 在庫数, 最低在庫数
        FROM 商品
    ''').fetchall()

    conn.close()
     # ★テンプレートに user を渡す！
    return render_template('index.html', products=products, user=user['名前'])

# 🔹入庫画面
@app.route('/entry/<int:product_id>')
@login_required
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


@app.route('/entry/<int:product_id>', methods=['POST'])
@login_required
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


# 🔹出庫画面
@app.route('/exit/<int:product_id>')
@login_required
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
@login_required
def exit_post(product_id):
    quantity = int(request.form['quantity'])

    conn = get_db_connection()

    current_stock = conn.execute('''
        SELECT 在庫数
        FROM 商品
        WHERE 商品ID = ?
    ''', (product_id,)).fetchone()['在庫数']

    if quantity > current_stock:
        conn.close()
        return render_template('error.html', message='出庫数が在庫数を超えています。')

    conn.execute('''
        INSERT INTO 入出庫 (商品ID, 区分ID, 日時, ユーザーID, 数)
        VALUES (?, 2, datetime('now', 'localtime'), 1, ?)
    ''', (product_id, quantity))

    conn.execute('''
        UPDATE 商品
        SET 在庫数 = 在庫数 - ?
        WHERE 商品ID = ?
    ''', (quantity, product_id))

    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

