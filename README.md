# Session 4 — Basic RAG

Project này triển khai đúng luồng của `02_module4-rag-lab_hybrid 1.html`:

`input/*.md` → indexing (chunk + embedding + PostgreSQL/pgvector) → retrieval (vector + full-text → RRF → rerank → prompt + Ollama chat) → API → UI.

## Chạy bằng Docker

```bash
docker compose up -d --build
docker compose logs -f rag-app
```

Mở [http://localhost:8000](http://localhost:8000), chọn file Markdown rồi bấm **Upload & Index**.

UI có toggle **Bật hybrid search** và **Bật rerank**. Khi bật hybrid, hệ thống lấy
ứng viên từ vector và PostgreSQL full-text rồi hợp nhất bằng Reciprocal Rank Fusion
(RRF). Khi bật rerank, hệ thống lấy 20 ứng viên rồi dùng
cross-encoder FlashRank giữ 4 chunk tốt nhất; đổi sang LLM bằng
`RERANK_BACKEND=llm` trong `.env.rag`, sau đó recreate container.

Sau khi chỉnh `.env.rag`, dùng `docker compose up -d rag-app --force-recreate`
để container nhận biến mới.

Khi clone project, copy `.env.rag.example` thành `.env.rag` và
`.env.pgvector.example` thành `.env.pgvector`, rồi đặt cùng một mật khẩu cho
PostgreSQL trong hai file đó.

Để xem input/output của từng lần gọi LLM, bật `LLM_LOG_ENABLED=true` trong
`.env.rag` rồi xem:

```bash
docker compose logs -f rag-app
```

Nội dung exchange LLM cũng được ghi vào `rag_pipeline/logs/llm.log`:

```bash
tail -f rag_pipeline/logs/llm.log
```

Log gồm system prompt, context/user prompt, câu trả lời và thống kê token/thời
gian từ Ollama. `LLM_LOG_FULL_CONTENT=true` chỉ nên dùng khi debug local vì
prompt có thể chứa dữ liệu tài liệu hoặc dữ liệu người dùng.

Các model được pull lúc build nên lần đầu có thể mất vài phút và cần khoảng 6GB dung lượng. Compose mặc định không ép GPU để chạy được trên Docker Desktop không có GPU; nếu máy có GPU, có thể thêm device reservation theo hướng dẫn trong lab.

## Kiểm tra trực tiếp

```bash
curl -F "file=@input/corrector-agents.md" http://localhost:8000/upload
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Corrector agent để làm gì?"}'

# Hoặc index lại toàn bộ input/
curl -X POST http://localhost:8000/reindex
```

Kiểm tra số bản ghi:

```bash
docker exec -it pgvector psql -U ai_user -d ai_db \
  -c 'SELECT count(*) FROM rag_documents;' \
  -c 'SELECT count(*) FROM rag_chunks;' \
  -c 'SELECT count(*) FROM rag_embeddings;'
```

Đo 4 cấu hình baseline, rerank, hybrid và hybrid+rerank bằng golden set:

```bash
python eval/run_eval.py
```

## Test offline

```bash
cd rag_pipeline
python -m unittest discover -s tests -v
```

## Cấu trúc chính

- `indexing/`: process 1, đọc Markdown, tách frontmatter, chunk fixed-token 800/120, gọi nomic và lưu DB.
- `retrieval/`: embed câu hỏi, tìm vector/full-text, RRF, rerank, dựng prompt và gọi llama3.2:3b.
- `retrieval/rerank/`: registry + policy dùng chung + backend FlashRank/LLM.
- `retrieval/hybrid/`: query builder, lexical search và RRF fusion.
- `api/`: `/upload`, `/chat`, `/health` và `GET /` phục vụ UI.
- `sql/init_rag_db.sql`: schema idempotent cho documents, chunks và embeddings.
