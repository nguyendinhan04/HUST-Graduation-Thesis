import re
import unidecode


def keyword_normalize(keyword: str) -> str:
    # chuyển từ chữ có dấu thành không dấu
    normalized = unidecode.unidecode(keyword)
    # chuyển thành chữ thường
    normalized = normalized.lower()
    # thay khoảng trắng bằng dấu gạch nối
    normalized = re.sub(r'\s+', '-', normalized)
    # thay ký tự đặc biệt bằng dấu gạch nối
    normalized = re.sub(r'[^a-z0-9\-]', '-', normalized)
    return normalized

if __name__ == "__main__":
    test_keywords = [
        "Kỹ sư phần mềm",
        "Quản trị mạng",
        "Phát triển web",
        "Lập trình viên Java",
        "Chuyên viên phân tích dữ liệu",
        "Kinh doanh thiết bị/vật liệu xây dựng"
    ]
    for kw in test_keywords:
        print(f"Original: {kw} -> Normalized: {keyword_normalize(kw)}")
