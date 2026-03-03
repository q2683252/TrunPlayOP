package api

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

func registerHistory(r *gin.RouterGroup) {
	g := r.Group("/history")
	g.GET("", listHistory)
	g.GET("/:history_id", getHistory)
	g.DELETE("/:history_id", deleteHistory)
	g.DELETE("", clearHistory)
}

func listHistory(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	planID := c.Query("plan_id")
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}
	skip := (page - 1) * pageSize
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	total, items, err := db.GetPlaybackHistories(tx, skip, pageSize, planID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"total": total, "page": page, "page_size": pageSize, "items": items})
}

func getHistory(c *gin.Context) {
	historyID := c.Param("history_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	h, err := db.GetPlaybackHistory(tx, historyID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if h == nil {
		NotFound(c, "History record not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, h)
}

func deleteHistory(c *gin.Context) {
	historyID := c.Param("history_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.DeletePlaybackHistory(tx, historyID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "History record not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "History record deleted"})
}

func clearHistory(c *gin.Context) {
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	n, err := db.ClearPlaybackHistory(tx)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Cleared " + strconv.FormatInt(n, 10) + " history records"})
}
