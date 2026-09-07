import json
import os
import unittest
from urllib.request import Request, urlopen


RUN_CALIBRATION = os.getenv("CALIBRATE") == "1"


@unittest.skipUnless(RUN_CALIBRATION, "Set CALIBRATE=1 to print calibration distributions")
class CalibrationE2ETests(unittest.TestCase):
    base_url = os.getenv("RAG_EVAL_URL", "http://localhost:8000")

    def test_print_fixture_score_distribution(self):
        # This tool deliberately reports observations; it does not choose a
        # threshold or assert that the groups are separable.
        questions = [
            ("real", "Nhân viên mới được bao nhiêu ngày phép năm?"),
            ("real", "Được làm việc từ xa tối đa mấy ngày một tuần?"),
            ("trap", "Giá cổ phiếu Apple hôm nay bao nhiêu?"),
            ("trap", "Thời tiết Hà Nội ngày mai thế nào?"),
        ]
        observations = []
        for label, question in questions:
            body = json.dumps(
                {"question": question, "rerank": True, "retrieve_only": True}
            ).encode("utf-8")
            request = Request(
                f"{self.base_url}/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=180) as response:
                payload = json.load(response)
            scores = [
                source.get("rerank_score")
                for source in payload.get("retrieved_sources", [])
                if source.get("rerank_score") is not None
            ]
            observations.append((label, max(scores, default=0.0)))
        print("calibration_observations=", observations)


if __name__ == "__main__":
    unittest.main()
