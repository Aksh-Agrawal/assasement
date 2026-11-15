import httpx
import pytest

from app.content.client import ContentApiClient, ContentProtocolError


def test_exam_filter_rejects_unfiltered_response_from_older_portal():
    def serve(request):
        return httpx.Response(200, json={"schema_version": 1, "packs": [], "next_offset": None})

    with ContentApiClient("https://cloud.test", auth_token="test-device", local_profile_id="p1",
                          link_id="test-link", transport=httpx.MockTransport(serve)) as client:
        assert client.browse_question_banks() == ((), None)
        with pytest.raises(ContentProtocolError, match="does not support this exam filter"):
            client.browse_question_banks(exam="jee")
