# Corrector agents

## Corrector agent để làm gì?

Corrector agent là một agent LLM chạy sau agent chính để sửa đúng một lỗi hay lặp lại trong kết quả. Nó nhận output vừa tạo, kiểm tra lỗi theo một quy tắc cụ thể, rồi trả lại phiên bản đã sửa cùng lý do ngắn gọn.

Corrector không thay thế agent chính và không nên tự ý viết lại toàn bộ câu trả lời. Mục tiêu của nó là một lần sửa có phạm vi nhỏ, có thể kiểm tra được.

## Luồng xử lý

Agent chính tạo bản nháp. Corrector đọc bản nháp và tiêu chí kiểm tra. Nếu phát hiện lỗi, nó thay đổi phần sai; nếu không phát hiện lỗi, nó giữ nguyên nội dung. Ứng dụng sau đó ghi nhận cả bản nháp và kết quả cuối để tiện debug.

## Nguyên tắc

Mỗi corrector nên có một nhiệm vụ rõ ràng, đầu vào và đầu ra có cấu trúc, cùng một ví dụ kiểm thử. Không dùng corrector để che giấu lỗi ở prompt hoặc dữ liệu nguồn của agent chính.

