from server.llm.memory_retriever import MemoryRetriever, SimpleKeywordRetriever


class TestSimpleKeywordRetriever:
    def test_fixed_load_self_summary(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": (
                "## 摘要1\nDay 1: 在田里干了一整天活。\n\n"
                "## 摘要2\nDay 2: 遇到了流浪商人，买了一包种子。\n\n"
                "## 摘要3\nDay 3: 听说警长丢了戒指，村里议论纷纷。\n\n"
                "## 摘要4\nDay 4: 下雨，在家休息。"
            ),
            "user.md": "这个玩家是个陌生人，看起来对村子很好奇。经常问来问去。",
            "agent_mem.md": "",
            "world.md": "",
        }
        result, meta = retriever.retrieve("戒指的事", files, max_tokens=500)
        assert "警长丢了戒指" in result
        assert "陌生人" in result

    def test_keyword_match_and_score(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": "## Day 1\n在后巷看到了警长。\n## Day 2\n铁匠铺着火了。\n## Day 3\n酒保和农夫吵了一架。",
            "user.md": "一个旅行者。",
            "agent_mem.md": "酒保: 他问了很多关于戒指的问题。\n农夫: 告诉了他村口的路。",
            "world.md": "Day 3: 流浪商人路过村子。",
        }
        result, meta = retriever.retrieve("警长在后巷干什么", files, max_tokens=500)
        assert "警长" in result

    def test_respects_max_tokens(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": "长文本内容。" * 200,
            "user.md": "短",
            "agent_mem.md": "",
            "world.md": "",
        }
        result, _ = retriever.retrieve("无关查询", files, max_tokens=50)
        from server.llm.token_counter import TokenCounter
        assert TokenCounter.count(result) <= 50

    def test_empty_files_returns_fixed_only(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": "",
            "user.md": "一个旅行者。",
            "agent_mem.md": "",
            "world.md": "",
        }
        result, _ = retriever.retrieve("你好", files, max_tokens=500)
        assert "旅行者" in result
