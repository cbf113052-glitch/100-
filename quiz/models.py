from django.db import models
from django.contrib.auth.models import User # 🚀 核心：引入 Django 內建的使用者模型來記錄是哪位學生

# ==============================================================================
# 1. 題目資料表（加上 E 選項與防爆字數優化 🚀）
# ==============================================================================
class Question(models.Model):
    # 題目內容
    question_text = models.CharField(max_length=255, verbose_name="題目")
    
    # 選項 A、B、C、D、E（將長度擴充至 255 避免複雜選項爆掉）
    option_a = models.CharField(max_length=255, verbose_name="選項 A")
    option_b = models.CharField(max_length=255, verbose_name="選項 B")
    option_c = models.CharField(max_length=255, verbose_name="選項 C")
    option_d = models.CharField(max_length=255, verbose_name="選項 D")
    # ➕ 新增 E 選項，設定 blank=True 和 null=True 允許部分題目沒有 E 選項
    option_e = models.CharField(max_length=255, verbose_name="選項 E", blank=True, null=True)
    
    # 正確答案
    ANSWER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'), # ➕ 新增 E 選項到正確答案清單中
    ]
    # 因為多了 E，max_length 稍微放大到 2
    correct_answer = models.CharField(max_length=2, choices=ANSWER_CHOICES, verbose_name="正確答案")

    # 題目詳解
    explanation = models.TextField(blank=True, null=True, default="暫無詳解", verbose_name="題目詳解")

    # 🎯 難易度中文自訂：調整為你指定的「簡單、中等、困難」
    DIFFICULTY_CHOICES = [
        ('easy', '簡單'),
        ('medium', '中等'),
        ('hard', '困難'),
    ]
    difficulty = models.CharField(
        max_length=10, 
        choices=DIFFICULTY_CHOICES, 
        default='medium', 
        verbose_name="難易度"
    )

    def __str__(self):
        return f"[{self.get_difficulty_display()}] {self.question_text}"

    # 強制對齊你的 SQLite 資料表名稱
    class Meta:
        db_table = 'quiz_question'  


# ==============================================================================
# 2. ⚡ 核心新表：全新獨立的「間隔學習/錯題冷卻追蹤表」（完美保留核心邏輯！）
# ==============================================================================
class WrongQuestionTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="學生")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="錯題")
    
    # cooldown_count 代表還要經過幾題才能再次出現
    cooldown_count = models.IntegerField(default=0, verbose_name="剩餘冷卻題數")
    
    # 紀錄該生這題連續答錯幾次（用於連錯加成處罰）
    wrong_streak = models.IntegerField(default=1, verbose_name="連續答錯次數")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        db_table = 'quiz_wrong_tracker'
        unique_together = ('user', 'question') # 確保一個學生的一道題目只會有一筆追蹤紀錄

    def __str__(self):
        return f"{self.user.username} 的錯題：{self.question.id} (冷卻: {self.cooldown_count})"


# ==============================================================================
# 3. 全新獨立的「戰績紀錄資料表」
# ==============================================================================
class QuizResult(models.Model):
    # 關聯到目前的登入學生
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="學生")
    
    # 戰績數據
    score = models.IntegerField(verbose_name="得分")
    correct_count = models.IntegerField(verbose_name="答對題數")
    wrong_count = models.IntegerField(verbose_name="答錯題數")
    
    # 用來存放當次考試的所有題目、作答、詳解快照！
    detail_json = models.TextField(blank=True, null=True, verbose_name="詳細題目快照JSON")
    
    # 自動記錄交卷當下的時間
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="測試時間")

    class Meta:
        db_table = 'quiz_result'     # 強制設定 SQLite 中的資料表名稱為 quiz_result
        ordering = ['-created_at']   # 讓資料預設以時間由新到舊排序

    def __str__(self):
        return f"{self.user.username} - {self.score}分 ({self.created_at.strftime('%m/%d %H:%M')})"
    

# ==============================================================================
# 4. 歷次挑戰紀錄（保留你原本的設計）
# ==============================================================================
class QuizHistory(models.Model):
    STATUS_CHOICES = [
        ('PASS', 'PASS'),
        ('FAIL', 'FAIL'),
    ]

    # 1. 關聯使用者：誰做的測驗
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_histories')
    
    # 2. 測驗主題與範圍
    title = models.CharField(max_length=255, verbose_name="測驗範圍 / 標題")
    quiz_summary = models.CharField(max_length=255, verbose_name="題型統計（如：包含單選 6 題、多選 4 題）")
    
    # 3. 測驗結果與分數
    score = models.IntegerField(verbose_name="原始得分")
    total_possible_score = models.IntegerField(default=1000, verbose_name="總分（例如圖片中的 1000 分滿分）")
    score_percentage = models.IntegerField(verbose_name="答對率（百分比，如 85）")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='FAIL', verbose_name="結果狀態")
    
    # 4. 測驗時間
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="測驗日期")

    class Meta:
        ordering = ['-created_at'] # 預設依時間倒序排列
        verbose_name = "歷次挑戰紀錄"

    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.score_percentage}%"