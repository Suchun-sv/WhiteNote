import cocoindex as ci
from ..config import Config

@ci.flow_def(name="pdf_embedding_flow")
def pdf_flow(builder, scope):

    # 1️⃣ 指定 PDF 文件夹作为数据源
    scope["pdfs"] = builder.add_source(
        ci.sources.LocalFile(path=Config.pdf_save_path)
    )

    # 2️⃣ 转文本
    scope["text"] = builder.add_transform(
        ci.transforms.PdfToText(source=scope["pdfs"])
    )

    # 3️⃣ 分块
    scope["chunks"] = builder.add_transform(
        ci.transforms.TextChunk(source=scope["text"], chunk_size=Config.cocoindex.chunk_size)
    )

    # 4️⃣ embedding
    scope["emb"] = builder.add_transform(
        ci.transforms.Embedding(
            source=scope["chunks"],
            model=Config.cocoindex.embedding_model,
            api_key=Config.cocoindex.embedding_api_key,
            api_base=Config.cocoindex.embedding_api_base,
        )
    )

    # 5️⃣ 存 Qdrant
    builder.add_target(
        ci.targets.Qdrant(
            source=scope["emb"],
            host=Config.qdrant_database.host,
            port=Config.qdrant_database.port,
            collection=Config.qdrant_database.collection,
        )
    )