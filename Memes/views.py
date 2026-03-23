from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import pymysql
import pandas as pd
from joblib import load
import os
from io import TextIOWrapper
from PIL import Image
from transformers import  ViTFeatureExtractor, ViTModel
from sklearn.utils import resample
from django.contrib import messages

from PIL import Image
from transformers import  ViTFeatureExtractor, ViTModel
from sklearn.utils import resample

# ===============================
# Core Python Libraries
# ===============================
import pickle
import joblib
import numpy as np
from collections import Counter
from scipy.special import expit  # sigmoid

# ===============================
# NLP: NLTK & Gensim
# ===============================
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from nltk.util import ngrams

# ===============================
# Scikit-learn: Preprocessing, Models, Metrics
# ===============================

from sklearn.ensemble import RandomForestClassifier

# ===============================
# Transformers (Hugging Face)
# ===============================
from transformers import (
    AutoTokenizer, AutoModel,
    RobertaTokenizer, RobertaModel,
    BertTokenizer, BertForSequenceClassification,
    XLNetTokenizer, XLNetForSequenceClassification
)
from torch.optim import AdamW
import torch
from sklearn.linear_model import LogisticRegression
from django.core.files.storage import FileSystemStorage
from django.conf import settings

MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)


def ensure_single_admin():    
    try:
        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='mysql123',
            database='mydb'
        )
        with con:
            cur = con.cursor()

        
            cur.execute("SELECT id FROM emp_details3 WHERE role='admin'")
            admin = cur.fetchone()

            
            if not admin:
                cur.execute("""
                    INSERT INTO emp_details3
                    (username, email, password, role, approved, address, mobile)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    "admin",
                    "admin@gmail.com",
                    "admin",
                    "admin",
                    1,                     
                    "hyderabad",
                    "1234567890"
                ))
                con.commit()

    except Exception as e:
        print("Error ensuring admin:", e)



def index(request):
    return render(request, 'index.html')

def user_page(request):
    user = request.session.get('user')
    if not user:
        return redirect('login')  
    return render(request, 'user.html', {'user': user})


@csrf_exempt
def approve_user(request, username):
    user = request.session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect('login')

    try:
        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='mysql123',
            database='mydb'
        )
        with con:
            cur = con.cursor()
            cur.execute("UPDATE emp_details3 SET approved = 1 WHERE username = %s", (username,))
            con.commit()
    except Exception as e:
        print("Error approving user:", e)

    return redirect('admin_page')


def admin_page(request):
    user = request.session.get('user')
    if not user:
        return redirect('login')

    if user.get('role') != 'admin':
        return redirect('user_page')

    users_list = []
    try:
        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='mysql123',
            database='mydb'
        )
        with con:
            cur = con.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT * FROM emp_details3 WHERE role='user'")
            users_list = cur.fetchall()

    except Exception as e:
        return render(request, 'admin.html', {
            'user': user,
            'error': f'Database error: {str(e)}'
        })

    return render(request, 'admin.html', {'user': user, 'users_list': users_list})



def register_view(request):

    ensure_single_admin()

    message = None

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        mobile = request.POST.get('mobile')          
        address = request.POST.get('address')        
        role = "user"                               

        if password != confirm_password:
            message = {'error': 'Passwords do not match'}

        else:
            try:
                con = pymysql.connect(
                    host='127.0.0.1',
                    port=3306,
                    user='root',
                    password='mysql123',
                    database='mydb'
                )
                with con:
                    cur = con.cursor()

                    cur.execute("SELECT username FROM emp_details3 WHERE username=%s", (username,))
                    if cur.fetchone():
                        message = {'error': 'Username already exists'}


                    else:
                        cur.execute("SELECT email FROM emp_details3 WHERE email=%s", (email,))
                        if cur.fetchone():
                            message = {'error': 'Email already exists'}
                        cur.execute("SELECT mobile FROM emp_details3 WHERE mobile=%s", (mobile,))
                        if cur.fetchone():
                            message = {'error': 'mobile already exists'}
                        else:
                            cur.execute("""
                                INSERT INTO emp_details3
                                (username, email, password, role, approved, mobile, address)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (username, email, password, role, 0, mobile, address))

                            con.commit()
                            message = {'success': 'Account created successfully! Awaiting admin approval.'}

            except Exception as e:
                message = {'error': f'Database error: {str(e)}'}

    return render(request, 'register.html', message)




# ============================================================
#  LOGIN VIEW — ADMIN AUTO-CREATION ADDED
# ============================================================
def login_view(request):

    ensure_single_admin()    

    context = {}

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            con = pymysql.connect(
                host='127.0.0.1',
                port=3306,
                user='root',
                password='mysql123',
                database='mydb'
            )
            with con:
                cur = con.cursor(pymysql.cursors.DictCursor)
                cur.execute(
                    "SELECT * FROM emp_details3 WHERE username=%s AND password=%s",
                    (username, password)
                )
                user = cur.fetchone()

                if user:
                    if not user.get('approved') and user['role'] == 'user':
                        context['error'] = 'Your account is awaiting admin approval.'
                    else:
                        request.session['user'] = user

                        if user['role'] == 'admin':
                            return redirect('admin_page')
                        else:
                            return redirect('user_page')

                else:
                    context['error'] = 'Invalid login credentials'

        except Exception as e:
            context['error'] = f'Database error: {str(e)}'

    return render(request, 'login.html', context)

def preprocess_data(df, save_path=None, target_cols=None):

    global label_encoders
    label_encoders = {}  

    if save_path and os.path.exists(save_path):
        print(f"Loading existing preprocessed file: {save_path}")
        df = pd.read_csv(save_path)
    else:
        print("Preprocessing data" + (f" and saving to: {save_path}" if save_path else " (no saving)"))
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))

        def clean_text(text):
            text = str(text).lower()
            tokens = word_tokenize(text)
            tokens = [lemmatizer.lemmatize(t) for t in tokens if t.isalnum() and t not in stop_words]
            return ' '.join(tokens)
        
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        if 'image_name' in df.columns:
            df = df.drop(columns=['image_name'])
            
        # Separate target columns
        target_df = None
        if target_cols:
            existing_targets = [col for col in target_cols if col in df.columns]
            target_df = df[existing_targets].copy()
            df = df.drop(columns=existing_targets)

        # Process text columns
        text_columns = df.select_dtypes(include='object').columns
        for col in text_columns:
            df[f'processed_{col}'] = df[col].apply(clean_text)

        # Drop original text columns
        df.drop(columns=text_columns, inplace=True)

        # Reattach target columns
        if target_df is not None:
            for col in target_df.columns:
                df[col] = target_df[col]

        # Save only if path is specified
        if save_path:
            df.to_csv(save_path, index=False)

    # Select processed and numerical columns
    processed_text_cols = [col for col in df.columns if col.startswith('processed_')]
    non_text_cols = [col for col in df.columns if col not in processed_text_cols + (target_cols if target_cols else [])]

    # Join processed text columns into one string
    X_text = df[processed_text_cols].astype(str).agg(' '.join, axis=1)

    # Combine with numerical columns if any
    X_numeric = df[non_text_cols].values if non_text_cols else None
    if X_numeric is not None and len(X_numeric) > 0:
        X = [f"{text} {' '.join(map(str, numeric))}" for text, numeric in zip(X_text, X_numeric)]
    else:
        X = X_text.tolist()

    # Encode multiple target columns
    Y_dict = {}
    if target_cols:
        for col in target_cols:
            if col in df.columns:
                le = LabelEncoder()
                Y_dict[col] = le.fit_transform(df[col])
                label_encoders[col] = le

    return X, Y_dict

import torch
import joblib
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

# -------------------------------
# XLNet Feature Extraction
# -------------------------------
def xlnet_feature_extraction(texts, model_name='xlnet-base-cased', batch_size=32, pooling='mean'):
    """Extract XLNet features from texts with tqdm progress bar."""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    all_embeddings = []

    for i in tqdm(range(0, len(texts), batch_size), desc="Extracting XLNet embeddings"):
        batch_texts = texts[i:i + batch_size]
        encoded_input = tokenizer(batch_texts, padding=True, truncation=True, return_tensors='pt')

        with torch.no_grad():
            model_output = model(**encoded_input)

        token_embeddings = model_output.last_hidden_state  # [batch_size, seq_len, hidden_dim]
        attention_mask = encoded_input['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

        # Pooling
        if pooling == 'mean':
            sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
            sum_mask = input_mask_expanded.sum(dim=1)
            embeddings = sum_embeddings / sum_mask
        elif pooling == 'cls':
            # XLNet does not have a [CLS] token like BERT; use the last token representation
            embeddings = token_embeddings[:, -1, :]
        else:
            raise ValueError("Pooling must be 'mean' or 'cls'")

        all_embeddings.append(embeddings.cpu().numpy())

    X = np.vstack(all_embeddings)
    return X, model


# -------------------------------
# Wrapper for Training/Testing
# -------------------------------
def feature_extraction(X_text, method='XLNet_word_embeddings', model_dir='model', is_train=True):
    x_file = os.path.join(model_dir, f'X_{method}.pkl')

    print(f"[INFO] Feature extraction method: {method}, Train mode: {is_train}")
    model_name = 'xlnet-base-cased'  # Other options: 'xlnet-large-cased'

    if is_train:
        if os.path.exists(x_file):
            print(f"[INFO] Loading cached XLNet features from {x_file}")
            X = joblib.load(x_file)
        else:
            print("[INFO] Computing XLNet features...")
            X, model = xlnet_feature_extraction(X_text, model_name=model_name, pooling='mean')
            os.makedirs(model_dir, exist_ok=True)
            joblib.dump(X, x_file)
    else:
        print("[INFO] Performing XLNet feature extraction for testing...")
        X, model = xlnet_feature_extraction(X_text, model_name=model_name, pooling='mean')

    return X

class SLIMClassifier():

    def __init__(self,  max_depth=None, random_state=42):
        """
        Initialize the internal RandomForestClassifier.
        :param n_estimators: Number of trees in the forest
        :param max_depth: Maximum depth of the tree
        :param random_state: Random seed
        """
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = RandomForestClassifier(
            max_depth=self.max_depth,
            random_state=self.random_state
        )

    def fit(self, X, y):

        self.model.fit(X, y)
        return self

    def predict(self, X):

        return self.model.predict(X)

    def predict_proba(self, X):

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        else:
            preds = self.model.predict(X)
            classes = np.unique(preds)
            proba = np.zeros((len(preds), len(classes)))
            for i, p in enumerate(preds):
                proba[i, np.where(classes == p)[0][0]] = 1.0
            return proba

    def score(self, X, y):

        return self.model.score(X, y)

    

def prediction_page(request):
    prediction_table = None
    uploaded_filename = None
    labels1 = ['Non-offensiv', 'offensive']

    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        uploaded_filename = file.name
        df_test1 = pd.read_csv(file)
        df_result = df_test1.copy()

        #Preprocess uploaded file
        df_test, _ = preprocess_data(df_test1)

        #  Generate embeddings (set is_train=False)
        features_test = feature_extraction(df_test,method='XLNet_word_embeddings',is_train=None)

        model_path = r"Memes\Model\label_SLIM.pkl"

# Temporary compatibility fix
        import sys
        sys.modules['__main__'].SLIMClassifier = SLIMClassifier

 
        
        # Load the model safely
        model = joblib.load(model_path)
        #  Predict sentiments
        y_pred = model.predict(features_test)
        mapped_labels = [labels1[i] for i in y_pred]
        df_result['Predicted_output'] = mapped_labels
        df_result.insert(0, "Sl.No", range(0, len(df_result)))

        #  Display prediction table
        prediction_table = df_result.to_html(
            classes='table table-bordered table-striped table-hover',
            index=False
        )

        messages.success(request, f"Predictions generated successfully for {uploaded_filename}")

    return render(
        request,
        'prediction.html',
        {
            'prediction_table': prediction_table,
            'uploaded_filename': uploaded_filename
        }
    )


device = "cuda" if torch.cuda.is_available() else "cpu"

# ViT for images
vit_model_name = "google/vit-base-patch16-224"
vit_model = ViTModel.from_pretrained(vit_model_name).to(device)
vit_model.eval()
vit_feature_extractor = ViTFeatureExtractor.from_pretrained(vit_model_name)

# -------------------------
# Preprocessing helpers
# -------------------------
def preprocess_image(file_path):
    print(file_path)
    img = Image.open(file_path).convert("RGB")
    inputs = vit_feature_extractor(images=img, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)
    return pixel_values  # shape: [1, 3, 224, 224]

# -------------------------
# ViT Feature extraction
# -------------------------
def extract_features_image(pixel_values):
    with torch.no_grad():
        outputs = vit_model(pixel_values)
    pooled = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
    return pooled

# -------------------------
# Dataset loader
# -------------------------
def load_dataset_vit(model_folder, dataset_path):
    os.makedirs(model_folder, exist_ok=True)

    x_image_path = os.path.join(model_folder, "X_Image_ViT.npy")
    y_image_path = os.path.join(model_folder, "Y_Image_ViT.npy")

    # Load cached datasets
    if all(os.path.exists(p) for p in [x_image_path, y_image_path]):
        print("🔹 Loading cached datasets...")
        X_image = np.load(x_image_path, allow_pickle=True)
        Y_image = np.load(y_image_path, allow_pickle=True)

        # -----------------------------
        # Resample Image Dataset to 1300 per class
        # -----------------------------
        X_image_resampled = []
        Y_image_resampled = []
        
        for cls in np.unique(Y_image):
            X_cls = X_image[Y_image == cls]
            Y_cls = Y_image[Y_image == cls]
        
            X_res, Y_res = resample(
                X_cls, Y_cls,
                replace=True if len(X_cls) < 300 else False,
                n_samples=300,
                random_state=42
            )
        
            X_image_resampled.append(X_res)
            Y_image_resampled.append(Y_res)
        
        X_image_resampled = np.vstack(X_image_resampled)
        Y_image_resampled = np.hstack(Y_image_resampled)
        
        # -----------------------------
        # Save back to same files
        # -----------------------------
        np.save(x_image_path, X_image_resampled)
        np.save(y_image_path, Y_image_resampled)
        return X_image, Y_image

    # Initialize
    X_image, Y_image = [], []

    for modality in ["Image Dataset"]:
        for label in ["Offensive", "Non-offensive"]:
            folder = os.path.join(dataset_path, modality, label)
            if not os.path.exists(folder):
                continue
            print(f"📂 Processing {folder} ...")
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                try:
                    if modality == "Image Dataset" and file.lower().endswith((".jpg", ".png", ".jpeg")):
                        pixel_values = preprocess_image(file_path)
                        features = extract_features_image(pixel_values)
                        # Corrected label mapping
                        Y_value = 0 if label == "Non-offensive" else 1
                        X_image.append(features)
                        Y_image.append(Y_value)
                except Exception as e:
                    print("⚠️ Skipping:", file_path, "| Error:", e)

    # Convert to numpy
    X_image = np.array(X_image, dtype=np.float32)
    Y_image = np.array(Y_image, dtype=np.int64)

    # Save
    np.save(x_image_path, X_image)
    np.save(y_image_path, Y_image)
    print(f"✅ Saved datasets in {model_folder}")

    return X_image, Y_image

    model_folder = "Model"
    dataset_path = "MultiOFF_Dataset"
    X_image, Y_image = load_dataset_vit(model_folder, dataset_path)

    print("X_image shape:", X_image.shape)
    print("Y_image shape:", Y_image.shape)


def split_all_datasets(X_image=None, Y_image=None, features_dict=None, Y_dict=None,
                       test_size=0.2, random_state=42):
    """
    Combined train-test split for both image and tabular (dict-based) datasets.

    Parameters:
    - X_image, Y_image: image features and labels (numpy arrays)
    - features_dict: dict of feature arrays keyed by target_name
    - Y_dict: dict of target arrays keyed by target_name
    - test_size: fraction of test data
    - random_state: seed for reproducibility

    Returns:
    - splits: dict containing train-test splits for all datasets
    """
    splits = {}

    # ----------- Split Image Dataset -----------
    if X_image is not None and Y_image is not None:
        stratify_img = Y_image if len(np.unique(Y_image)) > 1 and len(Y_image) > 1 else None
        X_train_img, X_test_img, y_train_img, y_test_img = train_test_split(
            X_image, Y_image, test_size=test_size, random_state=random_state, stratify=stratify_img
        )
        splits['image'] = {
            'X_train': X_train_img,
            'X_test': X_test_img,
            'y_train': y_train_img,
            'y_test': y_test_img
        }
        print(f"✅ Image data split: {X_train_img.shape[0]} train, {X_test_img.shape[0]} test samples")

    # ----------- Split Tabular Dictionary Dataset -----------
    if features_dict is not None and Y_dict is not None:
        splits['tabular'] = {}
        for target_name, y_encoded in Y_dict.items():
            # Get features for this target
            X = features_dict[target_name] if isinstance(features_dict, dict) else features_dict

            # Handle stratify safely
            stratify_tab = y_encoded if len(np.unique(y_encoded)) > 1 and len(y_encoded) > 1 else None

            # Train-test split
            X_train_tab, X_test_tab, y_train_tab, y_test_tab = train_test_split(
                X, y_encoded, test_size=test_size, random_state=random_state, stratify=stratify_tab
            )

            splits['tabular'][target_name] = {
                'X_train': X_train_tab,
                'X_test': X_test_tab,
                'y_train': y_train_tab,
                'y_test': y_test_tab
            }

            print(f"✅ Tabular [{target_name}] split: {X_train_tab.shape[0]} train, {X_test_tab.shape[0]} test samples")

    return splits
    splits = split_all_datasets(
    X_image=X_image, Y_image=Y_image,
    features_dict=features, Y_dict=Y_dict,
    test_size=0.2, random_state=42
)

# Image splits
    X_train_img = splits['image']['X_train']
    y_train_img = splits['image']['y_train']

# Tabular splits - loop over all targets
    for target_name in splits['tabular'].keys():
        X_train_tab = splits['tabular'][target_name]['X_train']
        X_test_tab = splits['tabular'][target_name]['X_test']
        y_train_tab = splits['tabular'][target_name]['y_train']
        y_test_tab = splits['tabular'][target_name]['y_test']

    print(f"Target: {target_name}, Train: {X_train_tab.shape[0]}, Test: {X_test_tab.shape[0]}")


def train_logistic_regression(splits, metrics_calculator, Algorithm_prefix="LR"):
    image_model = {}
    tabular_model = {}

    # ----------- Image dataset -----------
    if 'image' in splits:
        X_train = splits['image']['X_train']
        X_test = splits['image']['X_test']
        y_train = splits['image']['y_train']
        y_test = splits['image']['y_test']

        mdl = LogisticRegression(max_iter=10)
        mdl.fit(X_train, y_train)

        y_pred = mdl.predict(X_test)
        try:
            y_score = mdl.predict_proba(X_test)
        except AttributeError:
            y_score = None

        algo_name = f"{Algorithm_prefix} [Image]"
        metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
        image_model[f"{Algorithm_prefix}_image"] = mdl

    # ----------- Tabular dataset -----------
    if 'tabular' in splits:
        for target_name, data in splits['tabular'].items():
            X_train = data['X_train']
            X_test = data['X_test']
            y_train = data['y_train']
            y_test = data['y_test']

            mdl = LogisticRegression(max_iter=10)
            mdl.fit(X_train, y_train)

            y_pred = mdl.predict(X_test)
            try:
                y_score = mdl.predict_proba(X_test)
            except AttributeError:
                y_score = None

            algo_name = f"{Algorithm_prefix} [{target_name}]"
            metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
            tabular_model[f"{target_name}_{Algorithm_prefix}"] = mdl

    return image_model, tabular_model

# ---------------- Decision Tree Classifier ----------------
def train_decision_tree(splits, metrics_calculator, Algorithm_prefix="DTC"):
    image_model = {}
    tabular_model = {}

    if 'image' in splits:
        X_train, X_test = splits['image']['X_train'], splits['image']['X_test']
        y_train, y_test = splits['image']['y_train'], splits['image']['y_test']

        mdl = DecisionTreeClassifier(max_depth=5, random_state=42)
        mdl.fit(X_train, y_train)

        y_pred = mdl.predict(X_test)
        try: y_score = mdl.predict_proba(X_test)
        except AttributeError: y_score = None

        algo_name = f"{Algorithm_prefix} [Image]"
        metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
        image_model[f"{Algorithm_prefix}_image"] = mdl

    if 'tabular' in splits:
        for target_name, data in splits['tabular'].items():
            X_train, X_test = data['X_train'], data['X_test']
            y_train, y_test = data['y_train'], data['y_test']

            mdl = DecisionTreeClassifier(max_depth=5, random_state=42)
            mdl.fit(X_train, y_train)

            y_pred = mdl.predict(X_test)
            try: y_score = mdl.predict_proba(X_test)
            except AttributeError: y_score = None

            algo_name = f"{Algorithm_prefix} [{target_name}]"
            metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
            tabular_model[f"{target_name}_{Algorithm_prefix}"] = mdl

    return image_model, tabular_model

# ---------------- K-Nearest Neighbors ----------------
def train_knn(splits, metrics_calculator, Algorithm_prefix="KNN"):
    image_model = {}
    tabular_model = {}

    if 'image' in splits:
        X_train, X_test = splits['image']['X_train'], splits['image']['X_test']
        y_train, y_test = splits['image']['y_train'], splits['image']['y_test']

        mdl = KNeighborsClassifier(n_neighbors=5)
        mdl.fit(X_train, y_train)

        y_pred = mdl.predict(X_test)
        try: y_score = mdl.predict_proba(X_test)
        except AttributeError: y_score = None

        algo_name = f"{Algorithm_prefix} [Image]"
        metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
        image_model[f"{Algorithm_prefix}_image"] = mdl

    if 'tabular' in splits:
        for target_name, data in splits['tabular'].items():
            X_train, X_test = data['X_train'], data['X_test']
            y_train, y_test = data['y_train'], data['y_test']

            mdl = KNeighborsClassifier(n_neighbors=5)
            mdl.fit(X_train, y_train)

            y_pred = mdl.predict(X_test)
            try: y_score = mdl.predict_proba(X_test)
            except AttributeError: y_score = None

            algo_name = f"{Algorithm_prefix} [{target_name}]"
            metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
            tabular_model[f"{target_name}_{Algorithm_prefix}"] = mdl

    return image_model, tabular_model

import os
import joblib

def train_slim(splits, metrics_calculator, Algorithm_prefix="SLIM", model_dir="model"):

    os.makedirs(model_dir, exist_ok=True)
    image_model = {}
    tabular_model = {}

    # ----------- Image dataset -----------
    if 'image' in splits:
        X_train, X_test = splits['image']['X_train'], splits['image']['X_test']
        y_train, y_test = splits['image']['y_train'], splits['image']['y_test']

        model_path = os.path.join(model_dir, f"{Algorithm_prefix}_image.pkl")
        if os.path.exists(model_path):
            mdl = joblib.load(model_path)
            print(f"✅ Loaded existing image model: {model_path}")
        else:
            mdl = SLIMClassifier()
            mdl.fit(X_train, y_train)
            joblib.dump(mdl, model_path)
            print(f"✅ Trained and saved image model: {model_path}")

        y_pred = mdl.predict(X_test)
        try: y_score = mdl.predict_proba(X_test)
        except AttributeError: y_score = None

        algo_name = f"{Algorithm_prefix} [Image]"
        metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
        image_model[f"{Algorithm_prefix}_image"] = mdl

    # ----------- Tabular dataset -----------
    if 'tabular' in splits:
        for target_name, data in splits['tabular'].items():
            X_train, X_test = data['X_train'], data['X_test']
            y_train, y_test = data['y_train'], data['y_test']

            model_path = os.path.join(model_dir, f"{target_name}_{Algorithm_prefix}.pkl")
            if os.path.exists(model_path):
                mdl = joblib.load(model_path)
                print(f"✅ Loaded existing tabular model: {model_path}")
            else:
                mdl = SLIMClassifier()
                mdl.fit(X_train, y_train)
                joblib.dump(mdl, model_path)
                print(f"✅ Trained and saved tabular model: {model_path}")

            y_pred = mdl.predict(X_test)
            try: y_score = mdl.predict_proba(X_test)
            except AttributeError: y_score = None

            algo_name = f"{Algorithm_prefix} [{target_name}]"
            metrics_calculator.calculate_metrics(algo_name, y_pred, y_test, y_score)
            tabular_model[f"{target_name}_{Algorithm_prefix}"] = mdl

    return image_model, tabular_model

import matplotlib.pyplot as plt
from PIL import Image

def predict_from_image(file_path):

    # -------- Preprocess Image --------
    pixel_values = preprocess_image(file_path)  # tensor on device
    features = extract_features_image(pixel_values)  # NumPy array for SLIMClassifier

    # Convert features to 2D array if needed
    if isinstance(features, torch.Tensor):
        features = features.detach().cpu().numpy()
    if len(features.shape) == 1:
        features = features.reshape(1, -1)

    # -------- Prediction --------
    model_key = list(image_model.keys())[0]
    mdl = image_model[model_key]
    y_pred = mdl.predict(features)[0]
    pred_class = labels1[y_pred]
    # -------- Display Image with Prediction as Title --------
    img = Image.open(file_path).convert("RGB")
    plt.figure(figsize=(6, 6))
    plt.imshow(img)
    plt.axis('off')
    plt.title(f"Prediction Output: {pred_class}", fontsize=20, color='red')
    plt.show()

    return pred_class

    file_path = r"C:\Users\dell\Desktop\nlp\6. Hate Speech in Memes\MemeSentinel\Test Images\0bOKK62.png"
    predict_from_image(file_path)



def imageprediction_page(request):
    prediction_output = None
    uploaded_filename = None
    image_url = None

    if request.method == "POST" and request.FILES.get("image"):

        image_file = request.FILES["image"]
        uploaded_filename = image_file.name

        # Save image to MEDIA folder
        fs = FileSystemStorage()
        filename = fs.save(image_file.name, image_file)
        image_url = fs.url(filename)     # URL to display in template

        # Preprocess image
        temp_path = fs.path(filename)
        pixel_values = preprocess_image(temp_path)
        features = extract_features_image(pixel_values)
        features = features.reshape(1, -1)

        # Load model
        import sys
        sys.modules['__main__'].SLIMClassifier = SLIMClassifier
        model_path = os.path.join(settings.BASE_DIR, "Memes", "Model", "SLIM_image.pkl")
        image_model = joblib.load(model_path)

        # Predict
        y_pred = image_model.predict(features)[0]
        labels1 = ['Non-offensiv', 'offensive']
        prediction_output = labels1[y_pred]

    return render(
        request,
        "image-prediction.html",
        {
            "prediction_output": prediction_output,
            "uploaded_filename": uploaded_filename,
            "image_url": image_url
        }
    )
