import flet as ft
import sqlite3
import time
import os

DB_NAME = "vocab_app_mobile.db"

# 数据库初始化逻辑与上一版完全一致
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            phonetic TEXT,
            translation TEXT NOT NULL,
            example_sentence TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_learning_progress (
            word_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'new',
            step_index INTEGER DEFAULT 0,
            next_review_time INTEGER,
            review_count INTEGER DEFAULT 0,
            FOREIGN KEY(word_id) REFERENCES words(id)
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM words")
    if cursor.fetchone()[0] == 0:
        dummy_words = [
            ("abandon", "[əˈbændən]", "v. 放弃，抛弃", "He abandoned his plan."),
            ("benefit", "[ˈbenɪfɪt]", "n. 利益，好处", "The new policy is of great benefit to us."),
            ("candidate", "[ˈkændɪdət]", "n. 候选人", "She is the best candidate for the job.")
        ]
        cursor.executemany("INSERT INTO words (word, phonetic, translation, example_sentence) VALUES (?, ?, ?, ?)", dummy_words)
        
        cursor.execute("SELECT id FROM words")
        for w_id in cursor.fetchall():
            cursor.execute("INSERT INTO user_learning_progress (word_id, next_review_time) VALUES (?, ?)", (w_id[0], int(time.time())))
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "艾宾浩斯单词本"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 800

    init_db()
    current_word = {}

    # --- UI 组件定义 ---
    word_text = ft.Text(size=40, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    phonetic_text = ft.Text(size=20, color=ft.colors.GREY_500, visible=False)
    translation_text = ft.Text(size=24, visible=False)
    example_text = ft.Text(size=16, color=ft.colors.BLUE_GREY, italic=True, visible=False, text_align=ft.TextAlign.CENTER)
    
    status_text = ft.Text(size=14, color=ft.colors.GREY_400)

    # 翻转卡片按钮
    show_answer_btn = ft.ElevatedButton("点击查看释义", on_click=lambda e: show_answer(), width=250, height=50)

    # 艾宾浩斯反馈逻辑
    def handle_feedback(feedback_type):
        if not current_word: return
        intervals = [5*60, 30*60, 12*3600, 24*3600, 2*86400, 4*86400, 7*86400, 15*86400]
        step = current_word['step']
        now = int(time.time())
        
        if feedback_type == "forgot":
            new_step, next_time = 0, now + intervals[0]
        elif feedback_type == "hard":
            new_step = step
            next_time = now + int(intervals[step] * 0.5) if step < len(intervals) else now + 86400
        elif feedback_type == "good":
            new_step = step + 1
            next_time = now + intervals[new_step] if new_step < len(intervals) else now + 30*86400
        else: # easy
            new_step = step + 2
            next_time = now + intervals[new_step] if new_step < len(intervals) else now + 30*86400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_learning_progress 
            SET step_index = ?, next_review_time = ?, status = 'learning', review_count = review_count + 1
            WHERE word_id = ?
        ''', (new_step, next_time, current_word['id']))
        conn.commit()
        conn.close()
        load_next_word()

    # 底部反馈按钮区 (初始隐藏)
    feedback_row = ft.Row(
        controls=[
            ft.ElevatedButton("忘记", bgcolor=ft.colors.RED_400, color=ft.colors.WHITE, on_click=lambda e: handle_feedback("forgot"), expand=1),
            ft.ElevatedButton("困难", bgcolor=ft.colors.ORANGE_400, color=ft.colors.WHITE, on_click=lambda e: handle_feedback("hard"), expand=1),
            ft.ElevatedButton("认识", bgcolor=ft.colors.GREEN_400, color=ft.colors.WHITE, on_click=lambda e: handle_feedback("good"), expand=1),
            ft.ElevatedButton("简单", bgcolor=ft.colors.BLUE_400, color=ft.colors.WHITE, on_click=lambda e: handle_feedback("easy"), expand=1),
        ],
        visible=False,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    def show_answer():
        phonetic_text.visible = True
        translation_text.visible = True
        example_text.visible = True
        show_answer_btn.visible = False
        feedback_row.visible = True
        page.update()

    def load_next_word():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        now = int(time.time())
        
        # 更新剩余数量
        cursor.execute("SELECT COUNT(*) FROM user_learning_progress WHERE next_review_time <= ?", (now,))
        left_count = cursor.fetchone()[0]
        status_text.value = f"今日待复习: {left_count} 个"

        cursor.execute('''
            SELECT w.id, w.word, w.phonetic, w.translation, w.example_sentence, p.step_index 
            FROM words w 
            JOIN user_learning_progress p ON w.id = p.word_id 
            WHERE p.next_review_time <= ? 
            ORDER BY p.next_review_time ASC LIMIT 1
        ''', (now,))
        row = cursor.fetchone()
        conn.close()

        if row:
            current_word['id'] = row[0]
            current_word['step'] = row[5]
            word_text.value = row[1]
            phonetic_text.value = row[2]
            translation_text.value = row[3]
            example_text.value = row[4]
            
            # 重置界面状态为正面
            phonetic_text.visible = False
            translation_text.visible = False
            example_text.visible = False
            show_answer_btn.visible = True
            feedback_row.visible = False
        else:
            word_text.value = "🎉 任务完成！"
            phonetic_text.visible = False
            translation_text.visible = False
            example_text.visible = False
            show_answer_btn.visible = False
            feedback_row.visible = False

        page.update()

    # 拼装页面
    page.add(
        status_text,
        ft.Container(height=50), # 占位
        word_text,
        phonetic_text,
        ft.Container(height=20),
        translation_text,
        ft.Container(height=10),
        example_text,
        ft.Container(height=80),
        show_answer_btn,
        feedback_row
    )

    load_next_word()

ft.app(target=main)
