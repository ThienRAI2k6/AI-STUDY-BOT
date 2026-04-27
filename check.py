import pandas as pd
import numpy as np

def generate_student_data(subject, n_rows=500):
    np.random.seed(42)
    
    # 1. Tạo dữ liệu ngẫu nhiên
    study_hour = np.random.randint(5, 60, n_rows) # Học từ 5 đến 60h
    absences = np.random.randint(0, 10, n_rows)   # Nghỉ từ 0 đến 10 buổi
    midterm = np.random.uniform(4.0, 9.5, n_rows) # Điểm giữa kỳ
    
    # 2. Thiết lập trọng số theo môn học (Logic AI)
    if subject == 'tienganh':
        h_weight, a_weight = 0.12, -0.15
    elif subject == 'toan':
        h_weight, a_weight = 0.08, -0.25
    else: # vatly
        h_weight, a_weight = 0.06, -0.35
        
    # 3. Tính toán điểm cuối kỳ (Final Score) kèm một chút nhiễu (noise) cho thực tế
    noise = np.random.normal(0, 0.3, n_rows)
    final_score = midterm + (study_hour * h_weight) + (absences * a_weight) + noise
    
    # Giới hạn điểm trong khoảng 0 - 10
    final_score = np.clip(final_score, 0, 10)
    
    return pd.DataFrame({
        'study_hours': study_hour,
        'absences': absences,
        'midterm': np.round(midterm, 1),
        'final_score': np.round(final_score, 1)
    })

# Tạo và lưu file
df_toan = generate_student_data('tienganh')
df_toan.to_csv('data_tienganh.csv', index=False)
print("Đã tạo xong file data_toan.csv với 500 dòng dữ liệu xịn!")