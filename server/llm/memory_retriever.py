import re
from abc import ABC, abstractmethod
from server.llm.token_counter import TokenCounter


class MemoryRetriever(ABC):
    @abstractmethod
    def retrieve(self, trigger: str, files: dict, max_tokens: int) -> tuple:
        """返回 (检索到的文本, [匹配条目元信息])"""
        ...


class SimpleKeywordRetriever(MemoryRetriever):
    def retrieve(self, trigger: str, files: dict, max_tokens: int) -> tuple:
        parts = []
        meta = []

        # 动态检索：关键词提取 + 段落匹配
        # 只检索动态记忆文件（agent_mem.md, world.md）——
        # 静态背景(self.md)已在 L0 系统角色中，玩家印象(user.md)已在 L3+L5
        keywords = self._extract_keywords(trigger)
        if keywords:
            for file_key in ["agent_mem.md", "world.md"]:
                content = files.get(file_key, "")
                if content:
                    matched = self._match_paragraphs(content, keywords)
                    for paragraph, score in matched:
                        parts.append(paragraph)
                        meta.append({"source": file_key, "type": "dynamic", "score": score})

        # 4. 按 token 限制截取
        result_text = ""
        for p in parts:
            candidate = result_text + p + "\n"
            if TokenCounter.count(candidate) > max_tokens:
                break
            result_text = candidate

        return result_text.strip(), meta

    def _extract_keywords(self, text: str) -> list:
        chinese_words = re.findall(r'[一-鿿]{2,4}', text)
        stopwords = {'什么', '怎么', '为什么', '是不是', '有没有', '可以', '这个', '那个', '一下', '一个'}
        return [w for w in chinese_words if w not in stopwords]

    def _extract_recent_summaries(self, content: str, n: int = 3) -> list:
        paragraphs = re.split(r'\n(?=##|Day)', content)
        return [p.strip() for p in paragraphs[-n:] if p.strip()]

    def _match_paragraphs(self, content: str, keywords: list) -> list:
        paragraphs = re.split(r'\n\n|\n(?=##)', content)
        scored = []
        for para in paragraphs:
            if not para.strip():
                continue
            matched = sum(1 for kw in keywords if kw in para)
            if matched > 0:
                match_score = matched / len(keywords)
                score = match_score * 0.5
                scored.append((para.strip(), score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
