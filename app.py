from flask import Flask, render_template, request, redirect, url_for, session , flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from data import ROADMAPS
from flask import jsonify 
from dotenv import load_dotenv
from groq import Groq
import pickle
import datetime
import os
import google.generativeai as genai 
load_dotenv()
app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_ai_response(user_input):
    try:
        # Sử dụng model Llama 3.3 hoặc Llama 4 Scout tùy bạn chọn
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là một gia sư AI . Hãy trả lời cực kỳ ngắn gọn, súc tích và chính xác."
                },
                {
                    "role": "user",
                    "content": user_input,
                }
            ],
            model="llama-3.3-70b-versatile", # Hoặc "llama-4-scout-instruct"
            temperature=0.5,
            max_tokens=1024,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Lỗi Groq API: {str(e)}"
app.secret_key = "ai_project_secret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///study_data.db'
db = SQLAlchemy(app)
# --- CẤU HÌNH UPLOAD ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), default="Chưa rõ")
    dob_year = db.Column(db.Integer, default=2000)
    profile_pic = db.Column(db.String(200), default='default_avatar.png')
    targets = db.relationship('SubjectTarget', backref='user', lazy=True)

class SubjectTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(50), nullable=False)
    target_score = db.Column(db.Float, default=0.0)
    total_needed = db.Column(db.Float, default=0.0)

class StudyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today)
    hours = db.Column(db.Float)
class RoadmapProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.String(50), nullable=False) # VD: 'calc_1'
    is_completed = db.Column(db.Boolean, default=False)
# --- AI LOGIC ---
def ai_reverse_predict(target, abs_val, mid_val, sub):
    model_path = f"model_{sub}.pkl"
    if not os.path.exists(model_path): return None, None
    
    with open(model_path, "rb") as f:
        m = pickle.load(f)
    
    w, b = m.coef_, m.intercept_
    # Công thức dự đoán ngược
    h_per_day = (target - (w[1]*abs_val + w[2]*mid_val + b)) / w[0]
    return round(h_per_day, 1), round(h_per_day*2, 1)

# --- ROUTES ---

@app.route("/")
def home():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if user:
            session['user_id'] = user.id
            flash('Đăng nhập thành công! Chào mừng bạn quay trở lại.', 'success')
            return redirect(url_for('dashboard'))
        else :
            flash('Sai tài khoản hoặc mật khẩu. Vui lòng kiểm tra lại!', 'error')
    return render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        flash('Tạo tài khoản thành công! Giờ bạn có thể đăng nhập.', 'success')
        return redirect(url_for('login'))
        db.session.rollback()
        flash('Đăng ký không thành công. Vui lòng kiểm tra lại!', 'error')
    return render_template("register.html")

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # Lấy thông tin user từ DB
    user = User.query.get(session['user_id'])
    
    # THÊM ĐOẠN NÀY ĐỂ FIX LỖI:
    if user is None:
        session.pop('user_id', None) # Xóa session cũ bị lỗi đi
        return redirect(url_for('login')) # Quay về trang login
    
    if request.method == 'POST':
        if 'set_target' in request.form:
            sub = request.form['subject']
            target_val = float(request.form['target'])
            _, total = ai_reverse_predict(target_val, float(request.form['absences']), float(request.form['midterm']), sub)
            
            st = SubjectTarget.query.filter_by(user_id=user.id, subject=sub).first()
            if not st:
                st = SubjectTarget(user_id=user.id, subject=sub)
                db.session.add(st)
            st.target_score, st.total_needed = target_val, (total or 0)
            db.session.commit()
            flash("Đã dự đoán số giờ học thành công!", "success")
        elif 'add_hours' in request.form:
            try :
                h = float(request.form['hours'])
                if 0 < h <= 24 :

                    db.session.add(StudyLog(user_id=user.id, subject=request.form['subject'], hours = h))
                    db.session.commit()
                    flash("Đã lưu giờ học thành công!", "success")
                else :
                    flash("Số giờ học không được vượt quá 24 tiếng/ngày!", "danger")
            except ValueError :
                pass
        return redirect(url_for('dashboard'))

    subjects_data = []
    for t in user.targets:
        learned = db.session.query(db.func.sum(StudyLog.hours)).filter_by(user_id=user.id, subject=t.subject).scalar() or 0
        percent = round((learned / t.total_needed * 100), 1) if t.total_needed > 0 else 0
        subjects_data.append({'name': t.subject, 'percent': percent, 'target': t.target_score, 'needed': t.total_needed, 'learned': learned})
    all_logs = StudyLog.query.filter_by(user_id=user.id).order_by(StudyLog.date.desc()).all()
    return render_template("dashboard.html", user=user, subjects=subjects_data, all_logs=all_logs)

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
# Chức năng 1: Xóa hoàn toàn một môn học (Xóa mục tiêu và tất cả giờ học của môn đó)
@app.route("/delete_subject/<string:sub_name>")
def delete_subject(sub_name):
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    
    # Xóa tất cả nhật ký học của môn này
    StudyLog.query.filter_by(user_id=user_id, subject=sub_name).delete()
    # Xóa mục tiêu điểm của môn này
    SubjectTarget.query.filter_by(user_id=user_id, subject=sub_name).delete()
    
    db.session.commit()
    return redirect(url_for('dashboard'))

# Chức năng 2: Hoàn tác (Xóa bản ghi nhật ký học tập gần đây nhất)
@app.route("/undo_last_log")
def undo_last_log():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Tìm bản ghi cuối cùng của user này
    last_log = StudyLog.query.filter_by(user_id=session['user_id']).order_by(StudyLog.id.desc()).first()
    
    if last_log:
        db.session.delete(last_log)
        db.session.commit()
        
    return redirect(url_for('dashboard'))

@app.route("/profile", methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.gender = request.form['gender']
        user.dob_year = request.form['dob_year']
        
        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            # Đổi tên file để tránh trùng lặp: user_1_avatar.jpg
            filename = secure_filename(f"user_{user.id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = filename
            
        db.session.commit()
        return redirect(url_for('dashboard'))
        
    return render_template("profile.html", user=user)



@app.route("/toggle_roadmap/<item_id>")
def toggle_roadmap(item_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    
    progress = RoadmapProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
    if progress:
        db.session.delete(progress)
    else:
        db.session.add(RoadmapProgress(user_id=user_id, item_id=item_id, is_completed=True))
    
    db.session.commit()
    return redirect(url_for('roadmap'))

@app.route("/roadmap")
@app.route("/roadmap/<subject>") # Flask sẽ hiểu cả 2 đường dẫn này
def roadmap(subject='toan'): # Nếu không có <subject>, mặc định là 'toan'
    if 'user_id' not in session: 
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    
    # Lấy dữ liệu từ Dictionary ROADMAPS
    # Nếu subject truyền vào không tồn tại trong ROADMAPS, lấy 'toan' làm dự phòng
    selected_roadmap = ROADMAPS.get(subject, ROADMAPS['toan'])
    
    # Lấy danh sách ID các mục đã hoàn thành
    completed_ids = [p.item_id for p in RoadmapProgress.query.filter_by(user_id=user.id).all()]
    
    return render_template("roadmap.html", 
                           user=user, 
                           roadmap=selected_roadmap, 
                           completed=completed_ids,
                           current_sub=subject)

@app.route("/ask_ai", methods=['POST'])
def ask_ai():
    if 'user_id' not in session: 
        return jsonify({"error": "Vui lòng đăng nhập"}), 403
    
    # Lấy tin nhắn từ phía giao diện gửi lên
    data = request.get_json()
    user_message = data.get("message")
    
    if not user_message:
        return jsonify({"reply": "Bạn chưa nhập câu hỏi mà!"})

    try:
        bot_reply = get_ai_response(user_message)
        return jsonify({"reply": bot_reply})
    except Exception as e:
        print(f"Lỗi AI: {e}")
        return jsonify({"reply": "Robot đang bận xử lý dữ liệu, thử lại sau nhé!"})
if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Tự động tạo database khi chạy lần đầu
    print("AI Study Bot đang khởi động tại http://127.0.0.1:5000")
    app.run(debug=True)