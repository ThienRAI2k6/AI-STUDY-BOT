import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import pickle
import os
def train_manual_linear_regression(X, y, lr=0.001, epochs=10000):
    # m: số lượng dòng, n: số lượng đặc trưng (3)
    m, n = X.shape
    # Khởi tạo w bằng 0 và b bằng 0
    w = np.zeros(n)
    b = 0
    
    # Chuyển data sang numpy array để tính toán ma trận
    X = X.values
    y = y.values

    for i in range(epochs):
        # 1. Dự đoán (Forward Pass)
        y_pred = np.dot(X, w) + b
        
        # 2. Tính Gradients (Đạo hàm của hàm MSE)
        dw = (1/m) * np.dot(X.T, (y_pred - y))
        db = (1/m) * np.sum(y_pred - y)
        
        # 3. Cập nhật trọng số (Gradient Descent)
        w = w - lr * dw
        b = b - lr * db
        
        # In tiến độ mỗi 2000 vòng
        if i % 2000 == 0:
            loss = np.mean((y_pred - y)**2)
            print(f"   Epoch {i}: Loss = {loss:.4f}")
            
    return w, b
# Danh sách các môn bạn muốn AI "học"
subjects = ["toan", "tienganh", "vatly"]

for sub in subjects:
    file_path = f"data_{sub}.csv"
    if os.path.exists(file_path):
        data = pd.read_csv(file_path, sep=",", encoding='utf-8-sig')
        X = data[["study_hours", "absences", "midterm"]]
        y = data["final_score"]

        weights, bias = train_manual_linear_regression(X, y)
        y_pred = np.dot(X.values, weights) + bias
        print(f"   📊 Độ chính xác (R2): {r2_score(y, y_pred):.2f}")
        print(f"   📊 Sai số (MSE): {mean_squared_error(y, y_pred):.2f}")

        # Lưu thành các file riêng: model_toan.pkl, model_tienganh.pkl...
        model_data = {"weights": weights, "bias": bias}
        with open(f"model_{sub}.pkl", "wb") as f:
            pickle.dump(model_data, f)
        print(f"   ✅ Đã lưu model_{sub}.pkl\n")
