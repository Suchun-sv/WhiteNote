from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Any

from ..model.paper import Paper


class JsonStore:
    """
    简单的 JSON 存储层：
    - 保存 Paper 列表到一个 JSON 文件
    - 从 JSON 文件加载 Paper 列表
    - insert_new_papers：仅新增不重复的 Paper（根据 Paper.id 判断）
    """

    def __init__(self, save_path: str):
        self.save_path = Path(save_path)
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

    # --------- 基础读写 --------- #

    def _load_papers(self) -> List[Paper]:
        """
        从 JSON 文件加载所有 Paper。
        如果文件不存在 → 返回空列表。
        """
        if not self.save_path.exists():
            return []

        with self.save_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        return [Paper.model_validate(item) for item in raw]

    def _save_papers(self, papers: List[Paper]) -> None:
        """
        将 Paper 列表保存到 JSON 文件（覆盖式写入）。
        """
        data = [p.model_dump(mode="json") for p in papers]

        with self.save_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
    
    def get_all_papers(self) -> List[Paper]:
        return self._load_papers()

    # --------- 仅新增逻辑 --------- #

    def insert_new_papers(self, new_papers: List[Paper]) -> int:
        """
        仅新增不存在的论文（根据 Paper.id 判断）
        返回：成功新增的数量
        """
        existing = self._load_papers()

        # 建立已有 id 集合
        existing_ids = {p.id for p in existing if p.id}

        inserted_papers = []

        for p in new_papers:
            if not p.id:
                # 跳过没有 id 的
                continue

            if p.id in existing_ids:
                # 已存在 → 跳过
                continue

            existing.append(p)
            existing_ids.add(p.id)
            inserted_papers.append(p)

        self._save_papers(existing)
        return inserted_papers
    
    def update_paper_field(self, id: str, field: str, value: Any) -> None:
        papers = self._load_papers()
        # assert if filed is a valid field of Paper
        assert field in Paper.__fields__, f"Field {field} is not a valid field of Paper"
        
        for p in papers:
            if p.id == id:
                setattr(p, field, value)
                break
        self._save_papers(papers)
    
    def get_paper_by_id(self, id: str) -> Paper:
        papers = self._load_papers()
        for p in papers:
            if p.id == id:
                return p
        return None