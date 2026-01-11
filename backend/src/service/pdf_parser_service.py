import re
from pypdf import PdfReader


def sanitize_text_for_postgres(text: str) -> str:
    """
    清理文本中 PostgreSQL JSONB 不支持的字符。
    
    主要处理：
    - NULL 字符 (\u0000) - PostgreSQL 不支持
    - 其他不可打印的控制字符
    """
    if not text:
        return text
    
    # 移除 NULL 字符（\u0000）
    text = text.replace('\u0000', '')
    
    # 移除其他不安全的控制字符（保留换行、制表符等常用字符）
    # 保留: \t (0x09), \n (0x0A), \r (0x0D)
    # 移除: 0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    return text


def extract_pdf_markdown(pdf_path: str) -> str:
    """
    从 PDF 提取文本并清理不安全字符。
    """
    reader = PdfReader(pdf_path)
    raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    return sanitize_text_for_postgres(raw_text)