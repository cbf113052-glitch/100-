import random
import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import models 
from django.db.models import Count, Q, Max 
from django.db.models.functions import TruncDate 
from django.utils import timezone

from .models import Question, QuizResult, WrongQuestionTracker

# ==============================================================================
# 1. 學生註冊
# ==============================================================================
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username or not password or not password2:
            messages.error(request, '所有欄位皆為必填！')
            return render(request, 'registration/register.html')

        if password != password2:
            messages.error(request, '兩次輸入的密碼不一致，請重新確認！')
            return render(request, 'registration/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '此使用者名稱已被註冊，請換一個！')
            return render(request, 'registration/register.html')
        
        User.objects.create_user(username=username, password=password)
        messages.success(request, f'學生帳號 【{username}】 建立成功！請在此登入。')
        return redirect('login')
        
    return render(request, 'registration/register.html')


# ==============================================================================
# 2. 控制台主頁
# ==============================================================================
@login_required
def dashboard(request):
    user_results = QuizResult.objects.filter(user=request.user).order_by('-id')
    last_result = user_results.first()
    
    total_wrong = WrongQuestionTracker.objects.filter(user=request.user).count()
    last_score = last_result.score if last_result else None
    
    recent_histories = user_results[:3]
    
    mock_titles = [
        "Max-Heap 插入操作與調整",
        "Priority Queue 實務應用與核心",
        "Heapify 排序原理與時間複雜度",
        "二元樹節點走訪與刪除",
        "佇列 (Queue) 先進先出應用"
    ]

    for index, r in enumerate(recent_histories):
        r.score_percentage = r.score  
        r.status = 'PASS' if r.score >= 60 else 'FAIL'
        r.title = mock_titles[index % len(mock_titles)]

    chart_results = QuizResult.objects.filter(user=request.user).order_by('-id')[:5]
    chart_results = list(reversed(chart_results))
    
    scores = [res.score for res in chart_results]
    labels = [res.created_at.strftime('%m/%d %H:%M') for res in chart_results]
    
    while len(scores) < 5:
        scores.insert(0, 0)
        labels.insert(0, "暫無紀錄")

    leaderboard_data = (
        QuizResult.objects.values('user__username')
        .annotate(max_score=Max('score'))
        .order_by('-max_score')[:5]
    )

    today_date = timezone.now().date()
    start_date = today_date - timedelta(days=83)  
    
    daily_activities = (
        QuizResult.objects.filter(user=request.user, created_at__date__gte=start_date)
        .annotate(date_only=TruncDate('created_at'))
        .values('date_only')
        .annotate(count=Count('id'))
    )
    
    activity_mapping = {item['date_only']: item['count'] for item in daily_activities}
    
    activity_list = []
    for i in range(84):
        current_date = start_date + timedelta(days=i)
        count = activity_mapping.get(current_date, 0)
        
        if count == 0: level = 0
        elif count == 1: level = 1
        elif count <= 3: level = 2
        elif count <= 5: level = 3
        else: level = 4
            
        activity_list.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': count,
            'level': level
        })

    return render(request, 'quiz/dashboard.html', {
        'total_wrong': total_wrong,
        'last_score': last_score,
        'recent_histories': recent_histories,
        'scores_json': json.dumps(scores),    
        'labels_json': json.dumps(labels),    
        'leaderboard': leaderboard_data,      
        'activity_list': activity_list,       
    })


# ==============================================================================
# 2.5 準備入口
# ==============================================================================
@login_required
def quiz_ready_view(request):
    return render(request, 'quiz_ready.html')


# ==============================================================================
# 2.8 錯題統計與複習頁面
# ==============================================================================
@login_required
def wrong_questions_summary_view(request):
    trackers = WrongQuestionTracker.objects.filter(user=request.user).select_related('question')
    all_results = QuizResult.objects.filter(user=request.user).order_by('id')
    
    global_answer_text_map = {}
    global_answer_code_map = {}
    global_explanation_map = {}
    global_correct_text_map = {}
    
    for res in all_results:
        if res.detail_json:
            try:
                details = json.loads(res.detail_json)
                for item in details:
                    qid = int(item['id'])
                    u_text = item.get('user_answer_text', '未作答')
                    
                    u_code = "未作答"
                    if u_text != "未作答":
                        if u_text == item.get('option_a'): u_code = "(A)"
                        elif u_text == item.get('option_b'): u_code = "(B)"
                        elif u_text == item.get('option_c'): u_code = "(C)"
                        elif u_text == item.get('option_d'): u_code = "(D)"
                        elif u_text == item.get('option_e'): u_code = "(E)"
                    
                    global_answer_text_map[qid] = u_text
                    global_answer_code_map[qid] = u_code
                    
                    if item.get('explanation'):
                        global_explanation_map[qid] = item['explanation']

                    # 只記錄正確答案的「文字內容」，不記錄洗牌代號
                    if item.get('correct_answer_text'):
                        global_correct_text_map[qid] = item['correct_answer_text']

            except Exception:
                pass

    heap_adjust_count = 0
    pq_count = 0
    complexity_count = 0
    
    for t in trackers:
        qid = t.question.id
        q = t.question
        
        history_text = global_answer_text_map.get(qid, "未作答")
        history_code = global_answer_code_map.get(qid, "")
        
        if history_code and history_code != "未作答":
            display_user_answer = f"{history_code} {history_text}"
        else:
            display_user_answer = history_text

        # ✅ 修復核心：
        # 代號永遠從原始 DB 欄位（未洗牌）取得，
        # 文字優先用 detail_json 的 correct_answer_text，找不到才 fallback DB。
        orig_ans = q.correct_answer.replace('(', '').replace(')', '').strip()

        db_correct_text = ""
        if orig_ans == 'A': db_correct_text = q.option_a
        elif orig_ans == 'B': db_correct_text = q.option_b
        elif orig_ans == 'C': db_correct_text = q.option_c
        elif orig_ans == 'D': db_correct_text = q.option_d
        elif orig_ans == 'E': db_correct_text = getattr(q, 'option_e', '') or ''

        real_correct_text = global_correct_text_map.get(qid) or db_correct_text or "無答案紀錄"

        # 代號用原始未洗牌代號，文字用真實文字，兩者座標系一致永遠對齊
        perfect_correct_display = f"({orig_ans}) {real_correct_text}"

        t.user_answer = display_user_answer
        t.user_wrong_answer = display_user_answer
        t.user_answer_text = display_user_answer
        t.question.user_answer = display_user_answer
        t.question.user_wrong_answer = display_user_answer
        t.question.user_answer_text = display_user_answer
        
        t.correct_answer = perfect_correct_display
        t.question.correct_answer = perfect_correct_display
        
        correct_explanation = global_explanation_map.get(qid, q.explanation)
        if not correct_explanation or "根據二元堆積 (Binary Heap) 與二元搜尋樹" in correct_explanation:
            correct_explanation = q.explanation

        t.explanation = correct_explanation
        t.question.explanation = correct_explanation
        
        text = q.question_text
        if any(k in text for k in ["調整", "插入", "刪除", "根"]):
            heap_adjust_count += 1
        elif "優先" in text or "Priority" in text:
            pq_count += 1
        elif "複雜度" in text or "O(" in text:
            complexity_count += 1
            
    max_count = max(heap_adjust_count, pq_count, complexity_count)
    if trackers.count() == 0:
        disaster_zone = "暫無"
    elif max_count == heap_adjust_count:
        disaster_zone = "Heap 調整"
    elif max_count == pq_count:
        disaster_zone = "Priority Queue"
    else:
        disaster_zone = "時間複雜度"

    return render(request, 'wrong_questions.html', {
        'trackers': trackers,
        'disaster_zone': disaster_zone
    })


# ==============================================================================
# 2.9 單題重練
# ==============================================================================
@login_required
def retry_single_question_view(request, question_id):
    tracker = get_object_or_404(WrongQuestionTracker, user=request.user, question_id=question_id)
    request.session['current_quiz_ids'] = [tracker.question.id]
    return redirect('/quiz/?mode=review')


# ==============================================================================
# 3. 學生登出
# ==============================================================================
def logout_view(request):
    auth_logout(request)
    messages.success(request, '您已成功登出系統。')
    return redirect('login')


# ==============================================================================
# 4. 線上測驗視圖
# ==============================================================================
@login_required
def quiz_view(request):
    if request.method == 'POST':
        session_quiz_ids = request.session.get('current_quiz_ids', [])
        questions_dict = {q.id: q for q in Question.objects.filter(id__in=session_quiz_ids)}
        questions = [questions_dict[qid] for qid in session_quiz_ids if qid in questions_dict]
        
        score_count = 0
        total = len(questions)
        results = []
        db_details = []

        # ✅ 從 POST 讀取 mode，讓結果頁知道來源
        mode = request.POST.get('mode', 'normal')
        
        # 降溫冷卻機制
        WrongQuestionTracker.objects.filter(user=request.user).update(
            cooldown_count=models.F('cooldown_count') - 1
        )
        
        session_shuffled_options = request.session.get('shuffled_options_history', {})
            
        for q in questions:
            user_choice_code = request.POST.get(f'question_{q.id}', '').strip()
            str_qid = str(q.id)
            
            # A. 從原始 DB 取得真正正確答案文字
            orig_correct_code = q.correct_answer.replace('(', '').replace(')', '').strip()
            real_correct_text = ""
            if orig_correct_code == 'A': real_correct_text = q.option_a
            elif orig_correct_code == 'B': real_correct_text = q.option_b
            elif orig_correct_code == 'C': real_correct_text = q.option_c
            elif orig_correct_code == 'D': real_correct_text = q.option_d
            elif orig_correct_code == 'E' and hasattr(q, 'option_e'): real_correct_text = q.option_e

            # B. 取得洗牌後的實際選項順序
            default_options = [q.option_a, q.option_b, q.option_c, q.option_d]
            if getattr(q, 'option_e', None):
                default_options.append(q.option_e)
            current_options = session_shuffled_options.get(str_qid, default_options)
            
            # C. 找出學生選中的實際文字
            user_answer_text = "未作答"
            if user_choice_code == 'A' and len(current_options) > 0: user_answer_text = current_options[0]
            elif user_choice_code == 'B' and len(current_options) > 1: user_answer_text = current_options[1]
            elif user_choice_code == 'C' and len(current_options) > 2: user_answer_text = current_options[2]
            elif user_choice_code == 'D' and len(current_options) > 3: user_answer_text = current_options[3]
            elif user_choice_code == 'E' and len(current_options) > 4: user_answer_text = current_options[4]

            # D. 用字串比對判斷對錯
            is_correct = (user_answer_text.strip() == real_correct_text.strip() and user_choice_code != "")
                
            if is_correct:
                score_count += 1
                WrongQuestionTracker.objects.filter(user=request.user, question=q).delete()
            else:
                cooldown_map = {'easy': 5, 'medium': 3, 'hard': 1}
                assigned_cooldown = cooldown_map.get(q.difficulty, 3)
                
                tracker, created = WrongQuestionTracker.objects.get_or_create(
                    user=request.user, question=q
                )
                if not created:
                    tracker.wrong_streak += 1 
                tracker.cooldown_count = assigned_cooldown
                tracker.save()
            
            # E. 計算洗牌後正確答案的新代號
            shuffled_correct_code = "A"
            for index, opt_text in enumerate(current_options):
                if opt_text.strip() == real_correct_text.strip():
                    shuffled_correct_code = ['A', 'B', 'C', 'D', 'E'][index]
                    break
            
            # F. 同步物件狀態供前端渲染
            q.correct_answer = shuffled_correct_code
            q.correct_answer_text = real_correct_text

            results.append({
                'question': q,
                'user_answer': user_answer_text,
                'user_choice_code': user_choice_code, 
                'is_correct': is_correct,
                'correct_answer_text': real_correct_text,
                'correct_answer_code': shuffled_correct_code,
                'option_a': current_options[0] if len(current_options) > 0 else "",
                'option_b': current_options[1] if len(current_options) > 1 else "",
                'option_c': current_options[2] if len(current_options) > 2 else "",
                'option_d': current_options[3] if len(current_options) > 3 else "",
                'option_e': current_options[4] if len(current_options) > 4 else "None",
            })
            
            db_details.append({
                'id': q.id,
                'question_text': q.question_text,
                'option_a': current_options[0] if len(current_options) > 0 else "",
                'option_b': current_options[1] if len(current_options) > 1 else "",
                'option_c': current_options[2] if len(current_options) > 2 else "",
                'option_d': current_options[3] if len(current_options) > 3 else "",
                'option_e': current_options[4] if len(current_options) > 4 else "None", 
                'shuffled_options_list': current_options,
                'correct_answer_text': real_correct_text,
                'correct_answer_code': shuffled_correct_code,
                'correct_answer': shuffled_correct_code,
                'user_answer_text': user_answer_text,
                'user_choice_code': user_choice_code,
                'is_correct': is_correct,
                'explanation': q.explanation if q.explanation else "無詳細解析提示。"
            })
        
        final_score = int((score_count / total) * 100) if total > 0 else 0
        wrong_count = total - score_count
        
        QuizResult.objects.create(
            user=request.user,
            score=final_score,
            correct_count=score_count,
            wrong_count=wrong_count,
            detail_json=json.dumps(db_details, ensure_ascii=False)
        )
        
        return render(request, 'quiz.html', {
            'score': final_score,
            'correct_count': score_count,
            'total_count': total,
            'results': results,
            'is_submitted': True,
            'mode': mode,   # ✅ 傳給 template，讓按鈕知道要回哪裡
        })

    # GET 請求區塊
    mode = request.GET.get('mode', 'normal')
    quiz_size = int(request.GET.get('num', 5))
    
    if mode == 'review':
        trackers = WrongQuestionTracker.objects.filter(user=request.user).select_related('question')
        questions = [t.question for t in trackers]
    else:
        questions = list(Question.objects.all())
        if len(questions) > quiz_size:
            questions = random.sample(questions, quiz_size)
            
    request.session['current_quiz_ids'] = [q.id for q in questions]
    
    shuffled_options_history = {}
    for q in questions:
        opts = [q.option_a, q.option_b, q.option_c, q.option_d]
        if getattr(q, 'option_e', None):
            opts.append(q.option_e)
            
        random.shuffle(opts)
        shuffled_options_history[str(q.id)] = opts
        q.shuffled_options_list = opts

    request.session['shuffled_options_history'] = shuffled_options_history

    actual_size = len(questions)
    if mode == 'review':
        quiz_duration_minutes = max(actual_size * 2, 5)
    else:
        if actual_size == 5:
            quiz_duration_minutes = 10
        elif actual_size == 10:
            quiz_duration_minutes = 20
        else:
            quiz_duration_minutes = actual_size * 2

    return render(request, 'quiz.html', {
        'questions': questions,
        'quiz_size': actual_size,
        'quiz_duration': quiz_duration_minutes,
        'is_submitted': False,
        'mode': mode,   # ✅ 傳給 template，讓 hidden input 帶入 POST
    })


# ==============================================================================
# 5. 題庫總覽
# ==============================================================================
@login_required
def bank_view(request):
    if not Question.objects.exists():
        raw_quiz_data = [
            ("簡單", "下列有關「堆積」的敘述，何者正確？", "堆積是一棵完整二元樹", "最大堆積的元素是放在樹的最後一個節點", "最小堆積中，每個節點的父節點一定比該節點大", "堆建立用鏈結串列實現", "堆積是一棵完整二元樹", "", 
             "二元堆積（Binary Heap）在本質上是一棵完全二元樹（Complete Binary Tree），並且滿足堆積屬性：最大堆積中父節點大於或等於子節點；最小堆積中父節點小於或等於子節點。"),
            
            ("簡單", "下列的資料結構，何者適合用來實現「堆積」？", "陣列", "鏈結串列", "堆疊", "佇列", "陣列", "", 
             "因為堆積是一棵完全二元樹（Complete Binary Tree），節點沒有緊湊空缺，因此使用連續記憶體的「陣列（Array）」來實現最為高效，且能透過索引值輕易計算出父子節點的位置。"),
            
            ("簡單", "下列的資料結構，何者與「堆積」的結構最相似？", "鏈結串列", "堆疊", "佇列", "優先佇列", "優先佇列", "", 
             "堆積（Heap）是實作優先佇列（Priority Queue）最普遍且最高效的底層資料結構，兩者在邏輯與應用的核心機制上最為接近。"),
            
            ("簡單", "下列關於優先佇列（Priority Queue）的敘述何者正確？", "FIFO", "LIFO", "取出優先權最高者", "只能用陣列", "取出優先權最高者", "", 
             "優先佇列（Priority Queue）不再遵循傳統佇列的先進先出（FIFO）原則，而是每次從中取出「優先權最高（例如數值最大或最小）」的元素。"),
            
            ("簡單", "一個二元堆積（Binary Heap）在結構上必須是一個？", "完整二元樹", "滿二元樹", "二元搜尋樹", "鏈結串列", "完整二元樹", "", 
             "二元堆積在結構層面上必須嚴格滿足「完全二元樹（Complete Binary Tree，部分中文教材譯為完整二元樹）」的定義，除最後一層外其餘層皆滿，且節點由左至右依序填入。"),
            
            ("簡單", "堆積必須嚴格符合哪種樹的型態？", "完滿二元樹", "完全二元樹", "歪斜二元樹", "二元搜尋樹", "完全二元樹", "", 
             "堆積為了確保結構平衡、避免退化，並利用陣列緊湊儲存，必須嚴格符合「完全二元樹（Complete Binary Tree）」的型態。"),
            
            ("簡單", "在「最小堆積」中，根節點必定是？", "最大值", "最小值", "中位數", "隨機值", "最小值", "", 
             "根據最小堆積（Min-Heap）的定義，任何一個父節點的值都必須小於或等於其子節點的值。層層推導後，整個結構的樹根（Root）必定含有整個堆積中的最小值。"),
            
            ("簡單", "依序將數值 5, 3, 8, 2, 7 插入一個初始為空的「最小堆積（Min-Heap）」中。插入完成後，該堆積的陣列表示（假設索引由 1 開始）為何？","2, 3, 5, 7, 8","2, 3, 8, 5, 7", "2, 5, 8, 3, 7","8, 7, 5, 3, 2", "2, 3, 5, 7, 8", "", 
             "依序模擬插入：[5] -> [3, 5] -> [3, 5, 8] -> 插入2變 [2, 3, 8, 5] -> 插入7變 [2, 3, 8, 5, 7]。最終進行完整 Min-Heapify 調整後的陣列呈現結果為 2, 3, 5, 7, 8。"),
            
            ("中等", "最大堆積的「回傳最大值」操作，時間複雜度為何？", "O(1)", "O(log n)", "O(n)", "O(n log n)", "O(1)", "", 
             "在最大堆積（Max-Heap）中，最大值必然儲存在根節點（陣列的第一個位置索引 1），因此只需要花費 O(1) 的常數時間即可直接讀取並回傳。"),
            
            ("中等", "最大堆積的「插入」操作，時間複雜度為何？", "O(1)", "O(log n)", "O(n)", "O(n log n)", "O(log n)", "", 
             "插入新元素時會先放入樹的最後一個葉子節點，接著進行向上調整（Bubble Up / Percolate Up）。由於完全二元樹的高度為 log n，最壞情況下只需調整至根節點，因此時間複雜度為 O(log n)。"),
            
            ("中等", "最大堆積的「移除最大值」操作，時間複雜度為何？", "O(1)", "O(log n)", "O(n)", "O(n log n)", "O(log n)", "", 
             "移除最大值（刪除根節點）需要將樹的最後一個葉子節點移至根節點，接著執行向下調整（Max-Heapify）。調整路徑等同於樹的高度，因此時間複雜度為 O(log n)。"),
            
            ("中等", "「堆積」中，若節點索引為 i (1-based)，父節點索引為何？", "i / 2", "i * 2", "i - 1", "i + 1", "i / 2", "", 
             "在一維陣列實現的二元堆積（1-based 索引）中，任何一個位於索引 i 的節點，其父節點的索引位置必然是其除以 2 並向下取整數（即其商數值值為 i / 2）。"),
            
            ("中等", "「堆積」中，若節點索引為 i，左子節點索引為何？", "2i", "2i - 1", "2i + 1", "2i + 2", "2i", "", 
             "在一維陣列儲存的二元堆積（假設索引從 1 開始計數）中，對於任意非葉子節點 i，它的左子節點必定精準存放在索引值為 2i 的位置。"),
            
            ("中等", "作業系統管理執行緒優先權最適合用？", "堆疊", "佇列", "優先佇列", "雜湊表", "優先佇列", "", 
             "作業系統排程多個執行緒時，需要動態根據其重要性或優先級（Priority）高低來決定誰先執行，而非單純遵循先來後到的順序，因此最適合採用「優先佇列（Priority Queue）」結構。"),
            
            ("中等", "建立最大堆積 (Build-Max-Heap) 的時間複雜度？", "O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n)", "", 
             "利用 Bottom-Up 自底向上的方式將一個含有 n 個元素的無序陣列建立成一個最大堆積，經過數學級數緊縮收斂推導，其總時間複雜度上限為優異的 O(n)，而非單純看作 n 次插入的 O(n log n)。"),
            
            ("困難", "考慮「堆積排序」，輸入 4, 1, 5, 3, 2, 6，何者不是建立最大堆積的中間過程？", "4, 1, 6, 3, 2, 5", "4, 3, 6, 1, 2, 5", "4, 2, 6, 1, 3, 5", "6, 3, 5, 1, 2, 4", "4, 2, 6, 1, 3, 5", "", 
             "在 Build-Max-Heap（建立最大堆積）過程中，必須從最後一個非葉部節點開始逐步做 heapify 向下調整。選項中的 (C) 4, 2, 6, 1, 3, 5，雖然看起來某些子樹符合，但它不可能由原始序列經過合法的交換順序得到。"),
            
            ("困難", "依序插入 50, 30, 70, 20, 40, 60, 80 到二元搜尋樹，若刪除節點 50，新的根節點可能為？","30", "40", "60", "70", "60", "", 
             "在二元搜尋樹（BST）中刪除根節點時，為了維持搜尋樹特性，必須找「左子樹的最大值（前驅節點，此處為40）」或「右子樹的最小值（後繼節點，此處為60）」來取代根節點的位置。"),
            
            ("困難", "在一個「二元堆積（Binary Heap）」的「最小堆積（Min-Heap）」中，依序插入數值 10, 4, 15, 20, 0, 8。請問插入完成後，該堆積的陣列表示（假設陣列索引由 1 開始）為何？", "0, 4, 8, 20, 10, 15","0, 4, 10, 15, 20, 8 ", "0, 4, 10, 20, 15, 8", "0, 8, 4, 20, 10, 15", "0, 4, 8, 20, 10, 15", "", 
             "按順序模擬插入：[10] -> [4, 10] -> [4, 10, 15] -> [4, 10, 15, 20] -> 插入 0 後冒泡調整變為 [0, 4, 15, 20, 10] -> 最後插入 8 調整得到 [0, 4, 8, 20, 10, 15]。"),
        ]

        diff_map = {"簡單": "easy", "中等": "medium", "困難": "hard"}

        for item in raw_quiz_data:
            raw_diff, text, a, b, c, d, ans_text, e, each_explanation = item
            correct_code = "A"
            if ans_text.strip() == a.strip(): correct_code = "A"
            elif ans_text.strip() == b.strip(): correct_code = "B"
            elif ans_text.strip() == c.strip(): correct_code = "C"
            elif ans_text.strip() == d.strip(): correct_code = "D"

            Question.objects.create(
                difficulty=diff_map.get(raw_diff.strip(), "medium"),
                question_text=text.strip(),
                option_a=a.strip(), option_b=b.strip(), option_c=c.strip(), option_d=d.strip(),
                option_e=e.strip() if e else "",
                correct_answer=correct_code,
                explanation=each_explanation  
            )
            
    questions = Question.objects.all()
    user_wrongs = WrongQuestionTracker.objects.filter(user=request.user)
    wrong_map = {task.question_id: task for task in user_wrongs}
    
    for q in questions:
        if q.id in wrong_map:
            q.is_wrong_pool = True
            q.cooldown = wrong_map[q.id].cooldown_count
            q.streak = wrong_map[q.id].wrong_streak
        else:
            q.is_wrong_pool = False
            q.cooldown = None
            q.streak = 0
            
    return render(request, 'bank.html', {'questions': questions})


# ==============================================================================
# 5.5 歷次測驗歷史紀錄清單頁面
# ==============================================================================
@login_required
def quiz_history_view(request):
    db_results = QuizResult.objects.filter(user=request.user).order_by('-id')
    
    if not db_results.exists():
        db_results = QuizResult.objects.all().order_by('-id')
        
    total_count = db_results.count()
    mock_titles = [
        "堆積、優先佇列關聯綜合挑戰",
    ]
    
    for index, r in enumerate(db_results):
        r.score_percentage = r.score
        r.status = 'PASS' if r.score >= 60 else 'FAIL'
        r.title = mock_titles[index % len(mock_titles)]
        r.quiz_summary = f"包含答對 {r.correct_count} 題、答錯 {r.wrong_count} 題"
        
    return render(request, 'quiz/history.html', {
        'history_list': db_results,  
        'total_count': total_count
    })


# ==============================================================================
# 6. 歷史單次測驗詳細解析頁面
# ==============================================================================
@login_required
def quiz_detail_view(request, history_id):
    try:
        result = QuizResult.objects.get(id=history_id, user=request.user)
    except QuizResult.DoesNotExist:
        return redirect('quiz_history')
    
    if result.score >= 60:
        feedback = "太棒了！你對二元堆積（Binary Heap）、堆積調整（Heapify）以及優先佇列的觀念已掌握得相當紮實。"
        status_color = "text-emerald-400"
    else:
        feedback = "檢測到觀念混淆！建議重新溫習二元堆積在陣列中的父子節點索引計算公式（i/2 與 2i），以及最大、最小堆積的插入與刪除調整流程。"
        status_color = "text-rose-400"

    questions_data = []
    if hasattr(result, 'detail_json') and result.detail_json:
        try:
            raw_data = json.loads(result.detail_json)
            for item in raw_data:
                if 'correct_answer_code' in item:
                    item['correct_answer'] = item['correct_answer_code']
                questions_data.append(item)
        except json.JSONDecodeError:
            questions_data = []

    result.score_percentage = result.score

    return render(request, 'quiz/quiz_detail.html', {
        'result': result, 
        'feedback': feedback, 
        'status_color': status_color, 
        'questions': questions_data
    })