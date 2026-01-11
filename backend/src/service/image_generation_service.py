# src/service/image_generation_service.py

"""
论文漫画图生成服务 - 使用 Gemini 生成论文的图解

使用方法:
    from src.service.image_generation_service import generate_paper_comic
    
    image_path = generate_paper_comic(
        paper_id="2401.12345",
        paper_content="论文摘要或内容",
    )
"""

import logging
import mimetypes
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from src.config import Config

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
        """
        初始化生成器
        
        Args:
            api_key: Gemini API Key，默认从 Config 获取
        """
        self.api_key = api_key or Config.gemini.api_key
        if not self.api_key:
            raise ValueError("需要设置 gemini.api_key 配置或传入 api_key 参数")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = Config.gemini.model
        self.image_size = Config.gemini.image_size

    def generate(
        self,
        paper_content: str,
        output_path: str,
        custom_prompt: Optional[str] = None,
        image_size: Optional[str] = None,
    ) -> Optional[Path]:
        """
        生成论文漫画解读图
        
        Args:
            paper_content: 论文内容（摘要或全文）
            output_path: 输出图片路径
            custom_prompt: 自定义 prompt（可选）
            image_size: 图片尺寸 ("1K", "2K", "4K")，默认使用配置值
            
        Returns:
            生成的图片路径，失败返回 None
        """
        # 构建 prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self.DEFAULT_PROMPT_TEMPLATE.format(paper_content=paper_content)

        # 配置
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

        logger.info(f"🎨 Generating comic with model: {self.model}, size: {size}")

        # 生成（带重试机制）
        output_file = None
        last_error = None
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"🔄 Attempt {attempt}/{MAX_RETRIES}")
                
                # 收集所有文本响应
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
                    
                    # 遍历所有 parts
                    for part in chunk.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            # 保存图片
                            inline_data = part.inline_data
                            file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                            
                            # 确保输出路径有正确的扩展名
                            output_file = Path(output_path)
                            if not output_file.suffix:
                                output_file = output_file.with_suffix(file_extension)
                            
                            # 确保目录存在
                            output_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            # 写入文件
                            with open(output_file, "wb") as f:
                                f.write(inline_data.data)
                            
                            logger.info(f"✅ Comic saved to: {output_file}")
                            return output_file
                        
                        # 收集文本响应
                        if hasattr(part, 'text') and part.text:
                            text_responses.append(part.text)
                    
                    # 也检查 chunk 级别的 text
                    if hasattr(chunk, 'text') and chunk.text:
                        text_responses.append(chunk.text)
                
                # 记录所有文本响应
                full_text = ""
                if text_responses:
                    full_text = "\n".join(text_responses)
                    logger.info(f"📝 API Response Text:\n{full_text[:2000]}")  # 限制长度
                
                # 如果循环结束但没有返回，说明没有生成图片
                logger.warning(f"⚠️ Attempt {attempt}: No image generated, retrying...")
                last_error = Exception(f"No image data in response. Text: {full_text[:50] if full_text else 'None'}")

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Attempt {attempt} failed: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < MAX_RETRIES:
                logger.info(f"⏳ Waiting {RETRY_DELAY_SECONDS}s before retry...")
                time.sleep(RETRY_DELAY_SECONDS)
        
        # 所有重试都失败
        logger.error(f"❌ Failed to generate comic after {MAX_RETRIES} attempts")
        if last_error:
            raise last_error
        
        return output_file


def get_comic_path(paper_id: str) -> Path:
    """获取论文漫画的保存路径"""
    return Path(Config.image_save_path) / f"{paper_id}_comic.png"


def comic_exists(paper_id: str) -> bool:
    """检查论文漫画是否已存在"""
    comic_path = get_comic_path(paper_id)
    # 检查 png 和 jpg 两种格式
    return comic_path.exists() or comic_path.with_suffix(".jpg").exists()


def get_existing_comic_path(paper_id: str) -> Optional[Path]:
    """获取已存在的漫画路径"""
    comic_path = get_comic_path(paper_id)
    if comic_path.exists():
        return comic_path
    jpg_path = comic_path.with_suffix(".jpg")
    if jpg_path.exists():
        return jpg_path
    return None


def generate_paper_comic(
    paper_id: str,
    paper_content: str,
    api_key: Optional[str] = None,
    image_size: Optional[str] = None,
    force: bool = False,
) -> Optional[Path]:
    """
    快速生成论文漫画解读图
    
    Args:
        paper_id: 论文 ID（用于生成文件名）
        paper_content: 论文内容（摘要或全文总结）
        api_key: Gemini API Key（可选，默认从 Config 获取）
        image_size: 图片尺寸 ("1K", "2K", "4K")
        force: 是否强制重新生成（即使已存在）
        
    Returns:
        生成的图片路径，失败返回 None
        
    Example:
        >>> from src.service.image_generation_service import generate_paper_comic
        >>> 
        >>> path = generate_paper_comic(
        ...     paper_id="2401.12345",
        ...     paper_content="这篇论文提出了...",
        ... )
        >>> print(f"生成成功: {path}")
    """
    # 检查是否已存在
    if not force:
        existing = get_existing_comic_path(paper_id)
        if existing:
            logger.info(f"📄 Comic already exists: {existing}")
            return existing
    
    # 生成输出路径
    output_path = get_comic_path(paper_id)
    
    # 生成
    generator = PaperComicGenerator(api_key=Config.gemini.api_key)
    return generator.generate(
        paper_content=paper_content, 
        output_path=str(output_path),
        image_size=image_size,
    )


if __name__ == "__main__":
    # 测试用例
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
        print(f"✅ 测试成功: {result}")
    else:
        print("❌ 测试失败")
