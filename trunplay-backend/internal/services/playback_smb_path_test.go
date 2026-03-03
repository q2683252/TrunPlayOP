package services

import "testing"

func TestNormalizeSmbShareAndPathForPlayback(t *testing.T) {
	share, path := normalizeSmbShareAndPathForPlayback("Data", "smb://192.0.2.1/Data/video.mp4")
	if share != "Data" || path != "video.mp4" {
		t.Fatalf("configured share normalize failed: share=%q path=%q", share, path)
	}

	share, path = normalizeSmbShareAndPathForPlayback("Data", "Data/folder/ep01.mkv")
	if share != "Data" || path != "folder/ep01.mkv" {
		t.Fatalf("configured share plain path normalize failed: share=%q path=%q", share, path)
	}

	share, path = normalizeSmbShareAndPathForPlayback("", "smb://192.0.2.1/Media/folder/ep02.mkv")
	if share != "Media" || path != "folder/ep02.mkv" {
		t.Fatalf("derived share normalize failed: share=%q path=%q", share, path)
	}
}
