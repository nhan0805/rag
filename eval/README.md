# RAG hybrid and rerank evaluation

`golden_set.json` có 22 câu, gồm các câu `hard` và nhóm `ma-loi` để đánh giá
full-text trên mã lỗi. Script gọi `/chat` với `retrieve_only=true`, vì vậy đo
được thứ hạng ổn định mà không bị ảnh hưởng bởi câu trả lời của LLM.

```bash
python eval/run_eval.py
```

Có thể đổi URL hoặc số câu:

```bash
python eval/run_eval.py --url http://localhost:8000 --limit 15
```

Script in bốn cấu hình: `baseline`, `+rerank`, `+hybrid` và
`hybrid+rerank`. `Recall@fetch_k` lấy từ `retrieved_sources` (toàn bộ ứng
viên trước khi cắt), còn `MRR` lấy từ `sources` (danh sách cuối cùng đưa vào
prompt).
