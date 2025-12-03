# HUST-Graduation-Thesis
*This is my graduation thesis in Hanoi University of Science and Technology. The project aims to develop a robust, scalable data platfrom and machine learning model to predict and give user with useful advices for their career.*


## 1. Project description
- **Project purpose**:
- **Why matter**:
- **Solution**:
- **Scope**:

## 2. Project file structure
```text
/
├── data/                   # chứa dữ liệu thô, dữ liệu đã xử lý
│   ├── raw/                # dữ liệu gốc từ crawling
│   ├── processed/          # dữ liệu đã làm sạch, biến đổi
│   └── README.md           # mô tả dữ liệu nếu riêng biệt
├── notebooks/              # Jupyter notebooks phân tích, khám phá dữ liệu
├── src/                    # mã nguồn chính
│   ├── airflow/            # module airflow DAGs và operators
│   ├── JobUpdateConsumer/  # module crawling dữ liệu việc làm
│   ├── models/             # module huấn luyện, lưu mô hình
│   └── api/                # module triển khai inference API
├── models/                 # mô hình đã huấn luyện lưu lại (.pkl, .pt,…)
├── requirements.txt        # các thư viện cần thiết
└── README.md               # file bạn đang đọc
```
## 3. Setup guide
**Install and setup Python environment**
```shell
conda create -n rent-price-predict python=3.12
conda activate rent-price-predict
pip install -r requirements.txt
```
## 4. Usage
### 4.1 Crawling data
### 4.2 Model training
### 4.3 Deploy API inference


## 5. Architecture and Design

## 6. Key Features

## 7. Techonologies and Frameworks
- Data scrapping: `Beautifulsoup`, `Selenium`, `Scrapy`
- Data processing: `Numpy`, `Pandas`, `Scikitlearn`
- Explonatory data analysis: `Matplotlib`, `Seaborn`
- Model: `XGBoost`, `Prophet`
- Model deployment: `FastAPI`

## 8. Limitations and development directions

## 9. Acknowledgements  
- Thanks to the open source libraries the project uses.