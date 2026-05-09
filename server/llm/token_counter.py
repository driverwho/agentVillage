class TokenCounter:
    @staticmethod
    def count(text: str) -> int:
        if not text:
            return 0
        chinese = sum(1 for c in text if '一' <= c <= '鿿')
        other = len(text) - chinese
        result = int(chinese / 1.5 + other / 4)
        return max(1, result) if text.strip() else 0

    @staticmethod
    def count_messages(messages: list) -> int:
        return sum(TokenCounter.count(m.get("content", "")) for m in messages)
