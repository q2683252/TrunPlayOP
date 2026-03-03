package api

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestDLNA_AVTransportNotifyRejectsOversizedBody(t *testing.T) {
	router, _ := testRouter(t)
	payload := bytes.Repeat([]byte("A"), maxDLNANotifyBodyBytes+1)
	req := httptest.NewRequest("NOTIFY", "/api/v1/dlna/avtransport", bytes.NewReader(payload))
	req.Header.Set("SID", "uuid:test")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("expected 413 for oversized notify body, got %d body=%s", w.Code, w.Body.Bytes())
	}
}

func TestDLNA_AVTransportNotifyRequiresSIDHeader(t *testing.T) {
	router, _ := testRouter(t)
	req := httptest.NewRequest("NOTIFY", "/api/v1/dlna/avtransport", bytes.NewReader([]byte("<e/>")))
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing SID header, got %d body=%s", w.Code, w.Body.Bytes())
	}
}
