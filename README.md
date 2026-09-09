# Session 4 — Basic RAG

Project này triển khai đúng luồng của `02_module4-rag-lab_hybrid 1.html`:

`input/*.md` → indexing (chunk + embedding + PostgreSQL/pgvector) → retrieval (vector + full-text → RRF → rerank → prompt + Ollama chat) → API → UI.

## Chạy bằng Docker

```bash
docker compose up -d --build
docker compose logs -f rag-app
```

Mở [http://localhost:8000](http://localhost:8000), đăng ký/đăng nhập, chọn classification rồi bấm **Upload & Index**.

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

Memory bật với `MEMORY_ENABLED=true`; UI giữ `conversation_id` để câu hỏi phụ
thuộc lượt trước được bổ ngữ cảnh. Quyền đọc của `/chat` không lấy từ body mà
được đọc mới từ DB theo token ở từng request.

Memory telemetry được ghi riêng vào `rag_pipeline/logs/memory.log` khi bật
`MEMORY_LOG_ENABLED=true`:

```bash
tail -f rag_pipeline/logs/memory.log
```

Log có các event `memory_read`, `memory_context`, `memory_write` và
`memory_skip`. Conversation/user được hash; câu hỏi và câu trả lời không ghi
nguyên văn, chỉ có số ký tự và trạng thái contextualise.

## Lab 4 — permissions và vòng đời tài liệu

Schema tạo `rag_classifications`, `rag_roles`, `rag_role_classifications` và
`app_user_roles`. Quyền đọc được tính theo `user → role → classification` và
lọc trực tiếp trong cả nhánh vector lẫn full-text. JWT chỉ chứa định danh user;
thu hồi role có hiệu lực ở request kế tiếp. Admin chỉ được bootstrap từ biến môi
trường, không có mật khẩu trong SQL hoặc git:

```dotenv
ADMIN_EMAIL=admin@rag.local
ADMIN_PASSWORD=<đặt local, không commit>
ADMIN_ROLE=admin
DEFAULT_ROLE=staff
DEFAULT_CLASSIFICATION=A
JWT_SECRET=<chuỗi random local>
JWT_EXPIRES_MIN=720
QA_AWARE_CHUNKING=true
```

Upload cần classification và chỉ hiển thị nhãn người dùng được ghi. `POST
/reindex` giữ classification/created_by cũ. Hash SHA-256 của text đã parse giúp
upload lại không đổi trả `status=unchanged`, còn nội dung đổi hoặc document mất
chunk sẽ index lại. UI liệt kê hash rút gọn, số chunk và nút xoá; xoá dùng 404
cho cả tài liệu không tồn tại lẫn tài liệu ngoài quyền và dọn cả file trong
`input/`.

Ví dụ test nhanh sau khi stack chạy:

```bash
TOKEN=$(curl -sS -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"staff@example.local","password":"local-password-123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/upload/classifications
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/documents
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F classification=A -F file=@input/corrector-agents.md
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"Corrector agent để làm gì?","hybrid":true,"retrieve_only":true}'
```

`retrieve_only=true` phù hợp để test permission mà không gọi LLM generate. Không
gửi `allowed_classification_ids` từ client; server chỉ dùng classification lấy từ DB.

Các model được pull lúc build nên lần đầu có thể mất vài phút và cần khoảng 6GB dung lượng. Compose mặc định không ép GPU để chạy được trên Docker Desktop không có GPU; nếu máy có GPU, có thể thêm device reservation theo hướng dẫn trong lab.

## Kiểm tra trực tiếp

```bash
# Hoặc index lại toàn bộ input/
curl -X POST http://localhost:8000/reindex -H "Authorization: Bearer $ADMIN_TOKEN"
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
RAG_EVAL_EMAIL=admin@rag.local RAG_EVAL_PASSWORD='<local-password>' python eval/run_eval.py
```

Bộ đo tách riêng `recall/mrr`, `refusal_rate`, `block_rate` và
`false_block_rate`; golden set có cờ `attack: true` cho các câu injection.

## Test offline

```bash
cd rag_pipeline
python -m unittest discover -s tests -v
```

## Cấu trúc chính

- `indexing/`: đọc Markdown, hash nội dung, chunk fixed-token hoặc QA-aware, gọi nomic và lưu DB.
- `retrieval/`: embed câu hỏi, tìm vector/full-text, RRF, rerank, dựng prompt và gọi llama3.2:3b.
- `retrieval/rerank/`: registry + policy dùng chung + backend FlashRank/LLM.
- `retrieval/hybrid/`: query builder, lexical search và RRF fusion.
- `api/`: auth, `/upload`, `/documents`, `/chat`, `/eval/run`, `/health` và `GET /` phục vụ UI.
- `sql/init_rag_db.sql` + các migration đánh số: schema documents, permissions, hash và embeddings.
