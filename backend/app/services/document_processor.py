"""
文档处理器 - 使用 PDFMathTranslate (pdf2zh) 进行学术论文翻译/简化
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from string import Template

from ..core.config import AppConfig
from ..models.task import TaskResult, TaskStatus
from .highlighter import HighlightService
from .task_manager import TaskManager

logger = logging.getLogger(__name__)

SIMPLIFY_PROMPT = Template(
    "You are an expert at simplifying academic English. "
    "Rewrite the following text using simple, everyday vocabulary "
    "(CEFR A2/B1 level, approximately 2000 common English words). "
    "Keep the same meaning. Keep all formula notations {v*} unchanged. "
    "Output only the rewritten text, nothing else.\n\n"
    "Source Text: $text\n\n"
    "Simplified Text:"
)


class DocumentProcessor:
    def __init__(self, config: AppConfig, task_manager: TaskManager) -> None:
        self.config = config
        self.task_manager = task_manager

    async def process(
        self, task_id: str, file_bytes: bytes, filename: str, mode: str = "translate", highlight: bool = False,
        llm_config: dict | None = None,
    ) -> None:
        """使用 pdf2zh 处理 PDF 文档"""

        if mode == "simplify":
            self.task_manager.update_progress(task_id, TaskStatus.PARSING, 10, "Preparing to simplify...")
        else:
            self.task_manager.update_progress(task_id, TaskStatus.PARSING, 10, "Preparing to translate...")

        # Use per-request LLM config if provided, else fallback to config.yaml
        cfg = llm_config or {}
        base_url = cfg.get("base_url") or self.config.llm.base_url
        api_key = cfg.get("api_key") or self.config.llm.api_key
        model = cfg.get("model") or self.config.llm.model

        os.environ["OPENAILIKED_BASE_URL"] = base_url
        os.environ["OPENAILIKED_API_KEY"] = api_key
        os.environ["OPENAILIKED_MODEL"] = model

        try:
            # 在线程中运行 pdf2zh（同步库）
            result = await asyncio.to_thread(
                self._translate_with_pdf2zh,
                file_bytes,
                filename,
                task_id,
                mode,
            )

            if result is None:
                self.task_manager.set_error(task_id, "Processing failed, please retry")
                return

            pdf_bytes, output_filename = result

            # 高亮后处理
            if highlight and pdf_bytes:
                self.task_manager.update_progress(
                    task_id, TaskStatus.HIGHLIGHTING, 85, "AI highlighting key sentences..."
                )
                try:
                    highlight_service = HighlightService(
                        api_key=api_key,
                        model=model,
                        base_url=base_url,
                    )
                    async with highlight_service:
                        pdf_bytes, stats = await highlight_service.highlight_pdf(pdf_bytes)
                        self.task_manager.set_highlight_stats(
                            task_id, json.dumps(stats.to_dict())
                        )
                        logger.info(
                            f"Task {task_id} 高亮完成: {stats.total} sentences highlighted"
                        )
                except Exception as exc:
                    logger.warning(
                        "Highlight post-processing failed, using non-highlighted PDF: %s", exc
                    )

            # 生成简单的预览 HTML
            preview_html = self._build_simple_preview(mode)

            task_result = TaskResult(
                pdf_bytes=pdf_bytes,
                preview_html=preview_html,
                filename=output_filename,
            )

            self.task_manager.set_result(task_id, task_result)
            logger.info(f"Task {task_id} completed (mode={mode})")

            # Auto-extract knowledge if original PDF exists
            if llm_config and llm_config.get("api_key"):
                original_path = None
                task_obj = self.task_manager.get_task(task_id)
                if task_obj and task_obj.original_pdf_path:
                    original_path = task_obj.original_pdf_path
                if original_path and Path(original_path).exists():
                    try:
                        from .knowledge_extractor import KnowledgeExtractor
                        original_bytes = Path(original_path).read_bytes()
                        extractor = KnowledgeExtractor(
                            api_key=llm_config["api_key"],
                            model=llm_config.get("model", ""),
                            base_url=llm_config.get("base_url", ""),
                        )

                        async def _extract():
                            async with extractor:
                                await extractor.extract(original_bytes, task_id, user_id=0)
                            logger.info(f"Auto knowledge extraction completed for {task_id}")

                        import asyncio
                        asyncio.create_task(_extract())
                    except Exception:
                        logger.warning("Auto knowledge extraction failed to start for %s", task_id)

        except Exception as exc:
            logger.exception("Processing failed: %s", exc)
            self.task_manager.set_error(task_id, f"Processing failed: {exc}")

    def _translate_with_pdf2zh(
        self,
        file_bytes: bytes,
        filename: str,
        task_id: str,
        mode: str = "translate",
    ) -> tuple[bytes, str] | None:
        """调用 pdf2zh 进行翻译或简化"""

        try:
            from pdf2zh import translate
            from pdf2zh.doclayout import DocLayoutModel
        except ImportError:
            logger.error("pdf2zh 未安装，请运行: pip install pdf2zh")
            return None

        # 加载 DocLayout-YOLO 模型
        model = DocLayoutModel.load_available()

        # 根据模式设置目标语言
        lang_out = "zh" if mode == "translate" else "en"

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存输入文件
            input_path = Path(temp_dir) / filename
            input_path.write_bytes(file_bytes)

            logger.info(f"Processing: {input_path} (mode={mode}, lang_out={lang_out})")

            action = "simplifying" if mode == "simplify" else "translating"
            self.task_manager.update_progress(task_id, TaskStatus.REWRITING, 30, f"AI {action}...")

            # Progress callback: map pdf2zh page progress to 30%–80%
            def _on_page_progress(tqdm_bar):
                if tqdm_bar.total and tqdm_bar.total > 0:
                    pct = 30 + int(50 * tqdm_bar.n / tqdm_bar.total)
                    self.task_manager.update_progress(
                        task_id, TaskStatus.REWRITING, pct,
                        f"AI {action}... ({tqdm_bar.n}/{tqdm_bar.total} pages)",
                    )

            try:
                # 调用 pdf2zh
                results = translate(
                    files=[str(input_path)],
                    lang_in="en",
                    lang_out=lang_out,
                    service="openailiked",
                    thread=4,
                    output=temp_dir,
                    model=model,
                    prompt=SIMPLIFY_PROMPT if mode == "simplify" else None,
                    ignore_cache=mode == "simplify",
                    callback=_on_page_progress,
                )

                if not results or len(results) == 0:
                    logger.error("pdf2zh 返回空结果")
                    return None

                file_mono, file_dual = results[0]

                # 更新进度
                self.task_manager.update_progress(task_id, TaskStatus.RENDERING, 80, "Generating PDF...")

                # 优先使用双语版本，如果没有则使用单语版本
                output_file = file_dual if file_dual else file_mono

                if output_file and Path(output_file).exists():
                    pdf_bytes = Path(output_file).read_bytes()
                    prefix = "translated" if mode == "translate" else "simplified"
                    output_filename = f"{prefix}_{Path(filename).stem}.pdf"
                    logger.info(f"处理完成: {output_file}")
                    return pdf_bytes, output_filename

                logger.error("输出文件不存在")
                return None

            except Exception as e:
                logger.exception(f"pdf2zh Processing failed: {e}")
                return None

    def _build_simple_preview(self, mode: str = "translate") -> str:
        label = "Simplified" if mode == "simplify" else "Translated"
        return f'<div style="padding:20px;text-align:center;color:#666"><p>PDF {label}. Download to view.</p></div>'
