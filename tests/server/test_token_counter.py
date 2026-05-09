from server.llm.token_counter import TokenCounter


class TestTokenCounter:
    def test_count_empty_string(self):
        assert TokenCounter.count("") == 0

    def test_count_pure_chinese(self):
        text = "一二三四五六七八九十一二三四五"
        assert len(text) == 15
        assert TokenCounter.count(text) == 10

    def test_count_pure_english(self):
        text = "hello world test case"
        assert TokenCounter.count(text) == 5

    def test_count_mixed_cn_en(self):
        text = "你好abc "
        expected = int(2 / 1.5 + 4 / 4)  # 1.33 + 1 = 2
        assert TokenCounter.count(text) == expected

    def test_count_messages(self):
        messages = [
            {"role": "system", "content": "你好世界"},
            {"role": "user", "content": "hello"},
        ]
        assert TokenCounter.count_messages(messages) == 3
