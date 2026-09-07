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

## Guardrail, cache và memory

Lab production bổ sung ba lớp guardrail trong `rag_pipeline/guardrails/`:

- input chặn prompt injection Anh/Việt và câu quá dài; PII chỉ được che trong log;
- evidence chặn đường sinh câu khi không có bằng chứng đủ mạnh;
- output chặn prompt leak, còn số liệu không có trong context mặc định chỉ cảnh báo.

Ngưỡng mặc định được đo theo fixture và thang điểm FlashRank của stack này:
`GUARD_MIN_RERANK_SCORE=0.03`. `GUARD_MIN_VECTOR_SCORE` để trống vì
vector/RRF/reranker không cùng thang điểm. Khi thay corpus hoặc model, cần đo
lại phân phối điểm trước khi đổi ngưỡng.

Semantic cache dùng bảng `rag_query_cache`, khóa theo quyền đọc và cấu hình
`rerank/hybrid`, TTL 24 giờ, và được vô hiệu hóa khi tài liệu re-index hoặc bị
xóa. Chỉ câu trả lời có `document_id` mới được lưu. Có thể dọn cache bằng:

```bash
curl -X POST 'http://localhost:8000/eval/cache/purge?expired_only=true'
```

Memory bật với `MEMORY_ENABLED=true`; gửi thêm `conversation_id` và `user_id`
trong `/chat` để câu hỏi phụ thuộc lượt trước được bổ ngữ cảnh. Lịch sử luôn
được lọc theo cả hai trường này.

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

Bộ đo tách riêng `recall/mrr`, `refusal_rate`, `block_rate` và
`false_block_rate`; golden set có cờ `attack: true` cho các câu injection.

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
