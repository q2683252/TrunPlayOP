func TestPlayback_VolumeRequiresLevel(t *testing.T) {
	router, _ := testRouter(t)
	code, body := postJSON(t, router, "/api/v1/playback/volume", map[string]interface{}{})
	if code != 400 {
		t.Fatalf("expected 400 when level is missing, got %d body=%s", code, body)
	}
}

func TestPlayback_SeekRequiresPosition(t *testing.T) {
	router, _ := testRouter(t)
	code, body := postJSON(t, router, "/api/v1/playback/seek", map[string]interface{}{})
	if code != 400 {
		t.Fatalf("expected 400 when position is missing, got %d body=%s", code, body)
	}
}
