package services

import "errors"

var (
	ErrPlanNoDevice        = errors.New("plan has no device")
	ErrDeviceUnavailable   = errors.New("device unavailable")
	ErrPlanNoPlayableMedia = errors.New("plan has no playable media")
	ErrStudyTaskNotFound   = errors.New("study task not found")
	ErrStudyTaskNoMedia    = errors.New("study task has no media")
	ErrInvalidMediaURL     = errors.New("invalid media url")
	ErrSmbServerNotFound   = errors.New("smb server not found")
)

type playbackError struct {
	kind    error
	message string
	cause   error
}

func (e *playbackError) Error() string {
	if e == nil {
		return ""
	}
	return e.message
}

func (e *playbackError) Unwrap() error {
	if e == nil {
		return nil
	}
	if e.cause != nil {
		return errors.Join(e.kind, e.cause)
	}
	return e.kind
}

func newPlaybackError(kind error, message string) error {
	return &playbackError{kind: kind, message: message}
}

func wrapPlaybackError(kind error, message string, cause error) error {
	return &playbackError{kind: kind, message: message, cause: cause}
}
