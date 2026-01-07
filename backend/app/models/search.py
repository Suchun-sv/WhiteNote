"""
搜索相关的 Pydantic 模型

定义的模型:
- SearchFilters: 搜索过滤条件 (来源, 分类, 日期范围)
- SearchRequest: 搜索请求 (查询词, 过滤条件, 返回数量)
- SearchResult: 单条搜索结果 (论文 + 相似度分数)
- SearchResponse: 搜索响应 (结果列表, 总数, 耗时)

使用示例:
    request = SearchRequest(query="transformer attention", top_k=10)
"""

# TODO: 实现搜索相关模型

