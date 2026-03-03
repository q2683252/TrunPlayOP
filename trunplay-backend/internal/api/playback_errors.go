package api

import (
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/services"
)

func handleStartPlaybackError(c *gin.Context, err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	switch {
	case errors.Is(err, services.ErrPlanNoDevice),
		errors.Is(err, services.ErrInvalidMediaURL),
		errors.Is(err, services.ErrStudyTaskNoMedia):
		BadRequest(c, msg)
		return true
	case errors.Is(err, services.ErrPlanNoPlayableMedia),
		errors.Is(err, services.ErrStudyTaskNotFound),
		errors.Is(err, services.ErrSmbServerNotFound):
		NotFound(c, msg)
		return true
	case errors.Is(err, services.ErrDeviceUnavailable):
		ServiceUnavailable(c, msg)
		return true
	default:
		return false
	}
}
