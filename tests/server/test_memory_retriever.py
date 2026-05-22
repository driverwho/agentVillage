from server.llm.memory_retriever import MemoryRetriever, SimpleKeywordRetriever


class TestSimpleKeywordRetriever:
    def test_keyword_match_agent_mem(self):
        """agent_mem.md 是动态记忆文件，关键词匹配命中"""
        retriever = SimpleKeywordRetriever()
        files = {
            "agent_mem.md": (
                "## 酒保\n态度：尊重\n信任等级：8/10\n共同经历：酒馆老板知道乔治的过去。\n\n"
                "## 警长\n态度：敬畏\n信任等级：5/10\n共同经历：警长丢过戒指，乔治帮忙找过。\n"
            ),
            "world.md": "",
        }
        result, meta = retriever.retrieve("戒指", files, max_tokens=500)
        assert "戒指" in result

    def test_keyword_match_and_score(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "agent_mem.md": "酒保: 他问了很多关于戒指的问题。\n农夫: 告诉了他村口的路。\n警长: 在后巷巡逻时发现可疑人物。",
            "world.md": "Day 3: 流浪商人路过村子。警长在后巷盘问了他。",
        }
        result, meta = retriever.retrieve("警长在后巷干什么", files, max_tokens=500)
        assert "警长" in result

    def test_respects_max_tokens(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "agent_mem.md": "长文本内容。" * 200,
            "world.md": "",
        }
        result, _ = retriever.retrieve("无关查询", files, max_tokens=50)
        from server.llm.token_counter import TokenCounter
        assert TokenCounter.count(result) <= 50

    def test_empty_files_returns_empty(self):
        """没有动态记忆时，L4 返回空字符串（静态背景在 L0，用户印象在 L3/L5）"""
        retriever = SimpleKeywordRetriever()
        files = {
            "agent_mem.md": "",
            "world.md": "",
        }
        result, _ = retriever.retrieve("你好", files, max_tokens=500)
        assert result == ""
