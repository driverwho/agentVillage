"""NPC 背景管理器 — 单例模式。

启动时加载所有 ``server/data/npc_backgrounds/*.yaml`` 到内存，
后续通过 ``BackgroundManager.get(npc_id)`` 读取。
"""

import os
import glob
import logging
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class BackgroundManager:
    """单例：启动时一次性加载所有 NPC 背景 yaml 文件到内存。"""

    _instance: Optional["BackgroundManager"] = None

    def __init__(self, yaml_dir: str | None = None):
        self.yaml_dir = yaml_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # server/
            "data", "npc_backgrounds",
        )
        self._backgrounds: Dict[str, dict] = {}
        self._reload()

    # ---- public API ----

    @classmethod
    def init(cls, yaml_dir: str | None = None) -> "BackgroundManager":
        """初始化单例（幂等）。"""
        if cls._instance is None:
            cls._instance = cls(yaml_dir=yaml_dir)
            logger.info("BackgroundManager 已加载 %d 个 NPC", len(cls._instance._backgrounds))
        return cls._instance

    @classmethod
    def get(cls, npc_id: str) -> dict:
        """获取 NPC 完整背景。未找到抛出 KeyError。"""
        if cls._instance is None:
            raise RuntimeError("BackgroundManager 未初始化，请先调用 init()")
        if npc_id not in cls._instance._backgrounds:
            available = list(cls._instance._backgrounds.keys())
            raise KeyError(f"NPC '{npc_id}' 不在背景目录中。可用: {available}")
        return cls._instance._backgrounds[npc_id]

    @classmethod
    def all_ids(cls) -> list:
        """所有已加载的 NPC id 列表。"""
        if cls._instance is None:
            return []
        return list(cls._instance._backgrounds.keys())

    @classmethod
    def reset(cls) -> None:
        """（仅测试用）重置单例。"""
        cls._instance = None

    # ---- internal ----

    def _reload(self) -> None:
        pattern = os.path.join(self.yaml_dir, "*.yaml")
        for file_path in sorted(glob.glob(pattern)):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except yaml.YAMLError:
                logger.warning("跳过无效 yaml: %s", file_path)
                continue

            npc_id = data.get("id") or os.path.splitext(os.path.basename(file_path))[0]

            # 默认值（缺失字段不抛异常）
            data.setdefault("id", npc_id)
            data.setdefault("name", npc_id)
            data.setdefault("daily_habits", "")
            data.setdefault("core_motivation", "")
            data.setdefault("secret", "")
            data.setdefault("speaking_style", "")
            data.setdefault("visibility", ["basic"])
            data.setdefault("tools", [])
            data.setdefault("biography", "")
            data.setdefault("quirks", [])
            data.setdefault("state_reactions", {})
            data.setdefault("event_reactions", {})
            data.setdefault("relationships", {})
            data.setdefault("dialogue_topics", {})
            data.setdefault("information_layers", {})
            data.setdefault("tavern_social_behavior", {})

            self._backgrounds[npc_id] = data
