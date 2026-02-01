# src/service/image_generation_service.py

"""
论文漫画图生成服务 - 使用 Gemini 生成论文的图解

使用方法:
    from src.service.image_generation_service import generate_paper_comic

    key = generate_paper_comic(
        paper_id="2401.12345",
        paper_content="论文摘要或内容",
    )
"""

import logging
import mimetypes
import time
from typing import Optional

from google import genai
from google.genai import types

from src.config import Config
from src.service.storage_service import get_storage

# 重试配置
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 3

logger = logging.getLogger(__name__)


class PaperComicGenerator:
    """论文漫画生成器"""

    DEFAULT_PROMPT_TEMPLATE = """
你是一位擅长用漫画解释复杂学术概念的老师。

请根据以下学术论文内容，制作一个竖版长图（10格漫画形式）：

## 要求：
1. **格式**：竖版长图，分为10格漫画
2. **风格**：像一个耐心的老师给学生详细讲解
3. **内容**：
   - 第1格：论文标题和核心问题
   - 第2-3格：背景知识和动机
   - 第4-6格：核心方法/技术（用简单的图示解释）
   - 第7-8格：实验结果和关键发现
   - 第9格：对比和优势
   - 第10格：总结和应用场景
4. **表现**：用简洁的文字配合清晰的插图，让非专业人士也能理解

请给我纯图片响应，不要返回任何文本。
请给我纯图片响应，不要返回任何文本。
请给我纯图片响应，不要返回任何文本。
请给我纯图片响应，不要返回任何文本。

## 论文内容：
{paper_content}

请给我纯图片响应，不要返回任何文本。
请给我纯图片响应，不要返回任何文本。
请给我纯图片响应，不要返回任何文本。
请给我纯图片响应，不要返回任何文本。
"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.gemini.api_key
        if not self.api_key:
            raise ValueError("需要设置 gemini.api_key 配置或传入 api_key 参数")

        self.client = genai.Client(api_key=self.api_key)
        self.model = Config.gemini.model
        self.image_size = Config.gemini.image_size

    def generate(
        self,
        paper_content: str,
        custom_prompt: Optional[str] = None,
        image_size: Optional[str] = None,
    ) -> Optional[tuple[bytes, str]]:
        """
        生成论文漫画解读图

        Returns:
            (image_bytes, file_extension) on success, None on failure.
            file_extension includes the dot, e.g. ".png"
        """
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self.DEFAULT_PROMPT_TEMPLATE.format(paper_content=paper_content)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        size = image_size or self.image_size
        generate_config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(image_size=size),
        )

        logger.info(f"Generating comic with model: {self.model}, size: {size}")

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Attempt {attempt}/{MAX_RETRIES}")

                text_responses = []

                for chunk in self.client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=generate_config,
                ):
                    if (
                        chunk.candidates is None
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                    ):
                        continue

                    for part in chunk.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            inline_data = part.inline_data
                            file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                            logger.info(f"Comic generated ({len(inline_data.data)} bytes)")
                            return inline_data.data, file_extension

                        if hasattr(part, 'text') and part.text:
                            text_responses.append(part.text)

                    if hasattr(chunk, 'text') and chunk.text:
                        text_responses.append(chunk.text)

                full_text = ""
                if text_responses:
                    full_text = "\n".join(text_responses)
                    logger.info(f"API Response Text:\n{full_text[:2000]}")

                logger.warning(f"Attempt {attempt}: No image generated, retrying...")
                last_error = Exception(f"No image data in response. Text: {full_text[:50] if full_text else 'None'}")

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {e}")

            if attempt < MAX_RETRIES:
                logger.info(f"Waiting {RETRY_DELAY_SECONDS}s before retry...")
                time.sleep(RETRY_DELAY_SECONDS)

        logger.error(f"Failed to generate comic after {MAX_RETRIES} attempts")
        if last_error:
            raise last_error

        return None


def comic_exists(paper_id: str) -> bool:
    """检查论文漫画是否已存在（MinIO）"""
    return get_storage().comic_exists(paper_id)


def get_existing_comic_key(paper_id: str) -> Optional[str]:
    """获取已存在的漫画对象 key"""
    return get_storage().get_existing_comic_key(paper_id)


# Backward-compatible alias for Streamlit pages
get_existing_comic_path = get_existing_comic_key


def generate_paper_comic(
    paper_id: str,
    paper_content: str,
    api_key: Optional[str] = None,
    image_size: Optional[str] = None,
    force: bool = False,
) -> Optional[str]:
    """
    快速生成论文漫画解读图

    Returns:
        MinIO object key on success, None on failure
    """
    storage = get_storage()

    if not force:
        existing = storage.get_existing_comic_key(paper_id)
        if existing:
            logger.info(f"Comic already exists: {existing}")
            return existing

    generator = PaperComicGenerator(api_key=Config.gemini.api_key)
    result = generator.generate(
        paper_content=paper_content,
        image_size=image_size,
    )

    if result is None:
        return None

    image_bytes, ext = result
    key = storage.upload_comic(paper_id, image_bytes, ext)
    return key


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_content = """
    这篇论文提出了一种名为 "Transformer" 的新型神经网络架构。
    核心创新是 Self-Attention 机制，可以并行处理序列数据。
    相比 RNN/LSTM，训练速度更快，效果更好。
    在机器翻译任务上达到了 SOTA 效果。
    """

    result = generate_paper_comic(
        paper_id="test_paper",
        paper_content=test_content,
    )

    if result:
        print(f"Test succeeded: {result}")
    else:
        print("Test failed")
