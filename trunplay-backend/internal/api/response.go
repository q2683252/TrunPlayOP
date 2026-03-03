package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type ApiResponse struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func OK(c *gin.Context, data interface{}) {
	c.JSON(http.StatusOK, ApiResponse{Code: 0, Message: "ok", Data: data})
}

func OKList(c *gin.Context, data interface{}) {
	OK(c, data)
}

func Fail(c *gin.Context, code int, message string) {
	c.JSON(http.StatusOK, ApiResponse{Code: code, Message: message})
}

func NotFound(c *gin.Context, message string) {
	c.JSON(http.StatusNotFound, ApiResponse{Code: 404, Message: message})
}

func BadRequest(c *gin.Context, message string) {
	c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: message})
}

func ServerError(c *gin.Context, message string) {
	c.JSON(http.StatusInternalServerError, ApiResponse{Code: 500, Message: message})
}

func ServiceUnavailable(c *gin.Context, message string) {
	c.JSON(http.StatusServiceUnavailable, ApiResponse{Code: 503, Message: message})
}
