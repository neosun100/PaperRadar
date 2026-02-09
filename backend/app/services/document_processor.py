"""
文档处理器 - 使用 PDFMathTranslate (pdf2zh) 进行学术论文翻译
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from ..core.config import AppConfig
from ..models.task import TaskResult, TaskStatus
from .task_manager import TaskManager

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, config: AppConfig, task_manager: TaskManager) -> None:
        self.config = config
        self.task_manager = task_manager

    async def process(self, task_id: str, file_bytes: bytes, filename: str) -> None:
        """使用 pdf2zh 翻译 PDF 文档"""

        self.task_manager.update_progress(task_id, TaskStatus.PARSING, 10, "正在准备翻译...")

        # 设置 pdf2zh 环境变量
        os.environ["OPENAILIKED_BASE_URL"] = self.config.llm.base_url
        os.environ["OPENAILIKED_API_KEY"] = self.config.llm.api_key
        os.environ["OPENAILIKED_MODEL"] = self.config.llm.model

        try:
            # 在线程中运行 pdf2zh（同步库）
            result = await asyncio.to_thread(
                self._translate_with_pdf2zh,
                file_bytes,
                filename,
                task_id,
            )

            if result is None:
                self.task_manager.set_error(task_id, "翻译失败，请重试")
                return

            pdf_bytes, output_filename = result

            # 生成简单的预览 HTML
            preview_html = self._build_simple_preview()

            task_result = TaskResult(
                pdf_bytes=pdf_bytes,
                preview_html=preview_html,
                filename=output_filename,
            )

            self.task_manager.set_result(task_id, task_result)
            logger.info(f"Task {task_id} 翻译完成")

        except Exception as exc:
            logger.exception("翻译失败: %s", exc)
            self.task_manager.set_error(task_id, f"翻译失败: {exc}")

    def _translate_with_pdf2zh(
        self,
        file_bytes: bytes,
        filename: str,
        task_id: str,
    ) -> tuple[bytes, str] | None:
        """调用 pdf2zh 进行翻译"""

        try:
            from pdf2zh import translate
            from pdf2zh.doclayout import DocLayoutModel
        except ImportError:
            logger.error("pdf2zh 未安装，请运行: pip install pdf2zh")
            return None

        # 加载 DocLayout-YOLO 模型
        model = DocLayoutModel.load_available()

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存输入文件
            input_path = Path(temp_dir) / filename
            input_path.write_bytes(file_bytes)

            logger.info(f"开始翻译: {input_path}")

            # 更新进度
            self.task_manager.update_progress(
                task_id, TaskStatus.REWRITING, 30, "正在使用 AI 翻译..."
            )

            try:
                # 调用 pdf2zh 翻译
                results = translate(
                    files=[str(input_path)],
                    lang_in="en",
                    lang_out="zh",
                    service="openailiked",
                    thread=4,
                    output=temp_dir,
                    model=model,
                )

                if not results or len(results) == 0:
                    logger.error("pdf2zh 返回空结果")
                    return None

                file_mono, file_dual = results[0]

                # 更新进度
                self.task_manager.update_progress(
                    task_id, TaskStatus.RENDERING, 80, "正在生成 PDF..."
                )

                # 优先使用双语版本，如果没有则使用单语版本
                output_file = file_dual if file_dual else file_mono

                if output_file and Path(output_file).exists():
                    pdf_bytes = Path(output_file).read_bytes()
                    output_filename = f"translated_{Path(filename).stem}.pdf"
                    logger.info(f"翻译完成: {output_file}")
                    return pdf_bytes, output_filename

                logger.error("翻译输出文件不存在")
                return None

            except Exception as e:
                logger.exception(f"pdf2zh 翻译失败: {e}")
                return None

    def _build_simple_preview(self) -> str:
        """生成简单的预览 HTML"""
        return """
        <div style="padding: 20px; text-align: center; color: #666;">
            <p>PDF 翻译完成，请下载查看。</p>
            <p style="font-size: 12px;">使用 PDFMathTranslate 技术，保留公式和布局。</p>
        </div>
        """
